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
    initial_state = {
        "messages": [{"role": "user", "content": user_input}],
        "auto_accepted_plan": True,
        "plan_iterations": 0,
        "current_plan": None,
        "observations": []
    }

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
        async for s in graph.astream(input=initial_state, config=config, stream_mode="values"):
            try:
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
                        logger.info("[workflow] Unpacking 'planner_output' from current_plan")
                        raw_plan = raw_plan["planner_output"]

                    logger.info(f"[workflow] RAW PLAN TYPE: {type(raw_plan)}")
                    logger.info(f"[workflow] RAW PLAN VALUE: {raw_plan}")

                    serialized_plan = serialize_plan(raw_plan)
                    logger.info(f"[workflow] SERIALIZED PLAN: {serialized_plan}")

                    yield {"type": "plan", "content": serialized_plan}
                    current_plan_yielded = True

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

            except Exception as e:
                logger.exception("[workflow] Exception in stream loop")
                yield {"type": "error", "content": str(e)}

    except Exception as e:
        logger.error(f"[workflow] Workflow error: {str(e)}")
        yield {"type": "error", "content": str(e)}

if __name__ == "__main__":
    print(graph.get_graph(xray=True).draw_mermaid())
