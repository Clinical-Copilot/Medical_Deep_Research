# The project is built upon Bytedance MedDR
# SPDX-License-Identifier: MIT

import json
import logging
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage

from src.llms.llm import get_llm_by_type
from .mcp_discovery_agent import MCPDiscoveryAgent, discover_mcp_server_tool
from .mcp_script_generator import MCPScriptGenerator, generate_mcp_scripts_tool
from .mcp_validator import MCPValidator, validate_tool_alignment_tool
from .mcp_integrator import MCPIntegrator, integrate_mcp_server_tool, list_integrated_mcp_servers_tool

logger = logging.getLogger(__name__)


@dataclass
class OrchestrationResult:
    """Result of the complete MCP orchestration process."""
    success: bool
    server_name: str
    discovery_result: Optional[Dict[str, Any]]
    generation_result: Optional[Dict[str, Any]]
    validation_result: Optional[Dict[str, Any]]
    integration_result: Optional[Dict[str, Any]]
    errors: List[str]
    warnings: List[str]
    summary: str


class MCPOrchestrator:
    """Main orchestrator for the complete MCP server integration process."""
    
    def __init__(self, llm_type: str = "basic"):
        self.llm = get_llm_by_type(llm_type)
        self.discovery_agent = MCPDiscoveryAgent(llm_type)
        self.script_generator = MCPScriptGenerator(llm_type)
        self.validator = MCPValidator(llm_type)
        self.integrator = MCPIntegrator(llm_type)
        
    async def orchestrate_mcp_integration(self, url: str, server_name: Optional[str] = None) -> OrchestrationResult:
        """
        Orchestrate the complete MCP server integration process.
        
        Args:
            url: URL to the MCP server repository or documentation
            server_name: Optional custom name for the server
            
        Returns:
            OrchestrationResult object with complete process results
        """
        logger.info(f"Starting MCP orchestration for URL: {url}")
        
        errors = []
        warnings = []
        
        try:
            # Step 1: Discover MCP server information
            logger.info("Step 1: Discovering MCP server information...")
            discovery_result = await self._discover_mcp_server(url)
            
            if not discovery_result.get("success", False):
                errors.append("Failed to discover MCP server information")
                return self._create_failed_result(url, errors, warnings)
            
            # Extract server name if not provided
            if not server_name:
                server_name = discovery_result.get("name", "unknown")
            
            # Step 2: Generate scripts and configuration
            logger.info("Step 2: Generating scripts and configuration...")
            generation_result = await self._generate_scripts(discovery_result)
            
            if not generation_result.get("success", False):
                errors.append("Failed to generate scripts and configuration")
                return self._create_failed_result(server_name, errors, warnings)
            
            # Step 3: Validate generated scripts
            logger.info("Step 3: Validating generated scripts...")
            validation_result = await self._validate_scripts(generation_result)
            
            if not validation_result.get("success", False):
                warnings.append("Script validation failed, but continuing with integration")
            
            # Step 4: Integrate MCP server
            logger.info("Step 4: Integrating MCP server...")
            integration_result = await self._integrate_server(
                server_name, generation_result, validation_result
            )
            
            if not integration_result.get("success", False):
                errors.append("Failed to integrate MCP server")
            
            # Generate summary
            summary = await self._generate_summary(
                server_name, discovery_result, generation_result, 
                validation_result, integration_result, errors, warnings
            )
            
            return OrchestrationResult(
                success=len(errors) == 0,
                server_name=server_name,
                discovery_result=discovery_result,
                generation_result=generation_result,
                validation_result=validation_result,
                integration_result=integration_result,
                errors=errors,
                warnings=warnings,
                summary=summary
            )
            
        except Exception as e:
            error_msg = f"Orchestration failed: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
            return self._create_failed_result(url, errors, warnings)
    
    async def _discover_mcp_server(self, url: str) -> Dict[str, Any]:
        """Discover MCP server information."""
        try:
            mcp_info = await self.discovery_agent.discover_mcp_server(url)
            
            # Convert to dict for JSON serialization
            result = {
                "success": True,
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
            
            return result
            
        except Exception as e:
            logger.error(f"Discovery failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _generate_scripts(self, discovery_result: Dict[str, Any]) -> Dict[str, Any]:
        """Generate scripts and configuration."""
        try:
            # Convert discovery result back to MCPServerInfo format
            from .mcp_discovery_agent import MCPServerInfo
            
            mcp_info = MCPServerInfo(
                name=discovery_result.get("name", "unknown"),
                description=discovery_result.get("description", ""),
                repository_url=discovery_result.get("repository_url"),
                documentation_url=discovery_result.get("documentation_url"),
                installation_instructions=discovery_result.get("installation_instructions"),
                usage_examples=discovery_result.get("usage_examples"),
                available_tools=discovery_result.get("available_tools", []),
                transport_type=discovery_result.get("transport_type"),
                command=discovery_result.get("command"),
                args=discovery_result.get("args"),
                env_vars=discovery_result.get("env_vars", {}),
                dependencies=discovery_result.get("dependencies", []),
                raw_content=""
            )
            
            scripts = await self.script_generator.generate_scripts(mcp_info)
            
            result = {
                "success": True,
                "setup_script": scripts.setup_script,
                "cleanup_script": scripts.cleanup_script,
                "config_json": scripts.config_json,
                "requirements_file": scripts.requirements_file,
                "package_json": scripts.package_json,
                "dockerfile": scripts.dockerfile
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Script generation failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _validate_scripts(self, generation_result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate generated scripts."""
        try:
            # Convert generation result to JSON string for validation
            scripts_json = json.dumps(generation_result)
            validation_result = await self.validator.validate_scripts(scripts_json)
            
            # Convert to dict for JSON serialization
            result = {
                "success": validation_result.success,
                "setup_success": validation_result.setup_success,
                "test_success": validation_result.test_success,
                "cleanup_success": validation_result.cleanup_success,
                "tool_alignment": {
                    "aligned": validation_result.tool_alignment.aligned if validation_result.tool_alignment else None,
                    "expected_tools": validation_result.tool_alignment.expected_tools if validation_result.tool_alignment else [],
                    "actual_tools": validation_result.tool_alignment.actual_tools if validation_result.tool_alignment else [],
                    "missing_tools": validation_result.tool_alignment.missing_tools if validation_result.tool_alignment else [],
                    "extra_tools": validation_result.tool_alignment.extra_tools if validation_result.tool_alignment else [],
                    "alignment_score": validation_result.tool_alignment.alignment_score if validation_result.tool_alignment else 0.0,
                    "tool_details": validation_result.tool_alignment.tool_details if validation_result.tool_alignment else {}
                } if validation_result.tool_alignment else None,
                "errors": validation_result.errors,
                "warnings": validation_result.warnings,
                "test_output": validation_result.test_output,
                "suggestions": validation_result.suggestions
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _integrate_server(
        self, 
        server_name: str, 
        generation_result: Dict[str, Any], 
        validation_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Integrate the MCP server."""
        try:
            # Convert results to JSON strings for integration
            scripts_json = json.dumps(generation_result)
            validation_json = json.dumps(validation_result)
            
            integration_result = await self.integrator.integrate_mcp_server(
                server_name, scripts_json, validation_json
            )
            
            # Convert to dict for JSON serialization
            result = {
                "success": integration_result.success,
                "server_name": integration_result.server_name,
                "config_updated": integration_result.config_updated,
                "files_created": integration_result.files_created,
                "errors": integration_result.errors,
                "warnings": integration_result.warnings,
                "next_steps": integration_result.next_steps
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Integration failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _generate_summary(
        self,
        server_name: str,
        discovery_result: Optional[Dict[str, Any]],
        generation_result: Optional[Dict[str, Any]],
        validation_result: Optional[Dict[str, Any]],
        integration_result: Optional[Dict[str, Any]],
        errors: List[str],
        warnings: List[str]
    ) -> str:
        """Generate a summary of the orchestration process."""
        
        # Extract tool alignment information
        tool_alignment_info = ""
        if validation_result and validation_result.get("tool_alignment"):
            alignment = validation_result["tool_alignment"]
            tool_alignment_info = f"""
Tool Alignment:
- Alignment Score: {alignment.get('alignment_score', 0.0):.2f}
- Expected Tools: {alignment.get('expected_tools', [])}
- Actual Tools: {alignment.get('actual_tools', [])}
- Missing Tools: {alignment.get('missing_tools', [])}
- Extra Tools: {alignment.get('extra_tools', [])}
- Aligned: {'Yes' if alignment.get('aligned', False) else 'No'}
"""
        
        prompt = f"""
Generate a comprehensive summary of the MCP server integration process for '{server_name}':

Process Results:
- Discovery: {'Success' if discovery_result and discovery_result.get('success') else 'Failed'}
- Script Generation: {'Success' if generation_result and generation_result.get('success') else 'Failed'}
- Validation: {'Success' if validation_result and validation_result.get('success') else 'Failed'}
- Integration: {'Success' if integration_result and integration_result.get('success') else 'Failed'}

Errors: {errors}
Warnings: {warnings}

Server Information:
- Name: {server_name}
- Description: {discovery_result.get('description', 'N/A') if discovery_result else 'N/A'}
- Available Tools: {discovery_result.get('available_tools', []) if discovery_result else []}
- Transport: {discovery_result.get('transport_type', 'N/A') if discovery_result else 'N/A'}

Files Created: {integration_result.get('files_created', []) if integration_result else []}
Next Steps: {integration_result.get('next_steps', []) if integration_result else []}
{tool_alignment_info}

Provide a clear, concise summary that includes:
1. Overall success/failure status
2. Key achievements
3. Tool alignment assessment (if applicable)
4. Any issues encountered
5. Next steps for the user
6. Recommendations

Format the summary in markdown with clear sections.
"""
        
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            return response.content
        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            return f"Integration process completed for {server_name}. Check the detailed results for more information."
    
    def _create_failed_result(self, server_name: str, errors: List[str], warnings: List[str]) -> OrchestrationResult:
        """Create a failed result object."""
        return OrchestrationResult(
            success=False,
            server_name=server_name,
            discovery_result=None,
            generation_result=None,
            validation_result=None,
            integration_result=None,
            errors=errors,
            warnings=warnings,
            summary=f"Integration failed for {server_name}. Errors: {', '.join(errors)}"
        )
    
    async def list_all_integrated_servers(self) -> Dict[str, Any]:
        """List all integrated MCP servers."""
        return await self.integrator.list_integrated_servers()
    
    async def remove_integrated_server(self, server_name: str) -> bool:
        """Remove an integrated MCP server."""
        return await self.integrator.remove_mcp_server(server_name)


@tool
async def orchestrate_mcp_integration_tool(
    url: str,
    server_name: Optional[str] = None
) -> str:
    """
    Orchestrate the complete MCP server integration process.
    
    This tool performs the full pipeline:
    1. Discovers MCP server information from the URL
    2. Generates setup and cleanup scripts
    3. Validates the scripts in an isolated environment
    4. Integrates the server into the system
    
    Args:
        url: URL to the MCP server repository, documentation, or introduction page
        server_name: Optional custom name for the server (if not provided, will be extracted from discovery)
        
    Returns:
        JSON string containing complete orchestration results
    """
    try:
        orchestrator = MCPOrchestrator()
        result = await orchestrator.orchestrate_mcp_integration(url, server_name)
        
        # Convert to dict for JSON serialization
        result_dict = {
            "success": result.success,
            "server_name": result.server_name,
            "discovery_result": result.discovery_result,
            "generation_result": result.generation_result,
            "validation_result": result.validation_result,
            "integration_result": result.integration_result,
            "errors": result.errors,
            "warnings": result.warnings,
            "summary": result.summary
        }
        
        return json.dumps(result_dict, indent=2)
        
    except Exception as e:
        error_msg = f"Orchestration failed: {e}"
        logger.error(error_msg)
        return error_msg


@tool
async def list_all_mcp_servers_tool() -> str:
    """
    List all integrated MCP servers in the system.
    
    Returns:
        JSON string containing list of all integrated servers
    """
    try:
        orchestrator = MCPOrchestrator()
        result = await orchestrator.list_all_integrated_servers()
        return json.dumps(result, indent=2)
        
    except Exception as e:
        error_msg = f"Failed to list MCP servers: {e}"
        logger.error(error_msg)
        return error_msg


@tool
async def remove_mcp_server_orchestrator_tool(
    server_name: str
) -> str:
    """
    Remove an integrated MCP server from the system.
    
    Args:
        server_name: Name of the MCP server to remove
        
    Returns:
        JSON string containing removal result
    """
    try:
        orchestrator = MCPOrchestrator()
        success = await orchestrator.remove_integrated_server(server_name)
        
        result = {
            "success": success,
            "server_name": server_name,
            "message": f"MCP server '{server_name}' {'removed successfully' if success else 'failed to remove'}"
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        error_msg = f"Failed to remove MCP server: {e}"
        logger.error(error_msg)
        return error_msg 