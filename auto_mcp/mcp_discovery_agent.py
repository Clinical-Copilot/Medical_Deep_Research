# The project is built upon Bytedance MedDR
# SPDX-License-Identifier: MIT

import json
import logging
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from urllib.parse import urlparse

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage

from src.tools.crawl import crawl_tool
from src.llms.llm import get_llm_by_type
from src.config.agents import AGENT_LLM_MAP

logger = logging.getLogger(__name__)


@dataclass
class MCPServerInfo:
    """Information about an MCP server discovered from crawling."""
    name: str
    description: str
    repository_url: Optional[str]
    documentation_url: Optional[str]
    installation_instructions: Optional[str]
    usage_examples: Optional[str]
    available_tools: List[str]
    transport_type: Optional[str]  # stdio, sse, etc.
    command: Optional[str]
    args: Optional[List[str]]
    env_vars: Optional[Dict[str, str]]
    dependencies: List[str]
    raw_content: str


class MCPDiscoveryAgent:
    """Agent responsible for discovering and analyzing MCP servers from URLs."""
    
    def __init__(self, llm_type: str = "basic"):
        self.llm = get_llm_by_type(llm_type)
        
    async def discover_mcp_server(self, url: str) -> MCPServerInfo:
        """
        Discover MCP server information from a given URL.
        
        Args:
            url: URL to the MCP server repository or documentation
            
        Returns:
            MCPServerInfo object containing discovered information
        """
        logger.info(f"Starting MCP discovery for URL: {url}")
        
        # Crawl the URL to get content
        crawled_content = await self._crawl_url(url)
        
        # Extract MCP server information using LLM
        mcp_info = await self._extract_mcp_info(url, crawled_content)
        
        logger.info(f"Discovered MCP server: {mcp_info.name}")
        return mcp_info
    
    async def _crawl_url(self, url: str) -> str:
        """Crawl a URL to get its content."""
        try:
            result = crawl_tool(url)
            if isinstance(result, dict) and "crawled_content" in result:
                return result["crawled_content"]
            elif isinstance(result, str):
                return result
            else:
                logger.error(f"Unexpected crawl result format: {type(result)}")
                return str(result)
        except Exception as e:
            logger.error(f"Failed to crawl URL {url}: {e}")
            return f"Failed to crawl URL: {e}"
    
    async def _extract_mcp_info(self, url: str, content: str) -> MCPServerInfo:
        """Extract MCP server information from crawled content using LLM."""
        
        prompt = f"""
You are an expert at analyzing MCP (Model Context Protocol) servers. Analyze the following content from a URL and extract key information about the MCP server.

URL: {url}
Content:
{content[:8000]}  # Limit content length to avoid token limits

Please extract the following information and return it as a JSON object:

{{
    "name": "The name of the MCP server (e.g., 'github-trending-mcp', 'biomcp')",
    "description": "A brief description of what this MCP server does",
    "repository_url": "URL to the GitHub repository or source code",
    "documentation_url": "URL to documentation if different from the main URL",
    "installation_instructions": "How to install this MCP server (pip install, npm install, etc.)",
    "usage_examples": "Example commands or configuration for using this MCP server",
    "available_tools": ["list", "of", "tool", "names", "this", "server", "provides"],
    "transport_type": "stdio or sse",
    "command": "The command to run this MCP server (e.g., 'npx', 'python', 'uv')",
    "args": ["array", "of", "command", "arguments"],
    "env_vars": {{"ENV_VAR_NAME": "description of what this env var is for"}},
    "dependencies": ["list", "of", "required", "dependencies", "or", "packages"]
}}

If any information is not available or unclear, use null for that field. Focus on extracting practical information needed to integrate this MCP server into a system.
"""
        
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            
            # Try to parse JSON from the response
            content = response.content
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            
            if json_match:
                json_str = json_match.group()
                data = json.loads(json_str)
            else:
                # Fallback: try to extract information manually
                data = self._manual_extract_info(content, url)
            
            return MCPServerInfo(
                name=data.get("name", "unknown"),
                description=data.get("description", ""),
                repository_url=data.get("repository_url"),
                documentation_url=data.get("documentation_url"),
                installation_instructions=data.get("installation_instructions"),
                usage_examples=data.get("usage_examples"),
                available_tools=data.get("available_tools", []),
                transport_type=data.get("transport_type"),
                command=data.get("command"),
                args=data.get("args"),
                env_vars=data.get("env_vars", {}),
                dependencies=data.get("dependencies", []),
                raw_content=content
            )
            
        except Exception as e:
            logger.error(f"Failed to extract MCP info: {e}")
            # Return basic info as fallback
            return MCPServerInfo(
                name="unknown",
                description="Failed to extract information",
                repository_url=url,
                documentation_url=None,
                installation_instructions=None,
                usage_examples=None,
                available_tools=[],
                transport_type=None,
                command=None,
                args=None,
                env_vars={},
                dependencies=[],
                raw_content=content
            )
    
    def _manual_extract_info(self, content: str, url: str) -> Dict[str, Any]:
        """Manual extraction of MCP info as fallback."""
        data = {
            "name": "unknown",
            "description": "",
            "repository_url": url,
            "documentation_url": None,
            "installation_instructions": None,
            "usage_examples": None,
            "available_tools": [],
            "transport_type": "stdio",  # Default assumption
            "command": None,
            "args": None,
            "env_vars": {},
            "dependencies": []
        }
        
        # Try to extract name from URL or content
        if "github.com" in url:
            parts = url.split("/")
            if len(parts) >= 5:
                data["name"] = parts[-1].replace(".git", "").replace("-mcp", "").replace("mcp-", "")
        
        # Look for common patterns in content
        if "npm install" in content.lower():
            data["command"] = "npx"
        elif "pip install" in content.lower():
            data["command"] = "python"
        elif "uv" in content.lower():
            data["command"] = "uv"
        
        return data


@tool
async def discover_mcp_server_tool(
    url: str
) -> str:
    """
    Discover and analyze an MCP server from a given URL.
    
    Args:
        url: URL to the MCP server repository, documentation, or introduction page
        
    Returns:
        JSON string containing discovered MCP server information
    """
    try:
        agent = MCPDiscoveryAgent()
        mcp_info = await agent.discover_mcp_server(url)
        
        # Convert to dict for JSON serialization
        result = {
            "name": mcp_info.name,
            "description": mcp_info.description,
            "repository_url": mcp_info.repository_url,
            "documentation_url": mcp_info.documentation_url,
            "installation_instructions": mcp_info.installation_instructions,
            "usage_examples": mcp_info.usage_examples,
            "available_tools": mcp_info.available_tools,
            "transport_type": mcp_info.transport_type,
            "command": mcp_info.command,
            "args": mcp_info.args,
            "env_vars": mcp_info.env_vars,
            "dependencies": mcp_info.dependencies
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        error_msg = f"Failed to discover MCP server: {e}"
        logger.error(error_msg)
        return error_msg 