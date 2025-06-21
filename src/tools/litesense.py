import logging
import requests
from typing import Annotated

from langchain_core.tools import tool
from .decorators import log_io
from src.tools.decorators import process_queries
from src.utils.query_processor import QueryStrategy


logger = logging.getLogger(__name__)

## TODO: 
#  1. Try to improve my description of the tool (the current version might not be accurate)

@tool
@log_io
@process_queries(
    strategy=QueryStrategy.PARAPHRASE,
    max_variations=3
)
def litesense_tool(
    query: Annotated[str, "Free-text biomedical query (keywords, phrase, or question)."],
) -> str:
    """
    LitSense 2.0 semantic search
    - Vector-based retrieval over 38 M PubMed abstracts and 6.6 M PMC full-text articles  
    - Returns top ranked sentences or paragraphs (user’s query auto-matched to best level)  
    - Each hit includes passage text + metadata (PMID/PMCID, title, journal, year, rank)  
    Use to fetch compact, high-precision evidence from the biomedical literature.
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
            for i, p in enumerate(data[:5])
        ])

        return top_results

    except Exception as e:
        error_msg = f"LiteSense API error: {str(e)}"
        logger.error(error_msg)
        return error_msg