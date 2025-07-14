import asyncio
import json
import logging
import os
from pathlib import Path
from src.graph import build_graph
from langchain_core.messages import HumanMessage, AIMessage
from src.prompts.planner_model import Plan
from src.tools.decorators import set_tool_event_callback
from src.graph.nodes import reporter_node

# Create logs directory if it doesn't exist
# Get the absolute path to the meddr root directory
meddr_root = Path(__file__).parent.parent.absolute()
log_dir = meddr_root / "logs"
log_dir.mkdir(exist_ok=True)

# Configure root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

formatter = logging.Formatter("%(message)s")

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
root_logger.addHandler(console_handler)

file_handler = logging.FileHandler(
    filename=log_dir / "meddr.log",
    encoding="utf-8",
    mode="a",  # Append mode to preserve logs
)
file_handler.setFormatter(formatter)
root_logger.addHandler(file_handler)

for logger_name in ["src", "src.graph", "src.graph.nodes", "src.graph.dev_mode"]:
    logging.getLogger(logger_name).setLevel(logging.INFO)

logger = logging.getLogger(__name__)
graph = build_graph()


def load_mcp_config():
    """Load MCP configuration from JSON file."""
    try:
        # Get the absolute path to the meddr root directory
        meddr_root = Path(__file__).parent.parent.absolute()
        config_path = meddr_root / "mcp_config.json"
        logger.info(f"[workflow] Looking for mcp_config.json at: {config_path}")
        if config_path.exists():
            with open(config_path, "r") as f:
                config = json.load(f)
                mcp_servers = config.get("mcp_servers", {})
                logger.info(f"Loaded MCP servers: {list(mcp_servers.keys())}")
                return mcp_servers
        else:
            logger.warning(f"mcp_config.json not found at {config_path}, using default MCP settings")
            return {}
    except Exception as e:
        logger.error(f"Error loading MCP config: {e}")
        return {}


def serialize_message(message):
    if isinstance(message, (HumanMessage, AIMessage)):
        return {
            "role": message.type,
            "content": message.content,
            "name": getattr(message, "name", None),
        }
    elif isinstance(message, dict):
        return message
    else:
        return {"role": "system", "content": str(message)}


def serialize_plan(plan):
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
                    "execution_res": step.execution_res,
                }
                for step in plan.steps
            ],
        }

    elif isinstance(plan, dict):
        # Unwrap if necessary
        if "planner_output" in plan and isinstance(plan["planner_output"], dict):
            plan = plan["planner_output"]

        steps = plan.get("steps", [])
        if isinstance(steps, list):
            return {
                "title": plan.get("title", ""),
                "thought": plan.get("thought", ""),
                "steps": [
                    {
                        "title": step.get("title", ""),
                        "description": step.get("description", ""),
                        "step_type": step.get("step_type", None),
                        "execution_res": step.get("execution_res", None)
                    }
                    for step in steps
                ]
            }

    logger.warning("[serialize_plan] Invalid plan format")
    return {"error": "Invalid plan format"}


async def handle_recursion_limit(state, config):
    """Handle recursion limit by calling reporter directly."""
    logger.info("[workflow] Recursion limit reached, calling reporter directly")
    try:
        result = reporter_node(state, config)
        
        # Apply the Command's update to the state to get the final_report
        if hasattr(result, 'update') and isinstance(result.update, dict):
            # Apply the update to the state (simulating what the graph framework does)
            updated_state = state.copy()
            updated_state.update(result.update)
            return updated_state.get("final_report", "")
        elif isinstance(result, dict):
            return result.get("final_report", "")
        else:
            return "Report generation completed due to recursion limit."
    except Exception as e:
        logger.error(f"[workflow] Error calling reporter: {e}")
        return f"Report generation failed due to recursion limit: {str(e)}"


async def run_agent_workflow_async(
    user_input: str,
    max_plan_iterations: int = 1,
    max_step_num: int = 3,  # Reduced to prevent deep recursion
    output_format: str = "long-report",
    human_feedback: bool = False,  # Whether to require human feedback (default: False for auto-accept)
):
    if not user_input:
        raise ValueError("Input could not be empty")

    logger.info(f"[workflow] Starting workflow with query: {user_input[:100]}...")
    
    # Store reference to yielder for tool events
    tool_events_queue = asyncio.Queue()
    
    async def tool_event_handler(event):
        """Handle tool events and add them to queue for yielding."""
        await tool_events_queue.put(event)
    
    # Set up tool event callback
    set_tool_event_callback(tool_event_handler)
    
    initial_state = {
        "messages": [{"role": "user", "content": user_input}],
        "human_feedback": human_feedback,  # False = auto-accept plans, True = require human feedback
        "plan_iterations": 0,  # Track plan iterations
        "current_plan": None,  # Initialize plan
        "observations": [],  # Track observations
        "final_report": ""  # Initialize final report
    }
    
    # Load MCP servers configuration
    mcp_servers = load_mcp_config()

    config = {
        "configurable": {
            "thread_id": "default",
            "max_plan_iterations": max_plan_iterations,
            "max_step_num": max_step_num,
            "output_format": output_format,
            "mcp_settings": {
                "servers": mcp_servers
            },
        },
        "recursion_limit": 15,
    }

    last_message_cnt = 0
    current_plan_yielded = False
    yielded_steps = set()

    logger.info("=== WORKFLOW STARTING ===")
    
    # Track the last state for recursion limit handling
    last_state = initial_state
    
    try:
        async for s in graph.astream(input=initial_state, config=config, stream_mode="values"):
            # Update last state for potential recursion limit handling
            last_state = s
            
            try:
                # Check for any tool events first
                while not tool_events_queue.empty():
                    try:
                        tool_event = tool_events_queue.get_nowait()
                        yield tool_event
                    except asyncio.QueueEmpty:
                        break
                
                if isinstance(s, dict) and "messages" in s:
                    if len(s["messages"]) > last_message_cnt:
                        new_msgs = s["messages"][last_message_cnt:]
                        last_message_cnt = len(s["messages"])
                        for msg in new_msgs:
                            serialized = serialize_message(msg)
                            yield {"type": "message", "content": serialized}

                if isinstance(s, dict) and not current_plan_yielded and "current_plan" in s and s["current_plan"]:
                    raw_plan = s["current_plan"]

                    # Handle nested "planner_output" if it exists
                    if isinstance(raw_plan, dict) and "planner_output" in raw_plan:
                        raw_plan = raw_plan["planner_output"]

                    serialized_plan = serialize_plan(raw_plan)

                    # Only yield plan if it's not an error
                    if not (isinstance(serialized_plan, dict) and "error" in serialized_plan):
                        yield {"type": "plan", "content": serialized_plan}
                        current_plan_yielded = True
                        logger.info("[workflow] Plan yielded successfully")

                if isinstance(s, dict) and "current_plan" in s and s["current_plan"]:
                    plan = s["current_plan"]
                    if isinstance(plan, dict) and "planner_output" in plan:
                        plan = plan["planner_output"]

                    if isinstance(plan, Plan) or (isinstance(plan, dict) and "steps" in plan):
                        steps = plan.steps if isinstance(plan, Plan) else plan["steps"]
                        for step in steps:
                            step_title = step.title if hasattr(step, "title") else step.get("title")
                            step_res = step.execution_res if hasattr(step, "execution_res") else step.get("execution_res")
                            if step_res and step_title not in yielded_steps:
                                logger.info(f"[workflow] Yielding step: {step_title}")
                                yield {
                                    "type": "execution_res",
                                    "step_title": step_title,
                                    "content": step_res
                                }
                                yielded_steps.add(step_title)

                # Check for final report
                if isinstance(s, dict) and "final_report" in s and s["final_report"]:
                    logger.info("[workflow] Yielding final report")
                    yield {
                        "type": "final_report",
                        "content": s["final_report"]
                    }

            except Exception as e:
                logger.exception("[workflow] Exception in stream loop")
                yield {"type": "error", "content": str(e)}
        
        logger.info(f"=== WORKFLOW COMPLETED ===")
        
    except Exception as e:
        error_msg = str(e)
        if "recursion limit" in error_msg.lower():
            logger.warning(f"[workflow] Recursion limit reached: {error_msg}")
            # Call reporter directly with the last known state
            final_report = await handle_recursion_limit(last_state, config)
            yield {
                "type": "final_report",
                "content": final_report
            }
        else:
            logger.error(f"[workflow] Workflow error: {str(e)}")
            yield {"type": "error", "content": str(e)}

if __name__ == "__main__":
    print(graph.get_graph(xray=True).draw_mermaid())
