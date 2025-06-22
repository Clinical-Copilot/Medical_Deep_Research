# MCP Google Custom Search Server client (replace google_search.py)

import os
import logging
import json
import requests
from typing import Optional, Dict, Any
from langchain_core.tools import tool

logger = logging.getLogger(__name__)


class MCPGoogleSearch:
    """MCP Google Custom Search Server client."""

    def __init__(self):
        self.mcp_server_url = os.getenv("MCP_SERVER_URL", "http://localhost:3000")
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.search_engine_id = os.getenv("GOOGLE_SEARCH_ENGINE_ID")

        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is not set")
        if not self.search_engine_id:
            raise ValueError("GOOGLE_SEARCH_ENGINE_ID environment variable is not set")

    def search(self, query: str, num_results: int = 10) -> Dict[str, Any]:
        """Perform a search using the MCP Google Custom Search Server."""
        try:
            response = requests.post(
                f"{self.mcp_server_url}/search",
                json={"query": query, "numResults": min(num_results, 10)},
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to perform MCP search: {e}")
            raise


@tool
def mcp_google_search(query: str, num_results: int = 10) -> str:
    """Perform a Google search using the MCP Google Custom Search Server."""
    try:
        searcher = MCPGoogleSearch()
        results = searcher.search(query, num_results)

        if not results.get("items"):
            return f"No search results found for {query}."

        formatted_results = [f"Google Search Results for: '{query}'\n"]
        for item in results["items"]:
            title = item.get("title", "No title")
            link = item.get("link", "No link")
            snippet = item.get("snippet", "No description")
            domain = item.get("displayLink", "")
            formatted_results.append(
                f"Title: {title}\nLink: {link}\nDescription: {snippet}\nDomain: {domain}\n"
            )

        return "\n".join(formatted_results)

    except Exception as e:
        error_msg = f"Failed to search. Error: {e}"
        logger.error(error_msg)
        return error_msg
