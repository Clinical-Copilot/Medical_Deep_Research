import logging
from typing import Annotated

from langchain_core.tools import tool
from .decorators import log_io

import requests

logger = logging.getLogger(__name__)

@tool
@log_io
def litesense_tool(query) -> str:
    """
    Searching using LiteSense 2.0 API.
    Returns top 3 passages.
    """
    try:
        url = "https://www.ncbi.nlm.nih.gov/research/litsense2-api/api/passages/"
        params = {"query": query, "rerank": "true"}
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if not data:
            return "No relevant passages found."

        top_results = "\n\n".join([
            f"{i+1}. {p['text'].strip()}\n[PMCID: {p.get('pmcid')}, Section: {p.get('section')}, Score: {p.get('score'):.3f}]"
            for i, p in enumerate(data[:3])
        ])

        return top_results

    except Exception as e:
        error_msg = f"LiteSense API error: {str(e)}"
        logger.error(error_msg)
        return error_msg