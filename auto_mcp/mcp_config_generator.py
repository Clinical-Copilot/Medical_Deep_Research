import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
from langchain_core.messages import HumanMessage
from src.llms.llm import get_llm_by_type
from src.tools.crawl import crawl_tool


def generate_mcp_config_from_markdown(markdown_content: str, llm_type: str = "basic") -> dict:
    """
    Generate MCP configuration from markdown content using LLM analysis.
    
    Args:
        markdown_content: String containing markdown content (README, documentation, etc.)
        llm_type: Type of LLM to use for analysis
        
    Returns:
        Dictionary with MCP configuration
    """
    llm = get_llm_by_type(llm_type)
    
    prompt = f"""
You are an expert at analyzing MCP (Model Context Protocol) server documentation and generating configuration files.

Analyze the following markdown content and extract MCP server information to generate a configuration dictionary.

Content to analyze:
{markdown_content}

Based on the content, generate a JSON configuration that follows this exact structure:

{{
    "mcp_servers": {{
        "server_name": {{
            "transport": "stdio",
            "command": "command_to_run_server",
            "args": ["array", "of", "command", "arguments"],
            "enabled_tools": ["tool1", "tool2"],
            "add_to_agents": ["researcher"]
        }}
    }}
}}

Key guidelines:
1. Extract the MCP server name from the content
2. Identify available tools/functions this MCP server provides
3. Always use "stdio" for transport
4. Determine the appropriate command based on installation instructions
5. Generate args based on actual usage examples in the documentation
6. Always set add_to_agents to ["researcher"]

Return ONLY the JSON configuration, no explanations or additional text.
"""
    
    response = llm.invoke([HumanMessage(content=prompt)])
    content = response.content.strip()
    
    # Extract JSON from the response
    json_start = content.find('{')
    json_end = content.rfind('}') + 1
    json_str = content[json_start:json_end]
    
    return json.loads(json_str)


# Example usage
if __name__ == "__main__":
    url = "https://github.com/genomoncology/biomcp?tab=readme-ov-file" 
    crawl_result = crawl_tool(url)
    markdown_content = crawl_result["crawled_content"] if isinstance(crawl_result, dict) and "crawled_content" in crawl_result else ""
    result = generate_mcp_config_from_markdown(markdown_content)
    print(json.dumps(result, indent=2)) 