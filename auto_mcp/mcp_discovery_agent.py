import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
import logging
import re
from typing import List, Set
from langchain_core.messages import HumanMessage

from src.tools import google_search_tool
from src.tools.crawl import crawl_tool
from src.llms.llm import get_llm_by_type

logger = logging.getLogger(__name__)

class MCPDiscoveryAgent:
    """Agent responsible for discovering MCP servers using multiple sources."""
    
    def __init__(self, llm_type: str = "basic"):
        self.llm = get_llm_by_type(llm_type)
        # Known MCP server collections
        self.mcp_sources = {
            "official": "https://github.com/modelcontextprotocol/servers",
            "awesome": "https://github.com/wong2/awesome-mcp-servers"
        }
        
    async def discover_mcp_servers(self, query: str) -> List[str]:
        """
        Discover MCP server URLs using multiple sources.
        
        Args:
            query: Search query for MCP servers (e.g., "MCP server github", "Model Context Protocol server")
            
        Returns:
            List of discovered MCP server URLs
        """
        logger.info(f"Searching for MCP servers with query: {query}")
        
        all_urls: Set[str] = set()
        
        # 1. Search from official MCP servers repository
        logger.info("Searching official MCP servers repository...")
        official_urls = await self._search_official_repository(query)
        all_urls.update(official_urls)
        logger.info(f"Found {len(official_urls)} URLs from official repository")
        
        # 2. Search from awesome-mcp-servers collection
        logger.info("Searching awesome-mcp-servers collection...")
        awesome_urls = await self._search_awesome_collection(query)
        all_urls.update(awesome_urls)
        logger.info(f"Found {len(awesome_urls)} URLs from awesome collection")
        
        # 3. Use Google search as fallback
        logger.info("Searching with Google Custom Search...")
        google_urls = await self._search_google(query)
        all_urls.update(google_urls)
        logger.info(f"Found {len(google_urls)} URLs from Google search")
        
        # Convert to list and filter for GitHub URLs
        urls = list(all_urls)
        github_urls = [url for url in urls if "github.com" in url]
        
        logger.info(f"Total unique URLs found: {len(urls)}")
        logger.info(f"GitHub URLs after filtering: {len(github_urls)}")
        
        return github_urls
    
    async def _search_official_repository(self, query: str) -> List[str]:
        """Extract MCP server URLs from the official MCP servers repository."""
        try:
            # Crawl the official repository README
            crawl_result = crawl_tool(self.mcp_sources["official"])
            if isinstance(crawl_result, dict) and "crawled_content" in crawl_result:
                content = crawl_result["crawled_content"]
                return self._extract_github_urls_from_content(content, query)
        except Exception as e:
            logger.error(f"Error searching official repository: {e}")
        return []
    
    async def _search_awesome_collection(self, query: str) -> List[str]:
        """Extract MCP server URLs from the awesome-mcp-servers collection."""
        try:
            # Crawl the awesome collection README
            crawl_result = crawl_tool(self.mcp_sources["awesome"])
            if isinstance(crawl_result, dict) and "crawled_content" in crawl_result:
                content = crawl_result["crawled_content"]
                return self._extract_github_urls_from_content(content, query)
        except Exception as e:
            logger.error(f"Error searching awesome collection: {e}")
        return []
    
    async def _search_google(self, query: str) -> List[str]:
        """Search for MCP servers using Google Custom Search API."""
        try:
            search_result = google_search_tool.invoke({"query": query, "num_results": 10})
            if "error" in search_result:
                logger.error(f"Google search failed: {search_result['error']}")
                return []
            results = search_result.get("results", [])
            urls = [item["link"] for item in results if "link" in item]
            return urls
        except Exception as e:
            logger.error(f"Error in Google search: {e}")
            return []
    
    def _extract_github_urls_from_content(self, content: str, query: str) -> List[str]:
        """Extract GitHub URLs from markdown content, optionally filtering by query terms."""
        # Regex to find GitHub URLs in markdown
        github_pattern = r'https://github\.com/[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+'
        urls = re.findall(github_pattern, content)
        
        # If query has specific terms, try to filter for relevant URLs
        if query and query != "MCP server Model Context Protocol":
            query_terms = query.lower().split()
            filtered_urls = []
            for url in urls:
                # Simple relevance check - if any query term appears in the URL
                url_lower = url.lower()
                if any(term in url_lower for term in query_terms if len(term) > 2):
                    filtered_urls.append(url)
            return filtered_urls
        
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
