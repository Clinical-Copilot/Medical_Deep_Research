import asyncio
import logging
import os
from pathlib import Path
from src.graph import build_graph
from langchain_core.messages import HumanMessage, AIMessage
from src.prompts.planner_model import Plan

# Create logs directory if it doesn't exist
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# Configure root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# Create simple formatter
simple_formatter = logging.Formatter("%(message)s")

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(simple_formatter)
root_logger.addHandler(console_handler)

# File handler
file_handler = logging.FileHandler(
            filename=log_dir / "meddr.log",
            encoding='utf-8',
            mode='a'  # Append mode to preserve logs
        )
file_handler.setFormatter(simple_formatter)
root_logger.addHandler(file_handler)

# Set all loggers to INFO level
for logger_name in ["src", "src.graph", "src.graph.nodes", "src.graph.dev_mode"]:
    logging.getLogger(logger_name).setLevel(logging.INFO)

logger = logging.getLogger(__name__)

# Create the graph
graph = build_graph()

def serialize_message(message):
    """Helper function to serialize a message object to a dict."""
    if isinstance(message, (HumanMessage, AIMessage)):
        return {
            "role": message.type,
            "content": message.content,
            "name": getattr(message, "name", None)
        }
    elif isinstance(message, dict):
        return message
    else:
        return {"role": "system", "content": str(message)}

def serialize_plan(plan):
    """Helper function to serialize a Plan object to a dict."""
    if isinstance(plan, Plan):
        return {
            "has_enough_context": plan.has_enough_context,
            "thought": plan.thought,
            "title": plan.title,
            "steps": [
                {
                    "title": step.title,
                    "description": step.description,
                    "step_type": step.step_type.value if step.step_type else None,
                    "execution_res": step.execution_res
                }
                for step in plan.steps
            ]
        }
    elif isinstance(plan, dict):
        return plan
    else:
        return {"error": "Invalid plan format"}

async def run_agent_workflow_async(
    user_input: str,
    debug: bool = False,
    max_plan_iterations: int = 1,
    max_step_num: int = 2  # Reduced to prevent deep recursion
):
    """Run the agent workflow asynchronously with the given user input.

    Args:
        user_input: The user's query or request
        debug: If True, enables debug level logging
        max_plan_iterations: Maximum number of plan iterations
        max_step_num: Maximum number of steps in a plan

    Returns:
        The final state after the workflow completes
    """
    if not user_input:
        raise ValueError("Input could not be empty")

    logger.info(f"Starting workflow with query: {user_input}")
    initial_state = {
        # Runtime Variables
        "messages": [{"role": "user", "content": user_input}],
        "auto_accepted_plan": True,  # Auto-accept plans to reduce recursion
        "plan_iterations": 0,  # Track plan iterations
        "current_plan": None,  # Initialize plan
        "observations": []  # Track observations
    }
    config = {
        "configurable": {
            "thread_id": "default",
            "max_plan_iterations": max_plan_iterations,
            "max_step_num": max_step_num,
            "mcp_settings": {
                "servers": {
                    "mcp-github-trending": {
                        "transport": "stdio",
                        "command": "uvx",
                        "args": ["mcp-github-trending"],
                        "enabled_tools": ["get_github_trending_repositories"],
                        "add_to_agents": ["researcher"],
                    }
                }
            },
        },
        "recursion_limit": 20,  # Increased to 20 for more flexibility
    }
    last_message_cnt = 0
    try:
        async for s in graph.astream(
            input=initial_state, config=config, stream_mode="values"
        ):  
            try:
                if isinstance(s, dict) and "messages" in s:
                    if len(s["messages"]) <= last_message_cnt:
                        continue
                    last_message_cnt = len(s["messages"])
                    message = s["messages"][-1]
                    if isinstance(message, tuple):
                        print(message[0])
                    else:
                        print(message.get('content', ''))
                else:
                    print(s)
            except Exception as e:
                print(f"Error: {str(e)}")
        
        # Serialize messages and plan before returning
        if isinstance(s, dict):
            if "messages" in s:
                s["messages"] = [serialize_message(msg) for msg in s["messages"]]
            if "current_plan" in s:
                s["current_plan"] = serialize_plan(s["current_plan"])
            
            # Capture coordinator response from the last message
            if "messages" in s and s["messages"]:
                last_message = s["messages"][-1]
                if isinstance(last_message, dict) and last_message.get("role") == "assistant":
                    s["coordinator_response"] = last_message.get("content")
        
        # Return the final state
        return s
    except Exception as e:
        logger.error(f"Workflow error: {str(e)}")
        raise


if __name__ == "__main__":
    print(graph.get_graph(xray=True).draw_mermaid())