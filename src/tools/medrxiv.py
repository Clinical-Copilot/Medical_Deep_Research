import logging
import asyncio
import requests
import re
import urllib.parse
import time
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Annotated

from langchain_core.tools import tool
from .decorators import log_io
from src.llms.llm import get_llm_by_type
from src.tools.bioportal import BioPortalStandardizer

logger = logging.getLogger(__name__)

def get_issn_from_doi(doi: str) -> str:
    """Return ISSN from a published DOI using CrossRef. If missing, return 'unpublished'."""
    if not doi:
        return "unpublished"
    url = f"https://api.crossref.org/works/{doi}"
    try:
        res = requests.get(url, timeout=5)
        res.raise_for_status()
        data = res.json()
        if "ISSN" in data["message"] and data["message"]["ISSN"]:
            return data["message"]["ISSN"][0]
        else:
            return "unpublished"
    except Exception:
        return "unpublished"


def parse_query(query: str, model) -> str:
    """Parse a natural language query into searchable keywords for MedRxiv."""
    prompt = f"""
        You are helping prepare search queries for a biomedical literature retrieval system (medRxiv).

        Given a free-text question or task, extract 3–7 **important biomedical keywords or phrases** that will help find relevant academic papers. Focus on drugs, diseases, symptoms, mechanisms, or study targets. Ignore vague words like "explore", "investigate", or "effect of".

        Return only a comma-separated list of keywords.

        Query: "{query}"
    """
    response = model.invoke(prompt)
    keywords = response.content.strip().replace(",", " ").split()
    return "+".join(keywords)


def clean_author_text(raw_text):
    """Clean and format author text from MedRxiv."""
    cleaned = re.sub(r"(View ORCID Profile)+", "", raw_text)
    cleaned = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", cleaned)
    cleaned = re.sub(r"(?<=[A-Z])\.?(?=[A-Z][a-z])", ". ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def extract_full_text_sections(soup: BeautifulSoup) -> str:
    """Extract all section headings and paragraphs from the full-text version of the article except for the abstract."""
    sections = []
    for div in soup.find_all("div", class_="section"):
        heading = div.find(["h2", "h3"])
        heading_text = heading.get_text(strip=True) if heading else "Section"

        if heading_text.lower().startswith("abstract"):
            continue

        paragraphs = div.find_all("p")
        body = " ".join(p.get_text(strip=True) for p in paragraphs)
        body = re.sub(r"\s+", " ", body)
        sections.append(f"--- {heading_text} ---\n{body}")
    return "\n\n".join(sections).strip()


def search_medrxiv(query: str, model, max_results=1):
    """Search MedRxiv for biomedical preprints based on the given query (already normalized upstream)."""
    keywords = parse_query(query, model)
    encoded_query = urllib.parse.quote(keywords)
    search_url = f"https://www.medrxiv.org/search/{encoded_query}%20numresults%3A{max_results}%20sort%3Arelevance-rank"

    response = requests.get(search_url)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch MedRxiv results: {response.status_code}")

    soup = BeautifulSoup(response.text, "html.parser")
    results = []

    articles = soup.find_all("div", class_="highwire-article-citation")
    for article in articles[:max_results]:
        try:
            title_tag = article.find("span", class_="highwire-cite-title")
            if not title_tag or not title_tag.find("a"):
                continue

            title = title_tag.text.strip()
            base_link = "https://www.medrxiv.org" + title_tag.find("a")["href"]
            full_link = base_link + ".full"

            # Fetch full text page
            time.sleep(0.5)
            article_page = requests.get(full_link)
            article_soup = BeautifulSoup(article_page.text, "html.parser")

            # DOI/ISSN if published
            doi_tag = article_soup.find("span", class_="highwire-cite-metadata-doi")
            published_doi = None
            issn = "unpublished"

            if doi_tag:
                doi_link = doi_tag.find("a")
                if doi_link and "doi.org" in doi_link["href"]:
                    published_doi = doi_link["href"].split("doi.org/")[-1].strip()
                    issn = get_issn_from_doi(published_doi)

            # Authors
            authors_tag = article_soup.find("div", class_="highwire-cite-authors")
            authors = ", ".join([
                clean_author_text(span.get_text(strip=True))
                for span in authors_tag.find_all("span", class_="highwire-citation-author")
            ]) if authors_tag else None

            # Journal (try to extract, else blank)
            journal = ""
            journal_tag = article_soup.find("span", class_="highwire-cite-metadata-journal")
            if journal_tag:
                journal = journal_tag.get_text(strip=True)
            else:
                meta_journal = article_soup.find("meta", attrs={"name": "citation_journal_title"})
                if meta_journal and meta_journal.get("content"):
                    journal = meta_journal["content"].strip()

            # Abstract
            abstract_div = article_soup.find("div", class_="section abstract")
            abstract = None
            if abstract_div:
                abstract_text = abstract_div.get_text(separator=" ", strip=True)
                abstract = abstract_text.replace("Abstract", "", 1).strip()

            # Date
            date = None
            for div in article_soup.find_all("div", class_="pane-content"):
                text = div.get_text(separator=" ", strip=True)
                match = re.search(r"Posted\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})", text)
                if match:
                    try:
                        date_obj = datetime.strptime(match.group(1), "%B %d, %Y")
                        date = date_obj.strftime("%Y-%m-%d")
                        break
                    except Exception:
                        continue

            # Full text
            full_text = extract_full_text_sections(article_soup)

            results.append({
                "title": title,
                "link": base_link,
                "abstract": abstract,
                "authors": authors,
                "date": date,
                "journal": journal,
                "full_text": full_text,
                "issn": issn
            })

        except Exception as e:
            logger.warning(f"Skipping article due to parsing error: {e}")

    return results


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
    - Normalizes the query via BioPortal (once) to anchor to ontology terms
    - Uses an LLM to extract keywords from the normalized query
    - Scrapes medRxiv.org for recent biomedical preprints
    - Returns paper title, abstract snippet, link, and publication date
    """
    try:
        # Normalize query via BioPortal
        standardizer = BioPortalStandardizer()
        _, updated_query, _ = standardizer.standardize_query(query)

        # Log only in backend
        logger.info(f"[MedRxiv] Updated Query used for search: {updated_query}")

        llm = get_llm_by_type("basic")

        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, lambda: search_medrxiv(updated_query, model=llm))

        if not results:
            return f"Updated Query: {updated_query}\nNo MedRxiv preprints found for this query."

        output = "\n\n".join(
            f"Link: {r['link']}\n"
            f"**{i+1}. {r['title']}**\n"
            f"*Authors:* {r['authors']}  \n"
            f"*Journal:* {r['journal']}  \n"
            f"*Date:* {r['date']}  \n"
            f"*ISSN:* {r['issn']}  \n"
            f"{r['abstract']}...\n"
            for i, r in enumerate(results[:5])
        )

        return f"Updated Query: {updated_query}\n\n" + output

    except Exception as e:
        error_msg = f"MedRxiv tool error: {str(e)}"
        logger.error(error_msg)
        return error_msg
