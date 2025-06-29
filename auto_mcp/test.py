import asyncio
from auto_mcp import AutoMCPOrchestrator

async def main():
    user_requirements = {
        "discovery_query": "site:github.com 'MCP server' biomedical medical health research",  
        "enabled_tools": ["search", "fetch"]  
    }
    
    # discovery_query: Change to search for different types (e.g., "weather", "finance", "code", etc.)
    # enabled_tools: Change to require different tools (e.g., ["read", "write"], ["analyze"], etc.)
    
    print("Starting MCP server discovery and validation...")
    print(f"Searching for: {user_requirements['discovery_query']}")
    print(f"Required tools: {user_requirements['enabled_tools']}")
    print("⏱This may take several minutes for discovery, Docker builds, and validation...")
    
    orchestrator = AutoMCPOrchestrator(user_requirements)
    result = await orchestrator.orchestrate()
    
    print("\n" + "="*60)
    print("ORCHESTRATION COMPLETE!")
    print("="*60)
    
    if result["success"]:
        print("SUCCESS: Found valid MCP config!")
        print(f"URL: {result['url']}")
        print(f"Config: {result['config']}")
    else:
        print("FAILED: No valid MCP config found.")
        print(f"Reason: {result['reason']}")
        
        if "candidates" in result:
            print("\nCandidate Details:")
            for i, candidate in enumerate(result["candidates"]):
                print(f"  {i+1}. {candidate['url']}")
                print(f"     Success: {candidate['success']}")
                print(f"     Crawl: {candidate['crawl_success']}")
                if candidate.get("validation_result"):
                    print(f"     Tools: {candidate['validation_result']['actual_tools']}")
    
    print("\nLogs:")
    for log_entry in result["logs"]:
        print(f"  [{log_entry.step}] {log_entry.message}")

if __name__ == "__main__":
    asyncio.run(main()) 