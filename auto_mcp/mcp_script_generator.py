# The project is built upon Bytedance MedDR
# SPDX-License-Identifier: MIT

import json
import logging
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage

from src.llms.llm import get_llm_by_type
from .mcp_discovery_agent import MCPServerInfo

logger = logging.getLogger(__name__)


@dataclass
class MCPScript:
    """Generated scripts for MCP server setup and cleanup."""
    setup_script: str
    cleanup_script: str
    config_json: Dict[str, Any]
    requirements_file: Optional[str]
    package_json: Optional[str]
    dockerfile: Optional[str]


class MCPScriptGenerator:
    """Agent responsible for generating setup and cleanup scripts for MCP servers."""
    
    def __init__(self, llm_type: str = "basic"):
        self.llm = get_llm_by_type(llm_type)
        
    async def generate_scripts(self, mcp_info: MCPServerInfo) -> MCPScript:
        """
        Generate setup and cleanup scripts for an MCP server.
        
        Args:
            mcp_info: Discovered MCP server information
            
        Returns:
            MCPScript object containing generated scripts
        """
        logger.info(f"Generating scripts for MCP server: {mcp_info.name}")
        
        # Generate setup script
        setup_script = await self._generate_setup_script(mcp_info)
        
        # Generate cleanup script
        cleanup_script = await self._generate_cleanup_script(mcp_info)
        
        # Generate configuration JSON
        config_json = await self._generate_config_json(mcp_info)
        
        # Generate additional files
        requirements_file = await self._generate_requirements_file(mcp_info)
        package_json = await self._generate_package_json(mcp_info)
        dockerfile = await self._generate_dockerfile(mcp_info)
        
        return MCPScript(
            setup_script=setup_script,
            cleanup_script=cleanup_script,
            config_json=config_json,
            requirements_file=requirements_file,
            package_json=package_json,
            dockerfile=dockerfile
        )
    
    async def _generate_setup_script(self, mcp_info: MCPServerInfo) -> str:
        """Generate setup script for the MCP server."""
        
        prompt = f"""
You are an expert at creating setup scripts for MCP servers. Create a comprehensive setup script for the following MCP server:

Server Name: {mcp_info.name}
Description: {mcp_info.description}
Installation Instructions: {mcp_info.installation_instructions}
Usage Examples: {mcp_info.usage_examples}
Dependencies: {mcp_info.dependencies}
Environment Variables: {mcp_info.env_vars}
Command: {mcp_info.command}
Arguments: {mcp_info.args}

Create a setup script that:
1. Installs all required dependencies
2. Sets up environment variables
3. Validates the installation
4. Tests the MCP server connection
5. Provides clear error messages and troubleshooting steps

The script should be:
- Cross-platform compatible (Windows, macOS, Linux)
- Include proper error handling
- Use best practices for dependency management
- Include validation steps

Return only the script content, no explanations.
"""
        
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            return response.content
        except Exception as e:
            logger.error(f"Failed to generate setup script: {e}")
            return self._generate_fallback_setup_script(mcp_info)
    
    async def _generate_cleanup_script(self, mcp_info: MCPServerInfo) -> str:
        """Generate cleanup script for the MCP server."""
        
        prompt = f"""
You are an expert at creating cleanup scripts for MCP servers. Create a comprehensive cleanup script for the following MCP server:

Server Name: {mcp_info.name}
Dependencies: {mcp_info.dependencies}
Environment Variables: {mcp_info.env_vars}

Create a cleanup script that:
1. Stops any running MCP server processes
2. Removes installed dependencies
3. Cleans up environment variables
4. Removes temporary files and directories
5. Provides clear feedback on what was cleaned up

The script should be:
- Cross-platform compatible (Windows, macOS, Linux)
- Include proper error handling
- Be safe to run multiple times
- Include validation steps

Return only the script content, no explanations.
"""
        
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            return response.content
        except Exception as e:
            logger.error(f"Failed to generate cleanup script: {e}")
            return self._generate_fallback_cleanup_script(mcp_info)
    
    async def _generate_config_json(self, mcp_info: MCPServerInfo) -> Dict[str, Any]:
        """Generate MCP configuration JSON in the format expected by mcp_config.json."""
        
        # Base configuration structure
        config = {
            "transport": mcp_info.transport_type or "stdio",
            "command": mcp_info.command,
            "args": mcp_info.args or [],
            "enabled_tools": mcp_info.available_tools,
            "add_to_agents": ["researcher"]  # Default to researcher agent
        }
        
        # Add environment variables if present
        if mcp_info.env_vars:
            config["env"] = mcp_info.env_vars
        
        return config
    
    async def _generate_requirements_file(self, mcp_info: MCPServerInfo) -> Optional[str]:
        """Generate requirements.txt file for Python dependencies."""
        
        if not mcp_info.dependencies:
            return None
            
        # Filter for Python packages
        python_deps = [dep for dep in mcp_info.dependencies if any(pkg in dep.lower() for pkg in ['pip', 'python', 'py'])]
        
        if not python_deps:
            return None
            
        prompt = f"""
Create a requirements.txt file for the following Python dependencies:

Dependencies: {python_deps}

Format each dependency on a new line with appropriate version constraints.
Use standard pip format (package==version or package>=version).
"""
        
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            return response.content
        except Exception as e:
            logger.error(f"Failed to generate requirements file: {e}")
            return None
    
    async def _generate_package_json(self, mcp_info: MCPServerInfo) -> Optional[str]:
        """Generate package.json file for Node.js dependencies."""
        
        if not mcp_info.dependencies:
            return None
            
        # Filter for Node.js packages
        node_deps = [dep for dep in mcp_info.dependencies if any(pkg in dep.lower() for pkg in ['npm', 'node', 'js'])]
        
        if not node_deps:
            return None
            
        prompt = f"""
Create a package.json file for the following Node.js dependencies:

Dependencies: {node_deps}
Server Name: {mcp_info.name}
Description: {mcp_info.description}

Create a valid package.json with:
- name, version, description
- dependencies section
- scripts section for setup/cleanup
- proper JSON formatting
"""
        
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            return response.content
        except Exception as e:
            logger.error(f"Failed to generate package.json: {e}")
            return None
    
    async def _generate_dockerfile(self, mcp_info: MCPServerInfo) -> Optional[str]:
        """Generate Dockerfile for containerized deployment."""
        
        prompt = f"""
Create a Dockerfile for the following MCP server:

Server Name: {mcp_info.name}
Description: {mcp_info.description}
Dependencies: {mcp_info.dependencies}
Command: {mcp_info.command}
Arguments: {mcp_info.args}
Environment Variables: {mcp_info.env_vars}

Create a Dockerfile that:
1. Uses an appropriate base image
2. Installs all dependencies
3. Sets up the MCP server
4. Exposes necessary ports
5. Sets up proper entrypoint

Return only the Dockerfile content, no explanations.
"""
        
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            return response.content
        except Exception as e:
            logger.error(f"Failed to generate Dockerfile: {e}")
            return None
    
    def _generate_fallback_setup_script(self, mcp_info: MCPServerInfo) -> str:
        """Generate a basic fallback setup script."""
        script = f"""#!/bin/bash
# Setup script for {mcp_info.name}
# Generated automatically - please review before use

set -e

echo "Setting up {mcp_info.name} MCP server..."

# Install dependencies
"""
        
        if mcp_info.dependencies:
            for dep in mcp_info.dependencies:
                script += f"echo \"Installing {dep}...\"\n"
                script += f"# TODO: Add installation command for {dep}\n"
        
        script += f"""
# Set environment variables
"""
        
        if mcp_info.env_vars:
            for var, desc in mcp_info.env_vars.items():
                script += f"# export {var}=<value>  # {desc}\n"
        
        script += f"""
# Test installation
echo "Testing {mcp_info.name} installation..."
# TODO: Add test command

echo "Setup complete for {mcp_info.name}"
"""
        
        return script
    
    def _generate_fallback_cleanup_script(self, mcp_info: MCPServerInfo) -> str:
        """Generate a basic fallback cleanup script."""
        script = f"""#!/bin/bash
# Cleanup script for {mcp_info.name}
# Generated automatically - please review before use

set -e

echo "Cleaning up {mcp_info.name} MCP server..."

# Stop any running processes
echo "Stopping {mcp_info.name} processes..."
# TODO: Add process stopping logic

# Remove dependencies
"""
        
        if mcp_info.dependencies:
            for dep in mcp_info.dependencies:
                script += f"echo \"Removing {dep}...\"\n"
                script += f"# TODO: Add removal command for {dep}\n"
        
        script += f"""
# Clean up environment variables
echo "Cleaning up environment variables..."
# TODO: Remove environment variables

echo "Cleanup complete for {mcp_info.name}"
"""
        
        return script


@tool
async def generate_mcp_scripts_tool(
    mcp_info_json: str
) -> str:
    """
    Generate setup and cleanup scripts for an MCP server.
    
    Args:
        mcp_info_json: JSON string containing MCP server information from discovery
        
    Returns:
        JSON string containing generated scripts and configuration
    """
    try:
        # Parse MCP info
        mcp_info_data = json.loads(mcp_info_json)
        mcp_info = MCPServerInfo(
            name=mcp_info_data.get("name", "unknown"),
            description=mcp_info_data.get("description", ""),
            repository_url=mcp_info_data.get("repository_url"),
            documentation_url=mcp_info_data.get("documentation_url"),
            installation_instructions=mcp_info_data.get("installation_instructions"),
            usage_examples=mcp_info_data.get("usage_examples"),
            available_tools=mcp_info_data.get("available_tools", []),
            transport_type=mcp_info_data.get("transport_type"),
            command=mcp_info_data.get("command"),
            args=mcp_info_data.get("args"),
            env_vars=mcp_info_data.get("env_vars", {}),
            dependencies=mcp_info_data.get("dependencies", []),
            raw_content=""
        )
        
        # Generate scripts
        generator = MCPScriptGenerator()
        scripts = await generator.generate_scripts(mcp_info)
        
        # Return results
        result = {
            "setup_script": scripts.setup_script,
            "cleanup_script": scripts.cleanup_script,
            "config_json": scripts.config_json,
            "requirements_file": scripts.requirements_file,
            "package_json": scripts.package_json,
            "dockerfile": scripts.dockerfile
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        error_msg = f"Failed to generate MCP scripts: {e}"
        logger.error(error_msg)
        return error_msg 