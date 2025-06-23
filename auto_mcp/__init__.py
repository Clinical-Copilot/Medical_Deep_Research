# The project is built upon Bytedance MedDR
# SPDX-License-Identifier: MIT

"""
Auto MCP Agent System

This module provides an automated system for discovering, analyzing, and integrating
MCP (Model Context Protocol) servers into the MedDR system.
"""

from .mcp_discovery_agent import MCPDiscoveryAgent, discover_mcp_server_tool
from .mcp_script_generator import MCPScriptGenerator, generate_mcp_scripts_tool
from .mcp_validator import MCPValidator, validate_tool_alignment_tool
from .mcp_integrator import MCPIntegrator, integrate_mcp_server_tool, list_integrated_mcp_servers_tool, remove_mcp_server_tool
from .mcp_orchestrator import MCPOrchestrator, orchestrate_mcp_integration_tool, list_all_mcp_servers_tool, remove_mcp_server_orchestrator_tool

__all__ = [
    # Classes
    "MCPDiscoveryAgent",
    "MCPScriptGenerator", 
    "MCPValidator",
    "MCPIntegrator",
    "MCPOrchestrator",
    
    # Tools
    "discover_mcp_server_tool",
    "generate_mcp_scripts_tool",
    "validate_tool_alignment_tool",
    "integrate_mcp_server_tool",
    "list_integrated_mcp_servers_tool",
    "remove_mcp_server_tool",
    "orchestrate_mcp_integration_tool",
    "list_all_mcp_servers_tool",
    "remove_mcp_server_orchestrator_tool"
] 