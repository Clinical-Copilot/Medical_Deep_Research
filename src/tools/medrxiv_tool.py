import logging
import asyncio
from typing import Annotated

from langchain_core.tools import tool
from .decorators import log_io
from src.tools.medrxiv_search import search_medrxiv
from src.llms.llm import get_llm_by_type

logger = logging.getLogger(__name__)

@tool
@log_io
async def medrxiv_tool(
    query: Annotated[
        str,
        "Free-text biomedical query (question, phrase, or research plan). Will be parsed into keyword search for MedRxiv.",
    ],
) -> str:
    """
    MedRxiv Preprint Search Tool
    - Uses an LLM to extract keywords from a natural-language query
    - Scrapes medRxiv.org for recent biomedical preprints
    - Returns paper title, abstract snippet, link, and publication date
    """
    try:
        llm = get_llm_by_type("basic")

        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, lambda: search_medrxiv(query, model=llm))

        if not results:
            return "No MedRxiv preprints found for this query."

        output = "\n\n".join(
            f"**{i+1}. {r['title']}**\n"
            f"*Authors:* {r['authors']}  \n"
            f"*Date:* {r['date']}  \n"
            f"{r['abstract']}...\n"
            f"[Read more]({r['link']})"
            for i, r in enumerate(results[:5])
        )


        return output

    except Exception as e:
        error_msg = f"MedRxiv tool error: {str(e)}"
        logger.error(error_msg)
        return error_msg
