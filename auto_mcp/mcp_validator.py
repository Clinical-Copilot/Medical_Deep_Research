# The project is built upon Bytedance MedDR
# SPDX-License-Identifier: MIT

import json
import logging
import subprocess
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
    """Simple MCP validator focused on tool alignment."""
    
    async def validate_tool_alignment(self, config_json: Dict[str, Any]) -> ToolAlignmentResult:
        """Validate that the MCP server provides the expected tools."""
        
        inputted_tools = config_json.get("enabled_tools", [])
        actual_tools = []
        
        try:
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
                        await session.initialize()
                        listed_tools = await session.list_tools()
                        return [tool.name for tool in listed_tools.tools]
            
            import asyncio
            return await get_tools()
            
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

if __name__ == "__main__":
    import asyncio
    import sys
    import json

    # Minimal default config for two servers
    DEFAULT_CONFIG = {
        "biomcp": {
            "transport": "stdio",
            "command": "uv",
            "args": ["run", "--with", "biomcp-python", "biomcp", "run"],
            "enabled_tools": ["search", "fetch"],
            "add_to_agents": ["researcher"]
        }
    }

    def load_servers():
        if len(sys.argv) > 1:
            arg = sys.argv[1]
            if arg.endswith('.json'):
                with open(arg, 'r') as f:
                    config = json.load(f)
            else:
                config = json.loads(arg)
            return config  # Must be {server_key: {...}}
        else:
            return DEFAULT_CONFIG

    async def main():
        servers = load_servers()
        for name, cfg in servers.items():
            print(f"\n=== {name} ===")
            print(json.dumps(cfg, indent=2))
            validator = MCPValidator()
            try:
                result = await validator.validate_tool_alignment(cfg)
                print(f"Inputted: {result.inputted_tools}")
                print(f"Actual:   {result.actual_tools}")
                print(f"Missing:  {result.missing_tools}")
            except Exception as e:
                print(f"❌ Error: {e}")

    asyncio.run(main()) 