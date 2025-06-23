# The project is built upon Bytedance MedDR
# SPDX-License-Identifier: MIT

"""
Auto MCP Agent System

This module provides an automated system for discovering, analyzing, and integrating
MCP (Model Context Protocol) servers into the MedDR system.
"""

from .mcp_discovery_agent import MCPDiscoveryAgent, discover_mcp_server_tool
from .mcp_config_generator import generate_mcp_config_from_markdown
from .mcp_validator import MCPValidator, validate_tools_alignment

__all__ = [
    # Classes
    "MCPDiscoveryAgent",
    "MCPValidator",
    
    # Functions
    "generate_mcp_config_from_markdown",
    
    # Tools
    "discover_mcp_server_tool",
    "validate_tools_alignment"
] 