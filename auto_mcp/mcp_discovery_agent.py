import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
import logging
from typing import List
from langchain_core.messages import HumanMessage

from src.tools import openai_search_tool
from src.llms.llm import get_llm_by_type

logger = logging.getLogger(__name__)

# This is casually done, need to improve
class MCPDiscoveryAgent:
    """Agent responsible for discovering MCP servers using search tools."""
    
    def __init__(self, llm_type: str = "basic"):
        self.llm = get_llm_by_type(llm_type)
        
    async def discover_mcp_servers(self, query: str) -> List[str]:
        """
        Discover MCP server URLs using search tools.
        
        Args:
            query: Search query for MCP servers (e.g., "MCP server github", "Model Context Protocol server")
            
        Returns:
            List of discovered MCP server URLs
        """
        logger.info(f"Searching for MCP servers with query: {query}")
        
        # Use OpenAI search to find MCP server URLs
        search_result = await openai_search_tool.ainvoke({"query": query})
        
        if "error" in search_result:
            logger.error(f"Search failed: {search_result['error']}")
            return []
        
        urls = search_result.get("urls", [])
        logger.info(f"Found {len(urls)} potential MCP server URLs")
        
        return urls


# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def main():
        agent = MCPDiscoveryAgent()
        urls = await agent.discover_mcp_servers("MCP server github Model Context Protocol")
        print("Discovered MCP server URLs:")
        for url in urls:
            print(f"- {url}")
    
    asyncio.run(main())
