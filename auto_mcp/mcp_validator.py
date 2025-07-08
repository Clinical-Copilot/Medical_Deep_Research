import json
import logging
import subprocess
import asyncio
import tempfile
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

@dataclass
class ToolAlignmentResult:
    """Result of tool alignment validation."""
    inputted_tools: List[str]
    actual_tools: List[str]
    missing_tools: List[str]


class MCPValidator:
    """Simple MCP validator focused on tool alignment with Docker support."""
    
    async def validate_tool_alignment(self, config_json: Dict[str, Any]) -> ToolAlignmentResult:
        """Validate that the MCP server provides the expected tools."""
        
        inputted_tools = config_json.get("enabled_tools", [])
        actual_tools = []
        
        try:
            # Check if this is a Docker-based config
            if config_json.get("use_docker", False) and config_json.get("repo_url"):
                # Use Docker-based method
                actual_tools = await self._query_mcp_tools_docker(config_json)
            else:
                # Use original stdio method
                actual_tools = await self._query_mcp_tools(config_json)
        except Exception as e:
            logger.error(f"Failed to query MCP tools: {e}")
        
        inputted_set = set(inputted_tools)
        actual_set = set(actual_tools)
        
        missing_tools = list(inputted_set - actual_set)
        
        return ToolAlignmentResult(
            inputted_tools=inputted_tools,
            actual_tools=actual_tools,
            missing_tools=missing_tools
        )
    
    async def _query_mcp_tools(self, config_json: Dict[str, Any]) -> List[str]:
        """Query the MCP server for available tools."""
        
        command = config_json.get("command")
        args = config_json.get("args", [])
        
        if not command:
            return []
        
        try:
            # Try to get tools using MCP client
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
            
            server_params = StdioServerParameters(
                command=command,
                args=args,
                env=config_json.get("env", {})
            )
            
            async def get_tools():
                async with stdio_client(server_params) as (read, write):
                    async with ClientSession(read, write) as session:
                        try:
                            await asyncio.wait_for(session.initialize(), timeout=20)
                        except asyncio.TimeoutError:
                            logger.error("MCP client handshake (initialize) timed out.")
                            return []
                        try:
                            listed_tools = await asyncio.wait_for(session.list_tools(), timeout=15)
                        except asyncio.TimeoutError:
                            logger.error("MCP client list_tools timed out.")
                            return []
                        return [tool.name for tool in listed_tools.tools]
            
            try:
                return await asyncio.wait_for(get_tools(), timeout=20.0)
            except asyncio.TimeoutError:
                logger.warning("MCP server connection timed out completely")
                return []
            
        except ImportError:
            logger.warning("MCP client not available, using fallback method")
            return await self._query_tools_fallback(command, args)
        except Exception as e:
            logger.error(f"MCP client query failed: {e}")
            return await self._query_tools_fallback(command, args)
    
    async def _query_tools_fallback(self, command: str, args: List[str]) -> List[str]:
        """Fallback method to query tools using command line."""
        
        try:
            # Try common MCP server commands
            test_commands = [
                [command] + args + ["--help"],
                [command] + args + ["--tools"],
                [command] + args + ["list-tools"],
                [command] + args + ["tools"]
            ]
            
            for cmd in test_commands:
                try:
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    if result.returncode == 0:
                        # Simple pattern matching for tool names
                        import re
                        output = result.stdout.lower()
                        
                        # Look for tool names in output
                        tool_patterns = [
                            r"tool[s]?[\\s\\-]*:?\\s*([a-zA-Z_][a-zA-Z0-9_]*[,\\s]*)",
                            r"available[\\s\\-]*tool[s]?[\\s\\-]*:?\\s*([a-zA-Z_][a-zA-Z0-9_]*[,\\s]*)",
                            r"\\b([a-zA-Z_][a-zA-Z0-9_]*)\\s*\\(tool\\)"
                        ]
                        
                        tools = []
                        for pattern in tool_patterns:
                            matches = re.findall(pattern, output)
                            tools.extend([m.strip() for m in matches if m.strip()])
                        
                        if tools:
                            return list(set(tools))
                            
                except subprocess.TimeoutExpired:
                    continue
                except Exception:
                    continue
            
            return []
            
        except Exception as e:
            logger.error(f"Fallback query failed: {e}")
            return []

    async def _build_docker_container(self, repo_url: str, markdown_content: str = "") -> Optional[str]:
        """Build a Docker container for the MCP server from the repo URL."""
        try:
            # Extract repo name from URL for Docker image name
            repo_name = repo_url.split('/')[-1].replace('.git', '').lower()
            image_name = f"mcp-{repo_name}:latest"
            
            # Create temporary directory for cloning
            with tempfile.TemporaryDirectory() as temp_dir:
                logger.info(f"Cloning {repo_url} to {temp_dir}")
                
                # Clone the repo
                clone_result = subprocess.run(
                    ["git", "clone", repo_url, temp_dir],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if clone_result.returncode != 0:
                    logger.error(f"Failed to clone: {clone_result.stderr}")
                    return None
                
                # Check if Dockerfile exists, if not create a generic one
                dockerfile_path = os.path.join(temp_dir, "Dockerfile")
                if not os.path.exists(dockerfile_path):
                    logger.info("Creating generic Dockerfile")
                    await self._create_generic_dockerfile(temp_dir, markdown_content)
                
                # Build Docker image
                logger.info(f"Building Docker image: {image_name}")
                build_result = subprocess.run(
                    ["docker", "build", "-t", image_name, temp_dir],
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minutes for build
                )
                
                if build_result.returncode != 0:
                    logger.error(f"Failed to build: {build_result.stderr}")
                    return None
                
                logger.info(f"Successfully built {image_name}")
                return image_name
                
        except Exception as e:
            logger.error(f"Docker error: {str(e)}")
            return None

    async def _create_generic_dockerfile(self, temp_dir: str, markdown_content: str) -> None:
        """Create a generic Dockerfile for MCP servers that don't have one."""
        # Try to extract Python requirements from markdown content
        requirements = []
        if "requirements.txt" in markdown_content:
            # Simple heuristic - look for common Python packages
            common_packages = ["requests", "fastapi", "uvicorn", "pydantic", "mcp"]
            for package in common_packages:
                if package in markdown_content.lower():
                    requirements.append(package)
        
        dockerfile_content = f"""FROM python:3.11-slim

WORKDIR /app

# Install git for cloning
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Copy requirements if they exist
COPY requirements.txt* ./
RUN pip install --no-cache-dir -r requirements.txt 2>/dev/null || true

# Install additional common packages
RUN pip install --no-cache-dir {' '.join(requirements)}

# Copy the application
COPY . .

# Try to find and run the MCP server
CMD ["python", "-m", "mcp", "run"] || ["python", "main.py"] || ["python", "server.py"] || ["python", "-c", "print('MCP server not found')"]
"""
        
        with open(os.path.join(temp_dir, "Dockerfile"), "w") as f:
            f.write(dockerfile_content)

    async def _query_mcp_tools_docker(self, config_json: Dict[str, Any]) -> List[str]:
        """Query MCP tools using Docker container."""
        repo_url = config_json.get("repo_url")
        markdown_content = config_json.get("markdown_content", "")
        
        if not repo_url:
            return []
        
        # Build Docker container
        image_name = await self._build_docker_container(repo_url, markdown_content)
        if not image_name:
            return []
        
        # Convert to Docker config
        docker_config = config_json.copy()
        docker_config["command"] = "docker"
        docker_config["args"] = ["run", "--rm", "-i", image_name]
        
        # Add original command args if they exist
        if "original_args" in config_json:
            docker_config["args"].extend(config_json["original_args"])
        
        # Query tools using Docker
        return await self._query_mcp_tools(docker_config)


@tool
async def validate_tools_alignment(
    config_json: str
) -> str:
    """
    Validate tool alignment for an MCP server configuration.
    
    Args:
        config_json: JSON string containing MCP server configuration
        
    Returns:
        JSON string containing tool alignment validation results
    """
    try:
        validator = MCPValidator()
        config_data = json.loads(config_json)
        
        result = await validator.validate_tool_alignment(config_data)
        
        result_dict = {
            "inputted_tools": result.inputted_tools,
            "actual_tools": result.actual_tools,
            "missing_tools": result.missing_tools
        }
        
        return json.dumps(result_dict, indent=2)
        
    except Exception as e:
        error_msg = f"Failed to validate tool alignment: {e}"
        logger.error(error_msg)
        return error_msg 