import os
from googleapiclient.discovery import build

def test_google_search():
    # Use the same hardcoded values as in the implementation
    api_key = ""
    cse_id = ""
    
    try:
        # Build the service
        service = build("customsearch", "v1", developerKey=api_key)
        
        # Perform a test search
        print("Attempting to perform a test search...")
        response = service.cse().list(
            q="test query",
            cx=cse_id,
            num=1
        ).execute()
        
        # Process results similar to the actual implementation
        items = response.get("items", [])
        if not items:
            print("Warning: Search completed but no results were returned")
            return
            
        # Print the first result in a readable format
        first_result = items[0]
        print("\nSearch successful! First result:")
        print(f"Title: {first_result.get('title', 'No title')}")
        print(f"Link: {first_result.get('link', 'No link')}")
        print(f"Description: {first_result.get('snippet', 'No description')}")
        print(f"Domain: {first_result.get('displayLink', '')}")
            
    except Exception as e:
        print(f"Error: Search failed. Details: {e}")

if __name__ == "__main__":
    test_google_search() 