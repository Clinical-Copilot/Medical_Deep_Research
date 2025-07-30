import logging
import aiohttp
import requests
import asyncio
from typing import Annotated, List

from langchain_core.tools import tool
from .decorators import log_io
from src.tools.medrxiv import search_medrxiv
from src.llms.llm import get_llm_by_type
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def get_issn_from_pmid(pmid_or_pmcid: str) -> dict:
    """Return both e-ISSN and p-ISSN from PubMed or PMC using efetch."""
    pmid_or_pmcid = str(pmid_or_pmcid)
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    db = "pmc" if pmid_or_pmcid.lower().startswith("pmc") else "pubmed"
    pmid_clean = pmid_or_pmcid.replace("PMC", "").replace("pmc", "")

    try:
        response = requests.get(url, params={
            "db": db,
            "id": pmid_clean,
            "retmode": "xml"
        }, timeout=5)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml-xml")

        result = {"e_issn": "N/A", "p_issn": "N/A"}

        for tag in soup.find_all(['ISSN', 'issn']):
            attr = tag.get("IssnType") or tag.get("pub-type")
            if attr:
                attr = attr.lower()
                if attr in ["electronic", "epub"]:
                    result["e_issn"] = tag.text.strip()
                elif attr in ["print", "ppub"]:
                    result["p_issn"] = tag.text.strip()

        return result
    except Exception as e:
        logger.warning(f"Failed to fetch ISSN from efetch for {pmid_or_pmcid}: {e}")
        return {"e_issn": "N/A", "p_issn": "N/A"}


async def query_litsense(query: str, top_k: int = 3) -> List[str]:
    """Query LitSense and return top_k formatted results with ISSN enrichment."""
    try:
        url = "https://www.ncbi.nlm.nih.gov/research/litsense2-api/api/passages/"
        params = {"query": query, "rerank": "true"}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                response.raise_for_status()
                data = await response.json()

        if not data:
            return []

        results = []
        for i, p in enumerate(data[:top_k]):
            try:
                pmid_or_pmcid = p.get("pmcid") or p.get("pmid")
                issns = await asyncio.to_thread(get_issn_from_pmid, pmid_or_pmcid) if pmid_or_pmcid else {"e_issn": "N/A", "p_issn": "N/A"}

                text = p.get("text", "").strip()
                section = p.get("section") or "N/A"
                score = p.get("score")
                score_str = f"{score:.3f}" if isinstance(score, (int, float)) else str(score) if score is not None else "N/A"

                formatted = (
                    f"{i+1}. {text}\n"
                    f"[PMID/PMCID: {pmid_or_pmcid}, e-ISSN: {issns['e_issn']}, p-ISSN: {issns['p_issn']}, "
                    f"Section: {section}, Score: {score_str}]"
                )
                results.append(formatted)
            except Exception as inner_e:
                logger.error(f"Error formatting LitSense result #{i}: {inner_e}, data={p}")
                continue

        return results

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
