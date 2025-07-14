import json
import logging
import os
from typing import Annotated, Literal, Any, Dict, Optional, Callable
from functools import wraps
import asyncio

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langgraph.types import Command, interrupt
from langchain_mcp_adapters.client import MultiServerMCPClient

from src.agents import create_agent
from src.tools import (
    crawl_tool,
    openai_search_tool,
    litesense_tool,
    python_repl_tool
    # get_boxed_warning_info_by_drug_name
)


from src.config.agents import AGENT_LLM_MAP
from src.config.configuration import Configuration
from src.llms.llm import get_llm_by_type
from src.prompts.planner_model import Plan, StepType
from src.prompts.template import apply_prompt_template
from src.utils.json_utils import repair_json_output

from .types import State
from ..config import SELECTED_SEARCH_ENGINE, SearchEngine

logger = logging.getLogger(__name__)


@tool
def handoff_to_planner(
    task_title: Annotated[str, "The title of the task to be handed off."],
):
    """Handoff to planner agent to do plan."""
    # This tool is not returning anything: we're just using it
    # as a way for LLM to signal that it needs to hand off to planner agent
    return

def coordinator_node(
    state: State,
) -> Command[Literal["planner", "__end__"]]:
    """Coordinator node that communicate with users."""
    logger.info("Coordinator talking.")
    messages = apply_prompt_template("coordinator", state)
    response = (
        get_llm_by_type(AGENT_LLM_MAP["coordinator"])
        .bind_tools([handoff_to_planner])
        .invoke(messages)
    )

    logger.debug(f"Current state messages: {state['messages']}")

    goto = "__end__"

    if len(response.tool_calls) > 0:
        goto = "planner"
    else:
        logger.warning(
            f"Coordinator response contains no tool calls. Terminating workflow execution. Response: {response}"
        )
        logger.debug(f"Coordinator response: {response}")
        # Add the coordinator's response to the messages when it terminates the workflow
        coordinator_message = AIMessage(content=response.content, name="coordinator")
        return Command(
            update={"messages": state["messages"] + [coordinator_message]},
            goto=goto
        )

    return Command(goto=goto)

def planner_node(
    state: State, config: RunnableConfig
) -> Command[Literal["feedback_node", "reporter"]]:
    """Planner node that generate the full plan."""
    logger.info("Planner generating full plan")
    configurable = Configuration.from_runnable_config(config)
    plan_iterations = state["plan_iterations"] if state.get("plan_iterations", 0) else 0
    messages = apply_prompt_template("planner", state, configurable)

    if AGENT_LLM_MAP["planner"] == "basic":
        llm = get_llm_by_type(AGENT_LLM_MAP["planner"]).with_structured_output(
            Plan,
            method="json_mode",
        )
    else:
        llm = get_llm_by_type(AGENT_LLM_MAP["planner"])

    # if the plan iterations is greater than the max plan iterations, return the reporter node
    if plan_iterations >= configurable.max_plan_iterations:
        return Command(goto="reporter")

    full_response = ""
    if AGENT_LLM_MAP["planner"] == "basic":
        response = llm.invoke(messages)
        full_response = response.model_dump_json(indent=4, exclude_none=True)
    else:
        response = llm.stream(messages)
        for chunk in response:
            full_response += chunk.content
    logger.debug(f"Current state messages: {state['messages']}")
    logger.info(f"Planner response: {full_response}")

    try:
        curr_plan = json.loads(repair_json_output(full_response))
    except json.JSONDecodeError:
        logger.warning("Planner response is not a valid JSON")
        if plan_iterations > 0:
            return Command(goto="reporter")
        else:
            return Command(goto="__end__")
    
    if curr_plan.get("has_enough_context"):
        logger.info("Planner response has enough context.")
        new_plan = Plan.model_validate(curr_plan)
        return Command(
            update={
                "messages": [AIMessage(content=full_response, name="planner")],
                "current_plan": new_plan,
            },
            goto="reporter",
        )
    return Command(
        update={
            "messages": [AIMessage(content=full_response, name="planner")],
            "current_plan": full_response,
        },
        goto="feedback_node",
    )

def plan_modifier_node(
    state: State, config: RunnableConfig
) -> Command[Literal["feedback_node", "reporter"]]:
    """Plan modifier node that modifies existing plan based on feedback."""
    logger.info("Plan modifier updating plan based on feedback")
    
    current_plan = state.get("current_plan", "")
    messages = state.get("messages", [])
    
    # Find the feedback message
    feedback_content = ""
    for msg in messages:
        if hasattr(msg, 'name') and msg.name == "feedback":
            feedback_content = msg.content
            break
    
    if not feedback_content:
        logger.warning("No feedback found, returning to feedback node")
        return Command(goto="feedback_node")
    
    # Extract feedback (remove [EDIT_PLAN] prefix)
    if feedback_content.upper().startswith("[EDIT_PLAN]"):
        feedback = feedback_content[11:].strip()  # Remove "[EDIT_PLAN] "
    else:
        feedback = feedback_content
    
    # Convert Plan object to JSON string for the prompt
    if hasattr(current_plan, 'model_dump_json'):
        # It's a Plan object, convert to JSON
        plan_json = current_plan.model_dump_json(indent=2)
    else:
        # It's already a string, use as is
        plan_json = str(current_plan)
    
    # Create modification prompt
    modification_prompt = f"""You are a plan modifier. You have an existing plan and user feedback. 
Modify the plan based on the feedback while keeping the good parts of the original plan.

ORIGINAL PLAN:
{plan_json}

USER FEEDBACK:
{feedback}

Please modify the plan based on the feedback. Return the modified plan in the same JSON format as the original.
Focus on addressing the specific feedback while preserving the overall structure and good elements of the original plan.

IMPORTANT: For step_type values, use ONLY simple strings:
- Use "research" for information gathering steps
- Use "processing" for data processing and calculation steps
- Do NOT use complex values like "<StepType.RESEARCH: 'research'>"

The step_type field must be exactly "research" or "processing" as simple strings.

IMPORTANT: Include need_web_search field for each step:
- Set need_web_search: true for research steps that require external data gathering
- Set need_web_search: false for processing steps that do calculations or data processing."""

    configurable = Configuration.from_runnable_config(config)
    
    if AGENT_LLM_MAP["planner"] == "basic":
        llm = get_llm_by_type(AGENT_LLM_MAP["planner"]).with_structured_output(
            Plan,
            method="json_mode",
        )
    else:
        llm = get_llm_by_type(AGENT_LLM_MAP["planner"])

    # Generate modified plan
    full_response = ""
    if AGENT_LLM_MAP["planner"] == "basic":
        response = llm.invoke([HumanMessage(content=modification_prompt)])
        full_response = response.model_dump_json(indent=4, exclude_none=True)
    else:
        response = llm.stream([HumanMessage(content=modification_prompt)])
        for chunk in response:
            full_response += chunk.content
    
    logger.info(f"Plan modifier response: {full_response}")

    try:
        modified_plan = json.loads(repair_json_output(full_response))
        new_plan = Plan.model_validate(modified_plan)
        
        return Command(
            update={
                "messages": [AIMessage(content=full_response, name="plan_modifier")],
                "current_plan": new_plan,
            },
            goto="feedback_node",  # Go back to feedback node for review
        )
    except json.JSONDecodeError:
        logger.warning("Plan modifier response is not a valid JSON")
        return Command(goto="feedback_node")


##TODO: consider how to incorporate human feedback into the workflow
def human_feedback_node(
    state,
) -> Command[Literal["plan_modifier", "research_team", "reporter", "__end__"]]:
    current_plan = state.get("current_plan", "")
    # check if human feedback is required
    human_feedback = state.get("human_feedback", False)
    if human_feedback:
        # Simple terminal-based feedback
        print("\n" + "="*50)
        print("PLAN REVIEW REQUIRED")
        print("="*50)
        print("="*50)
        print("Options:")
        print("  [ACCEPTED] - Accept the plan and continue")
        print("  [EDIT_PLAN] <your feedback>")
        print("="*50)
        
        feedback = input("Enter your feedback: ").strip()
        
        # if the feedback is not accepted, return the planner node
        if feedback and str(feedback).upper().startswith("[EDIT_PLAN]"):
            return Command(
                update={
                    "messages": [
                        HumanMessage(content=feedback, name="feedback"),
                    ],
                },
                goto="plan_modifier",
            )
        elif feedback and str(feedback).upper().startswith("[ACCEPTED]"):
            logger.info("Plan is accepted by user.")
        else:
            # Default to accepted if no valid option provided
            logger.info("No valid option provided, accepting plan by default.")

    # if the plan is accepted, run the following node
    plan_iterations = state["plan_iterations"] if state.get("plan_iterations", 0) else 0
    goto = "research_team"
    try:
        current_plan = repair_json_output(current_plan)
        # increment the plan iterations
        plan_iterations += 1
        # parse the plan
        new_plan = json.loads(current_plan)
        if new_plan["has_enough_context"]:
            goto = "reporter"
    except json.JSONDecodeError:
        logger.warning("Planner response is not a valid JSON")
        if plan_iterations > 0:
            return Command(goto="reporter")
        else:
            return Command(goto="__end__")

    return Command(
        update={
            "current_plan": Plan.model_validate(new_plan),
            "plan_iterations": plan_iterations,
        },
        goto=goto,
    )


def research_team_node(
    state: State,
) -> Command[Literal["planner", "researcher", "coder", "reporter"]]:
    """Research team node that collaborates on tasks."""
    logger.info("Research team is collaborating on tasks.")
    current_plan = state.get("current_plan")
    if not current_plan or not current_plan.steps:
        return Command(goto="planner")
    if all(step.execution_res for step in current_plan.steps):
        return Command(goto="planner")
    for step in current_plan.steps:
        if not step.execution_res:
            break
    if step.step_type and step.step_type == StepType.RESEARCH:
        logger.info(f"Research team sending to researcher: {step.title}")
        logger.info(f"Step description: {step.description}")
        return Command(goto="researcher")
    if step.step_type and step.step_type == StepType.PROCESSING:
        return Command(goto="coder")
    return Command(goto="planner")


async def _execute_agent_step(
    state: State, agent, agent_name: str
) -> Command[Literal["research_team"]]:
    """Helper function to execute a step using the specified agent."""
    current_plan = state.get("current_plan")
    observations = state.get("observations", [])

    # Find the first unexecuted step
    current_step = None
    completed_steps = []
    for step in current_plan.steps:
        if not step.execution_res:
            current_step = step
            break
        else:
            completed_steps.append(step)

    if not current_step:
        logger.warning("No unexecuted step found")
        return Command(goto="research_team")

    logger.info(f"Executing step: {current_step.title}")

    # Format completed steps information
    completed_steps_info = ""
    if completed_steps:
        completed_steps_info = "# Existing Research Findings\n\n"
        for i, step in enumerate(completed_steps):
            completed_steps_info += f"## Existing Finding {i+1}: {step.title}\n\n"
            completed_steps_info += f"<finding>\n{step.execution_res}\n</finding>\n\n"

    # Prepare the input for the agent with completed steps info
    agent_input = {
        "messages": [
            HumanMessage(
                content=f"{completed_steps_info}# Current Task\n\n## Title\n\n{current_step.title}\n\n## Description\n\n{current_step.description}"
            )
        ]
    }

    # Add citation reminder for researcher agent
    if agent_name == "researcher":
        agent_input["messages"].append(
            HumanMessage(
                content="IMPORTANT: Use inline citations and a final \"### References\" section.  \nInline citations – place [tag] immediately after each claim; tag = first author's surname (or first significant title word if no author) + last two digits of year, e.g. [smith24]; add \"-a\", \"-b\"... if needed to keep tags unique; reuse the same tag for repeat citations.  \nReferences – append \"### References\" after the text; list every unique tag in the order it first appears, one per line with a blank line between, formatted **[tag]** [Full Source Title](URL). Show URLs only here.  \nNo other citation style.",
                name="system",
            )
        )
        logger.info("=== Researcher Input Messages ===")
        for msg in agent_input["messages"]:
            logger.info(f"Message from {msg.name if hasattr(msg, 'name') else 'user'}:")
            logger.info(msg.content)
            logger.info("---")

    # Invoke the agent
    default_recursion_limit = 20
    try:
        recursion_limit = int(os.getenv("AGENT_RECURSION_LIMIT", str(default_recursion_limit)))
        if recursion_limit <= 0:
            logger.warning(f"AGENT_RECURSION_LIMIT must be positive, using default: {default_recursion_limit}")
            recursion_limit = default_recursion_limit
        else:
            logger.info(f"Recursion limit set to: {recursion_limit}")
    except ValueError:
        logger.warning(f"Invalid AGENT_RECURSION_LIMIT value, using default: {default_recursion_limit}")
        recursion_limit = default_recursion_limit

    result = await agent.ainvoke(
        input=agent_input, config={"recursion_limit": recursion_limit}
    )

    # Process the result
    response_content = result["messages"][-1].content
    logger.debug(f"{agent_name.capitalize()} full response: {response_content}")

    # Update the step with the execution result
    current_step.execution_res = response_content
    logger.info(f"Step '{current_step.title}' execution completed by {agent_name}")

    return Command(
        update={
            "messages": [
                HumanMessage(
                    content=response_content,
                    name=agent_name,
                )
            ],
            "observations": observations + [response_content],
        },
        goto="research_team",
    )

async def _setup_and_execute_agent_step(
    state: State,
    config: RunnableConfig,
    agent_type: str,
    default_tools: list,
) -> Command[Literal["research_team"]]:
    """Helper function to set up an agent with appropriate tools and execute a step.

    This function handles the common logic for both researcher_node and coder_node:
    1. Configures MCP servers and tools based on agent type
    2. Creates an agent with the appropriate tools or uses the default agent
    3. Executes the agent on the current step

    Args:
        state: The current state
        config: The runnable config
        agent_type: The type of agent ("researcher" or "coder")
        default_tools: The default tools to add to the agent

    Returns:
        Command to update state and go to research_team
    """
    configurable = Configuration.from_runnable_config(config)
    mcp_servers = {}
    enabled_tools = {}

    # Extract MCP server configuration for this agent type
    if configurable.mcp_settings:
        for server_name, server_config in configurable.mcp_settings["servers"].items():
            if (
                server_config["enabled_tools"]
                and agent_type in server_config["add_to_agents"]
            ):
                mcp_servers[server_name] = {
                    k: v
                    for k, v in server_config.items()
                    if k in ("transport", "command", "args", "url", "env")
                }
                for tool_name in server_config["enabled_tools"]:
                    enabled_tools[tool_name] = server_name
 
    if mcp_servers:
        client = MultiServerMCPClient(mcp_servers)
        loaded_tools = default_tools[:]
        tools = await client.get_tools()
        for tool in tools:
            if tool.name in enabled_tools:
                tool.description = (
                    f"Powered by '{enabled_tools[tool.name]}'.\n{tool.description}"
                )
                loaded_tools.append(tool)
        agent = create_agent(agent_type, agent_type, loaded_tools, agent_type)
    else:
        # Fallback: create agent with default tools when no MCP servers configured
        agent = create_agent(agent_type, agent_type, default_tools, agent_type)
    
    return await _execute_agent_step(state, agent, agent_type)


async def researcher_node(
    state: State, config: RunnableConfig
) -> Command[Literal["research_team"]]:
    """Researcher node that do research"""
    logger.info("Researcher node is researching.")
    configurable = Configuration.from_runnable_config(config)
    research_tools = [openai_search_tool, litesense_tool, crawl_tool]

    return await _setup_and_execute_agent_step(
        state,
        config,
        "researcher",
        research_tools
        
    )

async def coder_node(
    state: State, config: RunnableConfig
) -> Command[Literal["research_team"]]:
    """Coder node that do code analysis."""
    logger.info("Coder node is coding.")
    return await _setup_and_execute_agent_step(
        state,
        config,
        "coder",
        [python_repl_tool],
    )

def reporter_node(state: State, config: RunnableConfig = None):
    """Reporter node that write a final report."""
    logger.info("=== REPORTER NODE STARTING ===")
    logger.info(f"Reporter node called with state keys: {list(state.keys())}")
    logger.info("Reporter write final report")
    current_plan = state.get("current_plan")
    
    # Get configuration
    configurable = Configuration.from_runnable_config(config) if config else Configuration()
    output_format = configurable.output_format
    
    # Handle both Plan object and string types for current_plan
    if hasattr(current_plan, 'title') and hasattr(current_plan, 'thought'):
        # It's a Plan object
        title = current_plan.title
        thought = current_plan.thought
    elif isinstance(current_plan, str):
        # It's a string, try to parse it as JSON
        try:
            import json
            plan_data = json.loads(current_plan)
            title = plan_data.get('title', 'Research Task')
            thought = plan_data.get('thought', 'No detailed thought process available')
        except (json.JSONDecodeError, TypeError):
            # If parsing fails, use the string as is
            title = 'Research Task'
            thought = current_plan
    else:
        # Fallback for unknown types
        title = 'Research Task'
        thought = 'No detailed thought process available'
    
    input_ = {
        "messages": [
            HumanMessage(
                f"# Research Requirements\n\n## Task\n\n{title}\n\n## Description\n\n{thought}"
            )
        ],
    }
    
    # Use different prompt template based on output format
    if output_format == "short-report":
        invoke_messages = apply_prompt_template("short_reporter", input_)
    elif output_format not in ["long-report", "short-report"]:
        # Custom format - use LLM to dynamically generate prompt based on user requirements
        prompt_generator = f"""You are a prompt engineering expert. Based on the user's requirements, generate a comprehensive prompt for a research report writer.

        User Requirements: {output_format}

        Generate a detailed prompt that:
        1. Understands the user's intention and requirements
        2. Provides clear instructions for the report structure and style
        3. Maintains professional standards and proper citations
        4. Adapts the format, tone, and content based on user needs
        5. Includes specific guidance for the AI reporter

        The prompt should be comprehensive and detailed, covering:
        - Role and responsibilities of the reporter
        - Report structure and organization
        - Writing style and tone
        - Citation format and requirements
        - Data integrity guidelines
        - Any specific formatting or content requirements

        Generate the prompt now:"""

        # Use LLM to generate the custom prompt
        custom_prompt_response = get_llm_by_type(AGENT_LLM_MAP["reporter"]).invoke([HumanMessage(content=prompt_generator)])
        custom_prompt = custom_prompt_response.content
        
        # Create messages with the dynamically generated prompt
        invoke_messages = [
            HumanMessage(content=custom_prompt),
            HumanMessage(content=input_["messages"][0].content)
        ]
    else:  # long-report (default)
        invoke_messages = apply_prompt_template("long_reporter", input_)
    
    observations = state.get("observations", [])

    # Add format-specific reminder
    if output_format == "short-report":
        format_reminder = "IMPORTANT: Provide a concise answer with key points only. Focus on the most essential findings in 2-3 sentences. Be direct and to the point."
    elif output_format not in ["long-report", "short-report"]:
        format_reminder = f"IMPORTANT: Follow the dynamically generated prompt above. The user's original requirements were: '{output_format}'. Ensure the report matches these requirements while maintaining professional standards and proper citations."
    else:  # long-report (default)
        format_reminder = "IMPORTANT: Structure your report according to the format in the prompt. Remember to include:\n\n1. Key Points - A bulleted list of the most important findings\n2. Overview - A brief introduction to the topic\n3. Detailed Analysis - Organized into logical sections\n4. Survey Note (optional) - For more comprehensive reports\n5. Key Citations - List all references at the end\n\nFor citations, DO NOT include inline citations in the text. Instead, place all citations in the 'Key Citations' section at the end using the format: `- [Source Title](URL)`. Include an empty line between each citation for better readability.\n\nPRIORITIZE USING MARKDOWN TABLES for data presentation and comparison. Use tables whenever presenting comparative data, statistics, features, or options. Structure tables with clear headers and aligned columns. Example table format:\n\n| Feature | Description | Pros | Cons |\n|---------|-------------|------|------|\n| Feature 1 | Description 1 | Pros 1 | Cons 1 |\n| Feature 2 | Description 2 | Pros 2 | Cons 2 |"

    invoke_messages.append(
        HumanMessage(
            content=format_reminder,
            name="system",
        )
    )

    for observation in observations:
        invoke_messages.append(
            HumanMessage(
                content=f"Below are some observations for the research task:\n\n{observation}",
                name="observation",
            )
        )

    
    response = get_llm_by_type(AGENT_LLM_MAP["reporter"]).invoke(invoke_messages)
    response_content = response.content
    logger.info(f"reporter response: {response_content}")
    
    result = {"final_report": response_content}
    logger.info(f"[reporter_node] Created result dict: {result}")
    logger.info(f"[reporter_node] About to return Command with update={result}")
    
    command_result = Command(
        update=result,
        goto="__end__"
    )
    logger.info(f"[reporter_node] Created Command object: {command_result}")
    logger.info("=== REPORTER NODE ENDING ===")
    return command_result

def node(func: Callable) -> Callable:
    """Decorator to create a node.
    
    Args:
        func: The function to wrap as a node
        
    Returns:
        Wrapped function
    """
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            raise

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            raise

    # Return the appropriate wrapper based on whether the function is async
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper