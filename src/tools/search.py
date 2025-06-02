# The project is built upon Bytedance MedDR
# SPDX-License-Identifier: MIT

import json
import logging
import os
from typing import Optional, List, Dict, Any

from langchain_community.tools import BraveSearch
from langchain_community.tools.arxiv import ArxivQueryRun
from langchain_community.utilities import ArxivAPIWrapper, BraveSearchWrapper
from langchain.tools import BaseTool
from langchain.callbacks.manager import CallbackManagerForToolRun
import requests
from datetime import datetime

from src.config import SearchEngine, SELECTED_SEARCH_ENGINE
# from src.tools.tavily_search.tavily_search_results_with_images import (
#     TavilySearchResultsWithImages,
# )

from src.tools.decorators import create_logged_tool

# Set up detailed logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

LoggedArxivSearch = create_logged_tool(ArxivQueryRun)

# Get the selected search tool
def get_web_search_tool(max_search_results: int):
    # logger.debug(f"Creating search tool with max_results={max_search_results}")
    
    return LoggedArxivSearch(
            name="web_search",
            api_wrapper=ArxivAPIWrapper(
                top_k_results=max_search_results,
                load_max_docs=max_search_results,
                load_all_available_meta=True,
            )
    )

if __name__ == "__main__":
    # Test the search tool with detailed logging
    logger.info("Starting search tool test")
    try:
        results = get_web_search_tool(max_search_results=3).invoke("latest developments in AI research")
        logger.info("Search completed successfully")
        print("\nSearch Results:")
        print(json.dumps(results, indent=2, ensure_ascii=False))
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", exc_info=True)
        print(f"\nTest failed with error: {str(e)}")
