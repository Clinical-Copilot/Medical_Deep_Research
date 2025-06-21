import asyncio
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add the project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.llms.llm import get_llm_by_type
from src.config.agents import AGENT_LLM_MAP
from src.tools import crawl_tool
from src.tools.openai_search import openai_search
from src.tools.query_processor import QueryProcessor, LLMExpansionStrategy
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent

# Configure logging with a simpler format
logging.basicConfig(
    level=logging.INFO, format="%(message)s"  # Only show the message, no timestamp
)

# Set OpenAI client logging to WARNING level to suppress debug messages
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Define MCP server configuration matching the structure in nodes.py
config = {
    "configurable": {
        "thread_id": "default",
        "max_plan_iterations": 3,
        "max_step_num": 1,
        "mcp_settings": {"servers": {}},
    },
    "recursion_limit": 100,
}


async def test_research():
    """Test the intelligent assistant functionality."""
    # Initialize MCP client with the same structure as nodes.py
    mcp_servers = {}
    enabled_tools = {}

    if config["configurable"]["mcp_settings"]:
        for server_name, server_config in config["configurable"]["mcp_settings"][
            "servers"
        ].items():
            if (
                server_config["enabled_tools"]
                and "researcher" in server_config["add_to_agents"]
            ):
                mcp_servers[server_name] = {
                    k: v
                    for k, v in server_config.items()
                    if k in ("transport", "command", "args", "url", "env")
                }
                for tool_name in server_config["enabled_tools"]:
                    enabled_tools[tool_name] = server_name

    # Initialize MCP client
    client = MultiServerMCPClient(mcp_servers)

    # Get default tools
    loaded_tools = [crawl_tool, openai_search]

    # Get tools from MCP servers
    try:
        tools = await client.get_tools()
        for tool in tools:
            if tool.name in enabled_tools:
                tool.description = (
                    f"Powered by '{enabled_tools[tool.name]}'.\n{tool.description}"
                )
                loaded_tools.append(tool)
        logger.info(f"Loaded {len(loaded_tools)} tools")
    except Exception as e:
        logger.error(f"Error loading tools: {e}")
        loaded_tools = []  # Fallback to empty tools list if MCP fails

    # Get LLM for query processing
    model = get_llm_by_type(AGENT_LLM_MAP["researcher"])

    # Initialize query processor with LLM
    query_processor = QueryProcessor(loaded_tools, llm=model)

    # Create the agent with MCP tools
    agent = create_react_agent(
        model=model,
        tools=loaded_tools,
        prompt="""You are an intelligent assistant that helps solve problems using available tools effectively.

Query Processing Strategy:
1. Analyze the main query to identify key aspects that need investigation
2. Break down complex queries into simpler, focused sub-queries
3. For each sub-query, determine which tools are most appropriate
4. Consider different angles or perspectives that might provide valuable information
5. Filter and prioritize information based on relevance to the original query

Tool Usage Rules:
1. Only use tools that are directly relevant to solving the current step of the problem
2. Never make tool calls with meaningless values
3. For dependent operations, always wait for the result of the first tool before using it in the second tool
4. You can use multiple tools in parallel only if they are completely independent of each other
5. Each tool call must contribute to solving the problem - no exploratory or unnecessary calls
6. Always verify the input values before making a tool call to ensure they are meaningful
7. If a tool requires the result of another tool, you must wait for that result before proceeding
8. Never make a tool call with zero values unless explicitly required by the problem
9. Before each tool call, validate that the inputs are non-zero and meaningful for the operation
10. If you need to use a tool's result in another tool, store the first result and use it directly

Information Processing:
1. For each tool result, evaluate its relevance to the original query
2. Filter out information that is not directly related to the query
3. Combine and synthesize information from multiple sources
4. Identify any gaps in information that need additional queries
5. Prioritize the most relevant and recent information

Problem-Solving Process:
1. First, analyze the problem to identify the required steps and available tools
2. For each step, determine which tools are needed and their dependencies
3. Execute tools in the correct order, waiting for results when necessary
4. Use parallel execution only for truly independent operations
5. Document your reasoning and the purpose of each tool call
6. If a tool call fails, analyze the error and adjust your approach accordingly
7. Store intermediate results and use them directly in subsequent tool calls
8. After gathering all information, synthesize the results into a coherent response""",
        name="assistant",
    )

    # Test queries
    test_queries = [
        "What are the latest developments in quantum computing?",
        "How does climate change affect marine ecosystems?",
        "What are the key features of the latest iPhone model?",
    ]

    for query in test_queries:
        logger.info(f"\nQuery: {query}")

        # Process each tool with its specific strategy
        for tool in loaded_tools:
            # Expand the query using tool-specific strategy
            expanded_query = query_processor.expand_query(query, tool)

            logger.info(f"\nExpanded query for {tool.__class__.__name__}:")
            logger.info(f"Rationale: {expanded_query.rationale}")
            logger.info(f"Tool Requirements: {expanded_query.tool_requirements}")

            # Process each sub-query
            for sub_query in expanded_query.query:
                result = await agent.ainvoke(
                    {"messages": [{"role": "user", "content": sub_query}]}
                )

                # Process and store the results
                messages = result.get("messages", [])
                if not messages:
                    logger.warning("No messages were returned")
                    continue

                # Process each message
                for message in messages:
                    if hasattr(message, "content"):
                        # Process tool results if present
                        if hasattr(message, "tool_calls"):
                            for tool_call in message.tool_calls:
                                tool_name = tool_call.get("name")
                                tool_result = tool_call.get("result")
                                if tool_name and tool_result:
                                    processed_result = (
                                        query_processor.process_tool_result(
                                            tool_name, tool_result, sub_query
                                        )
                                    )
                                    # Get relevant results for this tool
                                    relevant_results = (
                                        query_processor.get_relevant_results(
                                            query, tool_name
                                        )
                                    )
                                    logger.info(f"\nProcessed result from {tool_name}:")
                                    logger.info(processed_result)
                                    if relevant_results:
                                        logger.info(
                                            f"\nRelevant results for {tool_name}:"
                                        )
                                        logger.info(relevant_results)
                        else:
                            logger.info(f"\n{message.content}")
                    else:
                        logger.info(f"\n{message}")


if __name__ == "__main__":
    asyncio.run(test_research())
