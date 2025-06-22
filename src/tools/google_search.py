# Simple tool for google search and google scholar search

# The project is built upon Bytedance MedDR
# SPDX-License-Identifier: MIT

import os
import logging
# from scholarly import scholarly
from typing import Annotated, Dict, Any
from googleapiclient.discovery import build
from dotenv import load_dotenv
from langchain_core.tools import tool
from .decorators import log_io

logger = logging.getLogger(__name__)

load_dotenv()


def get_search_service():
    """Get Google Custom Search service."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable is not set.")
    return build("customsearch", "v1", developerKey=api_key)


@tool
@log_io
def get_web_search_tool(
    query: Annotated[str, "The search query to look up."],
    num_results: Annotated[int, "Number of results to return (max 10)."] = 1,
) -> Dict[str, Any]:
    """Use this to search the web using Google Custom Search API."""
    try:
        cse_id = os.getenv("GOOGLE_CSE_ID")
        if not cse_id:
            raise ValueError("GOOGLE_CSE_ID environment variable is not set.")

        service = get_search_service()
        response = (
            service.cse().list(q=query, cx=cse_id, num=min(num_results, 10)).execute()
        )

        items = response.get("items", [])
        if not items:
            return {"query": query, "results": []}

        results = []
        for item in items:
            results.append(
                {
                    "title": item.get("title", "No title"),
                    "link": item.get("link", "No link"),
                    "snippet": item.get("snippet", "No description"),
                    "domain": item.get("displayLink", ""),
                }
            )

        return {"query": query, "results": results}

    except Exception as e:
        error_msg = f"Failed to search. Error: {repr(e)}"
        logger.error(error_msg)
        return {"query": query, "error": error_msg}


# @tool
# def get_scholar_search_tool(query: str, num_results: int = 10) -> str:
#     """Perform a Google Scholar search using the scholarly package."""
#     try:
#         logger.info(f"Searching Google Scholar for: {query}")
#         search_query = scholarly.search_pubs(
#             query
#         )  # search_pubs is for publications ... decent but probably not the best choice
#         results = []

#         for i, pub in enumerate(search_query):
#             if i >= num_results:
#                 break
#             bib = pub.get("bib", {})
#             title = bib.get("title", "No title")
#             authors = ", ".join(bib.get("author", []))
#             year = bib.get("pub_year", "Unknown year")
#             venue = bib.get("venue", "Unknown venue")
#             abstract = bib.get("abstract", "No abstract available")

#             # These are in the main pub object
#             citations = pub.get("num_citations", 0)
#             url = pub.get("pub_url", "No URL available")

#             results.append(
#                 f"""
# {i+1}. {title}
#    Authors: {authors}
#    Year: {year}
#    Published in: {venue}
#    Citations: {citations} times
#    URL: {url}
#    Abstract: {abstract[:200]}{'...' if len(abstract) > 200 else ''}
# """
#             )

#         if not results:
#             return f"No Google Scholar results found for '{query}'."
#         return f"Google Scholar Results for '{query}':\n" + "\n".join(results)

#     except ImportError:
#         error_msg = "Google Scholar search requires the 'scholarly' package. Please install it with 'pip install scholarly'."
#         logger.error(error_msg)
#         return error_msg

#     except Exception as e:
#         error_msg = f"Failed to search. Error: {e}"
#         logger.error(error_msg)
#         return error_msg


# if __name__ == "__main__":
#     print(google_search.invoke("test query"))
