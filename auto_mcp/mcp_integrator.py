# The project is built upon Bytedance MedDR
# SPDX-License-Identifier: MIT

import json
import logging
import os
import shutil
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage

from src.llms.llm import get_llm_by_type

logger = logging.getLogger(__name__)


@dataclass
class IntegrationResult:
    """Result of MCP server integration."""
    success: bool
    server_name: str
    config_updated: bool
    files_created: List[str]
    errors: List[str]
    warnings: List[str]
    next_steps: List[str]


class MCPIntegrator:
    """Agent responsible for integrating validated MCP servers into the system."""
    
    def __init__(self, llm_type: str = "basic"):
        self.llm = get_llm_by_type(llm_type)
        self.project_root = Path(__file__).parent.parent.parent
        self.mcp_config_path = self.project_root / "mcp_config.json"
        self.auto_mcp_dir = self.project_root / "auto_mcp"
        
    async def integrate_mcp_server(
        self, 
        server_name: str, 
        scripts_json: str, 
        validation_result_json: str
    ) -> IntegrationResult:
        """
        Integrate a validated MCP server into the system.
        
        Args:
            server_name: Name of the MCP server to integrate
            scripts_json: JSON string containing generated scripts
            validation_result_json: JSON string containing validation results
            
        Returns:
            IntegrationResult object with integration results
        """
        logger.info(f"Starting integration of MCP server: {server_name}")
        
        try:
            # Parse inputs
            scripts_data = json.loads(scripts_json)
            validation_data = json.loads(validation_result_json)
            
            # Check if validation was successful
            if not validation_data.get("success", False):
                return IntegrationResult(
                    success=False,
                    server_name=server_name,
                    config_updated=False,
                    files_created=[],
                    errors=["Cannot integrate MCP server: validation failed"],
                    warnings=[],
                    next_steps=[]
                )
            
            # Create server directory
            server_dir = self.auto_mcp_dir / server_name
            server_dir.mkdir(parents=True, exist_ok=True)
            
            # Save generated files
            files_created = await self._save_generated_files(server_dir, scripts_data)
            
            # Update MCP configuration
            config_updated = await self._update_mcp_config(server_name, scripts_data)
            
            # Generate integration report
            next_steps = await self._generate_next_steps(server_name, validation_data)
            
            # Check for any issues
            errors = []
            warnings = []
            
            if not config_updated:
                errors.append("Failed to update MCP configuration")
            
            if validation_data.get("warnings"):
                warnings.extend(validation_data["warnings"])
            
            return IntegrationResult(
                success=True,
                server_name=server_name,
                config_updated=config_updated,
                files_created=files_created,
                errors=errors,
                warnings=warnings,
                next_steps=next_steps
            )
            
        except Exception as e:
            logger.error(f"Integration failed: {e}")
            return IntegrationResult(
                success=False,
                server_name=server_name,
                config_updated=False,
                files_created=[],
                errors=[f"Integration failed: {e}"],
                warnings=[],
                next_steps=[]
            )
    
    async def _save_generated_files(self, server_dir: Path, scripts_data: Dict[str, Any]) -> List[str]:
        """Save generated files to the server directory."""
        
        files_created = []
        
        try:
            # Save setup script
            if scripts_data.get("setup_script"):
                setup_file = server_dir / "setup.sh"
                with open(setup_file, "w") as f:
                    f.write(scripts_data["setup_script"])
                os.chmod(setup_file, 0o755)
                files_created.append(str(setup_file))
            
            # Save cleanup script
            if scripts_data.get("cleanup_script"):
                cleanup_file = server_dir / "cleanup.sh"
                with open(cleanup_file, "w") as f:
                    f.write(scripts_data["cleanup_script"])
                os.chmod(cleanup_file, 0o755)
                files_created.append(str(cleanup_file))
            
            # Save requirements.txt
            if scripts_data.get("requirements_file"):
                requirements_file = server_dir / "requirements.txt"
                with open(requirements_file, "w") as f:
                    f.write(scripts_data["requirements_file"])
                files_created.append(str(requirements_file))
            
            # Save package.json
            if scripts_data.get("package_json"):
                package_file = server_dir / "package.json"
                with open(package_file, "w") as f:
                    f.write(scripts_data["package_json"])
                files_created.append(str(package_file))
            
            # Save Dockerfile
            if scripts_data.get("dockerfile"):
                dockerfile = server_dir / "Dockerfile"
                with open(dockerfile, "w") as f:
                    f.write(scripts_data["dockerfile"])
                files_created.append(str(dockerfile))
            
            # Save server configuration
            if scripts_data.get("config_json"):
                config_file = server_dir / "server_config.json"
                with open(config_file, "w") as f:
                    json.dump(scripts_data["config_json"], f, indent=2)
                files_created.append(str(config_file))
            
            # Create README
            readme_content = self._generate_readme(scripts_data)
            readme_file = server_dir / "README.md"
            with open(readme_file, "w") as f:
                f.write(readme_content)
            files_created.append(str(readme_file))
            
            logger.info(f"Created {len(files_created)} files for MCP server")
            return files_created
            
        except Exception as e:
            logger.error(f"Failed to save generated files: {e}")
            return files_created
    
    async def _update_mcp_config(self, server_name: str, scripts_data: Dict[str, Any]) -> bool:
        """Update the main MCP configuration file."""
        
        try:
            # Load existing configuration
            if self.mcp_config_path.exists():
                with open(self.mcp_config_path, "r") as f:
                    config = json.load(f)
            else:
                config = {"mcp_servers": {}}
            
            # Add new server configuration
            server_config = scripts_data.get("config_json", {})
            config["mcp_servers"][server_name] = server_config
            
            # Save updated configuration
            with open(self.mcp_config_path, "w") as f:
                json.dump(config, f, indent=2)
            
            logger.info(f"Updated MCP configuration for server: {server_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update MCP configuration: {e}")
            return False
    
    def _generate_readme(self, scripts_data: Dict[str, Any]) -> str:
        """Generate a README file for the MCP server."""
        
        server_name = scripts_data.get("config_json", {}).get("command", "unknown")
        description = scripts_data.get("config_json", {}).get("description", "")
        
        readme = f"""# {server_name} MCP Server

This directory contains the automatically generated configuration and scripts for the {server_name} MCP server.

## Description

{description}

## Files

- `setup.sh` - Setup script for installing and configuring the MCP server
- `cleanup.sh` - Cleanup script for removing the MCP server and its dependencies
- `server_config.json` - MCP server configuration
- `requirements.txt` - Python dependencies (if applicable)
- `package.json` - Node.js dependencies (if applicable)
- `Dockerfile` - Docker configuration (if applicable)

## Quick Start

1. Run the setup script:
   ```bash
   ./setup.sh
   ```

2. The MCP server is now integrated into the system and available for use.

## Cleanup

To remove the MCP server:
```bash
./cleanup.sh
```

## Configuration

The server configuration is automatically added to `mcp_config.json` in the project root.

## Notes

This configuration was automatically generated. Please review the scripts before use in production environments.
"""
        
        return readme
    
    async def _generate_next_steps(self, server_name: str, validation_data: Dict[str, Any]) -> List[str]:
        """Generate next steps for the user."""
        
        prompt = f"""
Based on the successful integration of MCP server '{server_name}', provide 3-5 next steps for the user.

Validation Results:
- Setup Success: {validation_data.get('setup_success', False)}
- Test Success: {validation_data.get('test_success', False)}
- Cleanup Success: {validation_data.get('cleanup_success', False)}
- Errors: {validation_data.get('errors', [])}
- Warnings: {validation_data.get('warnings', [])}

Provide actionable next steps that the user should take to:
1. Test the integration
2. Configure the server
3. Use the MCP server in their workflow
4. Monitor and maintain the server

Return only the next steps as a JSON array of strings.
"""
        
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            content = response.content
            
            # Try to parse JSON from response
            import re
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            
            if json_match:
                next_steps = json.loads(json_match.group())
                return next_steps
            else:
                # Fallback: extract steps manually
                lines = content.split('\n')
                steps = []
                for line in lines:
                    line = line.strip()
                    if line.startswith('-') or line.startswith('•') or line.startswith('*'):
                        steps.append(line[1:].strip())
                    elif line and not line.startswith('Validation'):
                        steps.append(line)
                
                return steps[:5]  # Limit to 5 steps
                
        except Exception as e:
            logger.error(f"Failed to generate next steps: {e}")
            return [
                f"Test the {server_name} MCP server integration",
                "Review the generated scripts and configuration",
                "Add any required environment variables",
                "Restart the MedDR system to load the new MCP server"
            ]
    
    async def list_integrated_servers(self) -> Dict[str, Any]:
        """List all integrated MCP servers."""
        
        try:
            if not self.mcp_config_path.exists():
                return {"servers": [], "total": 0}
            
            with open(self.mcp_config_path, "r") as f:
                config = json.load(f)
            
            servers = []
            for server_name, server_config in config.get("mcp_servers", {}).items():
                server_dir = self.auto_mcp_dir / server_name
                
                server_info = {
                    "name": server_name,
                    "transport": server_config.get("transport"),
                    "command": server_config.get("command"),
                    "enabled_tools": server_config.get("enabled_tools", []),
                    "add_to_agents": server_config.get("add_to_agents", []),
                    "has_setup_script": (server_dir / "setup.sh").exists(),
                    "has_cleanup_script": (server_dir / "cleanup.sh").exists(),
                    "has_readme": (server_dir / "README.md").exists()
                }
                servers.append(server_info)
            
            return {
                "servers": servers,
                "total": len(servers)
            }
            
        except Exception as e:
            logger.error(f"Failed to list integrated servers: {e}")
            return {"servers": [], "total": 0, "error": str(e)}
    
    async def remove_mcp_server(self, server_name: str) -> bool:
        """Remove an integrated MCP server."""
        
        try:
            # Remove from configuration
            if self.mcp_config_path.exists():
                with open(self.mcp_config_path, "r") as f:
                    config = json.load(f)
                
                if server_name in config.get("mcp_servers", {}):
                    del config["mcp_servers"][server_name]
                    
                    with open(self.mcp_config_path, "w") as f:
                        json.dump(config, f, indent=2)
            
            # Remove server directory
            server_dir = self.auto_mcp_dir / server_name
            if server_dir.exists():
                shutil.rmtree(server_dir)
            
            logger.info(f"Removed MCP server: {server_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove MCP server {server_name}: {e}")
            return False


@tool
async def integrate_mcp_server_tool(
    server_name: str,
    scripts_json: str,
    validation_result_json: str
) -> str:
    """
    Integrate a validated MCP server into the system.
    
    Args:
        server_name: Name of the MCP server to integrate
        scripts_json: JSON string containing generated scripts
        validation_result_json: JSON string containing validation results
        
    Returns:
        JSON string containing integration results
    """
    try:
        integrator = MCPIntegrator()
        result = await integrator.integrate_mcp_server(server_name, scripts_json, validation_result_json)
        
        # Convert to dict for JSON serialization
        result_dict = {
            "success": result.success,
            "server_name": result.server_name,
            "config_updated": result.config_updated,
            "files_created": result.files_created,
            "errors": result.errors,
            "warnings": result.warnings,
            "next_steps": result.next_steps
        }
        
        return json.dumps(result_dict, indent=2)
        
    except Exception as e:
        error_msg = f"Failed to integrate MCP server: {e}"
        logger.error(error_msg)
        return error_msg


@tool
async def list_integrated_mcp_servers_tool() -> str:
    """
    List all integrated MCP servers.
    
    Returns:
        JSON string containing list of integrated servers
    """
    try:
        integrator = MCPIntegrator()
        result = await integrator.list_integrated_servers()
        return json.dumps(result, indent=2)
        
    except Exception as e:
        error_msg = f"Failed to list integrated servers: {e}"
        logger.error(error_msg)
        return error_msg


@tool
async def remove_mcp_server_tool(
    server_name: str
) -> str:
    """
    Remove an integrated MCP server.
    
    Args:
        server_name: Name of the MCP server to remove
        
    Returns:
        JSON string containing removal result
    """
    try:
        integrator = MCPIntegrator()
        success = await integrator.remove_mcp_server(server_name)
        
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