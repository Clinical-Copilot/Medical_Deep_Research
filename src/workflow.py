import asyncio
import logging
import os
from pathlib import Path
from src.graph import build_graph

# Create logs directory if it doesn't exist
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# Configure root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)  # Set to INFO level only

# Create formatters
formatter = logging.Formatter("%(asctime)s - %(message)s")

        # Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
root_logger.addHandler(console_handler)

        # File handler
file_handler = logging.FileHandler(
            filename=log_dir / "meddr.log",
            encoding='utf-8',
            mode='a'  # Append mode to preserve logs
        )
file_handler.setFormatter(formatter)
root_logger.addHandler(file_handler)

# Set all loggers to INFO level
for logger_name in ["src", "src.graph", "src.graph.nodes", "src.graph.dev_mode"]:
    logging.getLogger(logger_name).setLevel(logging.INFO)

logger = logging.getLogger(__name__)

# Create the graph
graph = build_graph()

async def run_agent_workflow_async(
    user_input: str,
    debug: bool = False,
    max_plan_iterations: int = 1,
    max_step_num: int = 3
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
        "auto_accepted_plan": True
        ##TODO: consider how to incorporate human feedback into the workflow
        # "auto_accepted_plan": False
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
        "recursion_limit": 100,
    }
    last_message_cnt = 0
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
                    logger.info(f"Processing: {message[0]}")
                    print(message)
                else:
                    logger.info(f"Processing: {message.get('content', '')}")
                    print(f"Message: {message}")
            else:
                # For any other output format
                logger.info(f"Processing: {s}")
                print(f"Output: {s}")
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            print(f"Error processing output: {str(e)}")

    logger.info("Workflow completed successfully")


if __name__ == "__main__":
    print(graph.get_graph(xray=True).draw_mermaid())