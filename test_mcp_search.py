from src.tools import mcp_google_search

def test_mcp_search():
    # Test a simple search
    query = "latest developments in AI"
    print(f"\nTesting MCP Google Search with query: '{query}'")
    
    try:
        results = mcp_google_search(query, num_results=3)
        print("\nSearch Results:")
        print(results)
    except Exception as e:
        print(f"Error occurred: {e}")

if __name__ == "__main__":
    test_mcp_search() 