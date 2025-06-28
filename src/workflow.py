import asyncio
import logging
import os
from pathlib import Path
from src.graph import build_graph
from langchain_core.messages import HumanMessage, AIMessage
from src.prompts.planner_model import Plan
from src.tools.decorators import set_tool_event_callback

# Create logs directory if it doesn't exist
log_dir = Path("logs")
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
    encoding='utf-8',
    mode='a'
)
file_handler.setFormatter(formatter)
root_logger.addHandler(file_handler)

for logger_name in ["src", "src.graph", "src.graph.nodes", "src.graph.dev_mode"]:
    logging.getLogger(logger_name).setLevel(logging.INFO)

logger = logging.getLogger(__name__)
graph = build_graph()

def serialize_message(message):
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
    logger.info(f"[serialize_plan] Plan type: {type(plan)}")

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
        # Unwrap if necessary
        if "planner_output" in plan and isinstance(plan["planner_output"], dict):
            logger.info("[serialize_plan] Unpacking 'planner_output'")
            plan = plan["planner_output"]

        steps = plan.get("steps", [])
        if isinstance(steps, list):
            logger.info("[serialize_plan] Treating as dict with steps")
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
    logger.warning(f"[serialize_plan] Received: {plan}")
    return {"error": "Invalid plan format"}

async def run_agent_workflow_async(
    user_input: str,
    debug: bool = False,
    max_plan_iterations: int = 1,
    max_step_num: int = 2,
    output_format: str = "long-report"
):
    if not user_input:
        raise ValueError("Input could not be empty")

    logger.info(f"[workflow] Starting workflow with query: {user_input}")
    
    # Store reference to yielder for tool events
    tool_events_queue = asyncio.Queue()
    
    async def tool_event_handler(event):
        """Handle tool events and add them to queue for yielding."""
        await tool_events_queue.put(event)
    
    # Set up tool event callback
    set_tool_event_callback(tool_event_handler)
    
    initial_state = {
        "messages": [{"role": "user", "content": user_input}],
        "auto_accepted_plan": True,
        "plan_iterations": 0,
        "current_plan": None,
        "observations": [],
        "final_report": ""
    }
    logger.info(f"[workflow] Created initial state with keys: {list(initial_state.keys())}")

    config = {
        "configurable": {
            "thread_id": "default",
            "max_plan_iterations": max_plan_iterations,
            "max_step_num": max_step_num,
            "output_format": output_format,
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
        "recursion_limit": 20,
    }

    last_message_cnt = 0
    current_plan_yielded = False
    yielded_steps = set()

    try:
        logger.info("=== WORKFLOW STARTING ===")
        async for s in graph.astream(input=initial_state, config=config, stream_mode="values"):
            try:
                logger.info(f"=== NEW STATE UPDATE RECEIVED ===")
                # Check for any tool events first
                while not tool_events_queue.empty():
                    try:
                        tool_event = tool_events_queue.get_nowait()
                        logger.info(f"[workflow] Yielding tool event: {tool_event}")
                        yield tool_event
                    except asyncio.QueueEmpty:
                        break
                
                logger.info(f"[workflow] Processing state update: messages count = {len(s.get('messages', []))}")
                logger.info(f"[workflow] State keys in this update: {list(s.keys()) if isinstance(s, dict) else 'Not a dict'}")
                if isinstance(s, dict) and "messages" in s:
                    if len(s["messages"]) > last_message_cnt:
                        new_msgs = s["messages"][last_message_cnt:]
                        last_message_cnt = len(s["messages"])
                        logger.info(f"[workflow] Yielding {len(new_msgs)} new messages")
                        for msg in new_msgs:
                            serialized = serialize_message(msg)
                            logger.info(f"[workflow] Yielding message: {serialized}")
                            yield {"type": "message", "content": serialized}

                if isinstance(s, dict) and not current_plan_yielded and "current_plan" in s and s["current_plan"]:
                    raw_plan = s["current_plan"]
                    logger.info(f"[workflow] Found current_plan in state: {raw_plan}")

                    # Handle nested "planner_output" if it exists
                    if isinstance(raw_plan, dict) and "planner_output" in raw_plan:
                        logger.info("[workflow] Unpacking 'planner_output' from current_plan")
                        raw_plan = raw_plan["planner_output"]

                    logger.info(f"[workflow] RAW PLAN TYPE: {type(raw_plan)}")
                    logger.info(f"[workflow] RAW PLAN VALUE: {raw_plan}")

                    serialized_plan = serialize_plan(raw_plan)
                    logger.info(f"[workflow] SERIALIZED PLAN: {serialized_plan}")

                    # Only yield plan if it's not an error
                    if not (isinstance(serialized_plan, dict) and "error" in serialized_plan):
                        yield {"type": "plan", "content": serialized_plan}
                        current_plan_yielded = True
                    else:
                        logger.info("[workflow] Skipping plan yield due to serialization error")

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
                                logger.info(f"[workflow] YIELDING STEP: {step_title}")
                                yield {
                                    "type": "execution_res",
                                    "step_title": step_title,
                                    "content": step_res
                                }
                                yielded_steps.add(step_title)

                # Check for final report
                logger.info(f"[workflow] Checking for final_report in state...")
                if isinstance(s, dict):
                    logger.info(f"[workflow] State is dict with keys: {list(s.keys())}")
                    if "final_report" in s:
                        logger.info(f"[workflow] final_report key exists! Value: {s['final_report']}")
                        if s["final_report"]:
                            logger.info(f"[workflow] final_report has content: {s['final_report'][:100]}...")
                            final_report_event = {
                                "type": "final_report",
                                "content": s["final_report"]
                            }
                            logger.info(f"[workflow] About to yield final_report event: {final_report_event}")
                            yield final_report_event
                            logger.info(f"[workflow] Successfully yielded final_report event")
                        else:
                            logger.info(f"[workflow] final_report exists but is empty/falsy")
                    else:
                        logger.info(f"[workflow] final_report key NOT found in state")
                else:
                    logger.info(f"[workflow] State is not a dict, type: {type(s)}")

            except Exception as e:
                logger.exception("[workflow] Exception in stream loop")
                yield {"type": "error", "content": str(e)}
        
        # Log that stream has ended
        logger.info(f"=== WORKFLOW STREAM ENDED ===")
        logger.info(f"[workflow] Stream ended. Total messages yielded: {last_message_cnt}")
        logger.info(f"[workflow] Final yielded_steps: {yielded_steps}")
        logger.info(f"[workflow] Current plan yielded: {current_plan_yielded}")

    except Exception as e:
        logger.error(f"[workflow] Workflow error: {str(e)}")
        yield {"type": "error", "content": str(e)}

if __name__ == "__main__":
    print(graph.get_graph(xray=True).draw_mermaid())
