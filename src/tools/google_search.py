# Simple tool for google search and google scholar search

import os
import logging
from scholarly import scholarly  
from typing import Optional, Dict, Any
from googleapiclient.discovery import build 
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

def get_search_service():
    """Get Google Custom Search service."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable is not set.") # remember to set environment variable 
    return build("customsearch", "v1", developerKey=api_key)    

@tool  
def google_search(query: str, num_results: int = 10) -> str:
    """Perform a Google search using Custom Search API."""
    try:
        cse_id = os.getenv("GOOGLE_CSE_ID")
        if not cse_id:
            raise ValueError("GOOGLE_CSE_ID environment variable is not set.")  # remember to set environment variable
        
        service = get_search_service()
        response = service.cse().list(
            q = query,
            cx = cse_id,
            num = min(num_results, 10)
        ).execute()
        
        items = response.get("items", [])
        if not items:
            return f"No search results found for {query}."
        
        formatted_results = [f"Google Search Results for: '{query}'\n"]
        for item in items:
            title = item.get("title", "No title")
            link = item.get("link", "No link")
            snippet = item.get("snippet", "No description")
            domain = item.get("displayLink", "")
            formatted_results.append(f"Title: {title}\nLink: {link}\nDescription: {snippet}\nDomain: {domain}\n")
            
        return "\n".join(formatted_results)
        
    except Exception as e:
        error_msg = f"Failed to search. Error: {e}"
        logger.error(error_msg)
        return error_msg


@tool 
def google_scholar_search(query: str, num_results: int = 10) -> str:
    """Perform a Google Scholar search using the scholarly package."""
    try:
        logger.info(f"Searching Google Scholar for: {query}")
        search_query = scholarly.search_pubs(query)   # search_pubs is for publications ... decent but probably not the best choice
        results = []
        
        for i, pub in enumerate(search_query):
            if i >= num_results:
                break
            bib = pub.get('bib', {})
            title = bib.get('title', 'No title')
            authors = ', '.join(bib.get('author', []))
            year = bib.get('pub_year', 'Unknown year')
            venue = bib.get('venue', 'Unknown venue')
            abstract = bib.get('abstract', 'No abstract available')
            
            # These are in the main pub object
            citations = pub.get('num_citations', 0)
            url = pub.get('pub_url', 'No URL available')
            
            results.append(f"""
{i+1}. {title}
   Authors: {authors}
   Year: {year}
   Published in: {venue}
   Citations: {citations} times
   URL: {url}
   Abstract: {abstract[:200]}{'...' if len(abstract) > 200 else ''}
""")
    
        if not results:
            return f"No Google Scholar results found for '{query}'."
        return f"Google Scholar Results for '{query}':\n" + "\n".join(results)
        
    except ImportError:
        error_msg = "Google Scholar search requires the 'scholarly' package. Please install it with 'pip install scholarly'."
        logger.error(error_msg)
        return error_msg
       
    except Exception as e:
        error_msg = f"Failed to search. Error: {e}"
        logger.error(error_msg)
        return error_msg