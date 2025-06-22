# import asyncio
# import logging
# import sys
# from pathlib import Path

# # Add the project root to sys.path
# project_root = Path(__file__).parent.parent
# sys.path.insert(0, str(project_root))

# from src.llms.llm import get_llm_by_type
# from src.config.agents import AGENT_LLM_MAP
# from src.tools import crawl_tool
# from src.tools.litesense import litesense_tool
# from src.tools.google_search import google_search
# from src.tools.openai_search import openai_search_tool
# from src.tools import weather_tool
# # from src.tools import get_drug_warnings_by_drug_name
# # from src.tools import (
# #     get_drug_warnings_by_drug_name,
# #     get_boxed_warning_info_by_drug_name,
# #     get_drug_names_by_controlled_substance_DEA_schedule,
# # )
# from langchain_mcp_adapters.client import MultiServerMCPClient
# from langgraph.prebuilt import create_react_agent

# # Configure logging with a simpler format
# logging.basicConfig(
#     level=logging.INFO, format="%(message)s"  # Only show the message, no timestamp
# )
# logger = logging.getLogger(__name__)

# # Define MCP server configuration matching the structure in nodes.py
# config = {
#     "configurable": {
#         "thread_id": "default",
#         "max_plan_iterations": 3,
#         "max_step_num": 1,
#         "mcp_settings": {
#             "servers": {
#                 # "mcp-github-trending": {
#                 #     "transport": "stdio",
#                 #     "command": "uvx",
#                 #     "args": ["mcp-github-trending"],
#                 #     "enabled_tools": ["get_github_trending_repositories"],
#                 #     "add_to_agents": ["researcher"],
#                 # }
#             }
#         },
#     },
#     "recursion_limit": 100,
# }


# async def test_research():
#     """Test the biomedical research assistant functionality."""
#     # Initialize MCP client with the same structure as nodes.py
#     mcp_servers = {}
#     enabled_tools = {}

#     if config["configurable"]["mcp_settings"]:
#         for server_name, server_config in config["configurable"]["mcp_settings"][
#             "servers"
#         ].items():
#             if (
#                 server_config["enabled_tools"]
#                 and "researcher" in server_config["add_to_agents"]
#             ):
#                 mcp_servers[server_name] = {
#                     k: v
#                     for k, v in server_config.items()
#                     if k in ("transport", "command", "args", "url", "env")
#                 }
#                 for tool_name in server_config["enabled_tools"]:
#                     enabled_tools[tool_name] = server_name

#     # Initialize MCP client
#     client = MultiServerMCPClient(mcp_servers)

#     # Get default tools
#     loaded_tools = [crawl_tool]

#     loaded_tools = [
#         get_drug_warnings_by_drug_name,
#         get_boxed_warning_info_by_drug_name,
#         get_drug_names_by_controlled_substance_DEA_schedule,
#     ]

#     # Get tools from MCP servers
#     try:
#         tools = await client.get_tools()
#         for tool in tools:
#             if tool.name in enabled_tools:
#                 tool.description = (
#                     f"Powered by '{enabled_tools[tool.name]}'.\n{tool.description}"
#                 )
#                 loaded_tools.append(tool)
#     except Exception as e:
#         logger.error(f"Error loading tools: {e}")
#         loaded_tools = []  # Fallback to empty tools list if MCP fails

#     # Create the agent with MCP tools
#     model = get_llm_by_type(AGENT_LLM_MAP["researcher"])
#     agent = create_react_agent(
#         model=model,
#         tools=loaded_tools,
#         prompt="""You are a biomedical research assistant that helps gather comprehensive information from multiple sources.
#         Use the available tools to find and analyze information from various biomedical sources.
#         Focus on peer-reviewed articles, clinical trials, and medical research papers.
#         Make sure to clearly label which information comes from which source. I also need smart incline citations with smart abbreviations in the text. Need the incline citation to match the references ta the final. Track all sources and include a References section at the end using link reference format. Include an empty line between each citation for better readability. Use this format for each reference:\n- [Source Title](URL)\n\n- [Another Source](URL)""",
#         name="biomedical_research_assistant",
#     )

#     # Test queries
#     test_queries = [
#         "What precautions or warnings should be kept in mind when taking aspirin?"
#     ]

#     for query in test_queries:
#         logger.info(f"\nQuery: {query}")
#         result = await agent.ainvoke({"messages": [{"role": "user", "content": query}]})

#         messages = result.get("messages", [])
#         print(messages[-1].content)


# if __name__ == "__main__":
#     asyncio.run(test_research())
