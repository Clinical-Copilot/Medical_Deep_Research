"""
Auto MCP Agent System

This module provides an automated system for discovering, analyzing, and integrating
MCP (Model Context Protocol) servers into the MedDR system.
"""

from .mcp_discovery_agent import MCPDiscoveryAgent
from .mcp_config_generator import generate_mcp_config_from_markdown
from .mcp_validator import MCPValidator, validate_tools_alignment
from .mcp_orchestrator import AutoMCPOrchestrator

__all__ = [
    # Classes
    "MCPDiscoveryAgent",
    "MCPValidator",
    
    # Functions
    "generate_mcp_config_from_markdown",
    
    # Tools
    "validate_tools_alignment",
    "AutoMCPOrchestrator"
] 