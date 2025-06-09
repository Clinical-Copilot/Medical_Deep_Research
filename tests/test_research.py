import asyncio
import logging
import sys
from pathlib import Path

# Add the project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.llms.llm import get_llm_by_type
from src.config.agents import AGENT_LLM_MAP
from src.tools import crawl_tool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Define MCP server configuration matching the structure in nodes.py
config = {
        "configurable": {
            "thread_id": "default",
            "max_plan_iterations": 3,
            "max_step_num": 1,
            "mcp_settings": {
                "servers": {
                    # "mcp-github-trending": {
                    #     "transport": "stdio",
                    #     "command": "uvx",
                    #     "args": ["mcp-github-trending"],
                    #     "enabled_tools": ["get_github_trending_repositories"],
                    #     "add_to_agents": ["researcher"],
                    # }
                }
            },
        },
        "recursion_limit": 100,
    }

async def test_research():
    """Test the biomedical research assistant functionality."""
    # Initialize MCP client with the same structure as nodes.py
    mcp_servers = {}
    enabled_tools = {}
    
    if config["configurable"]["mcp_settings"]:
        for server_name, server_config in config["configurable"]["mcp_settings"]["servers"].items():
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
    loaded_tools = [crawl_tool]
    
    # Get tools from MCP servers
    try:
        tools = await client.get_tools()
        for tool in tools:
            if tool.name in enabled_tools:
                tool.description = (
                    f"Powered by '{enabled_tools[tool.name]}'.\n{tool.description}"
                )
                loaded_tools.append(tool)
        logger.info(f"Successfully loaded {len(loaded_tools)} tools from MCP servers")
    except Exception as e:
        logger.error(f"Error loading tools from MCP servers: {e}")
        loaded_tools = []  # Fallback to empty tools list if MCP fails

    # Create the agent with MCP tools
    model = get_llm_by_type(AGENT_LLM_MAP["researcher"])
    agent = create_react_agent(
        model=model,
        tools=loaded_tools,
        prompt="""You are a biomedical research assistant that helps gather comprehensive information from multiple sources.
        Use the available tools to find and analyze information from various biomedical sources.
        Focus on peer-reviewed articles, clinical trials, and medical research papers.
        Make sure to clearly label which information comes from which source.""",
        name="biomedical_research_assistant"
    )
    
    # Test queries
    test_queries = [
        "Help me research about Yingtao Luo"
    ]
    
    for query in test_queries:
        logger.info(f"\nTesting query: {query}")
        result = await agent.ainvoke({
            "messages": [{
                "role": "user",
                "content": query
            }]
        })
        
        messages = result.get("messages", [])
        assert messages, "No messages were returned"
        
        # Log the results for inspection
        logger.info(f"Number of messages: {len(messages)}")
        for message in messages:
            logger.info(f"Message content: {message}")

if __name__ == "__main__":
    asyncio.run(test_research()) 