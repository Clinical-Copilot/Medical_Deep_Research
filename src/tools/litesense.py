import logging
import aiohttp
from typing import Annotated, List

from langchain_core.tools import tool
from .decorators import log_io
from src.tools.medrxiv import search_medrxiv
from src.llms.llm import get_llm_by_type

logger = logging.getLogger(__name__)


async def query_litsense(query: str, top_k: int = 3) -> List[str]:
    """Query LitSense and return top_k formatted results."""
    try:
        url = "https://www.ncbi.nlm.nih.gov/research/litsense2-api/api/passages/"
        params = {"query": query, "rerank": "true"}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                response.raise_for_status()
                data = await response.json()

        if not data:
            return []

        return [
            f"{i+1}. {p['text'].strip()}\n[PMCID: {p.get('pmcid')}, Section: {p.get('section')}, Score: {p.get('score'):.3f}]"
            for i, p in enumerate(data[:top_k])
        ]

    except Exception as e:
        logger.error(f"LiteSense API error: {str(e)}")
        return []


def extract_key_sentences_from_abstract(abstract: str) -> str:
    """Use an LLM to extract biomedical keywords from a medRxiv abstract."""
    llm = get_llm_by_type("basic")
    prompt = f"""
        You are helping prepare search queries for a biomedical literature retrieval system (LitSense).

        Given the abstract below, extract 1-2 key ideas that are presented in this paper.
        Ignore background information, similar literature, and other information that is not the main focus of the paper.

        Abstract:
        {abstract}

        Output (comma-separated):"""
    response = llm.invoke(prompt)
    content = response.content.strip() if hasattr(response, "content") else str(response).strip()

    # print("\nKey sentences extracted from abstract:")
    # print(content, "\n")
    return content


@tool
@log_io
async def litesense_tool(
    query: Annotated[
        str, "Free-text biomedical query. Uses both raw query and top medRxiv abstract to retrieve LitSense results."
    ]
) -> str:
    """
    LitSense 2.0 semantic search:
    - Strategy 1: Direct search using user query.
    - Strategy 2: medRxiv search → extract keywords from abstract → search LitSense.
    - Combines top 3 passages from each strategy.
    """
    try:
        # Direct query to LitSense
        direct_query = await query_litsense(query, top_k=3)

        # Get medRxiv abstract and extract keywords
        llm = get_llm_by_type("basic")
        medrxiv_results = search_medrxiv(query, model=llm, max_results=1)
        abstract = medrxiv_results[0]["abstract"] if medrxiv_results else ""
        if not abstract:
            abstract_query = []
        else:
            key_sentences = extract_key_sentences_from_abstract(abstract)
            abstract_query = await query_litsense(key_sentences, top_k=3)

        # Format output
        output = ""
        if direct_query:
            output += "### LitSense Results (Direct Query)\n\n" + "\n\n".join(direct_query) + "\n\n"
        else:
            output += "### LitSense Results (Direct Query)\n\nNo results found.\n\n"

        if abstract_query:
            output += "### LitSense Results (From medRxiv Abstract)\n\n" + "\n\n".join(abstract_query)
        else:
            output += "### LitSense Results (From medRxiv Abstract)\n\nNo results found."

        return output

    except Exception as e:
        logger.error(f"Combined LitSense query error: {str(e)}")
        return f"LitSense query failed: {str(e)}"
