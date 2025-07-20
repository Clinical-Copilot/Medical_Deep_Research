import logging
import asyncio
import requests
import re
import urllib.parse
import time
import xml.etree.ElementTree as ET
import os
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Annotated

from langchain_core.tools import tool
from .decorators import log_io
from src.llms.llm import get_llm_by_type

logger = logging.getLogger(__name__)

# PubMed API Configuration
PUBMED_API_KEY = os.getenv("PUBMED_API_KEY", "")
BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"


def parse_query(query: str, model) -> str:
    """Parse a natural language query into searchable keywords for PubMed."""
    prompt = f"""
        You are helping prepare search queries for a biomedical literature retrieval system (PubMed).

        Given a free-text question or task, extract 3–7 **important biomedical keywords or phrases** that will help find relevant academic papers. Focus on drugs, diseases, symptoms, mechanisms, or study targets. Ignore vague words like "explore", "investigate", or "effect of".

        Return only a comma-separated list of keywords.

        Query: "{query}"
    """
    response = model.invoke(prompt)
    keywords = response.content.strip().replace(",", " ").split()
    return "+".join(keywords)


def clean_author_text(raw_text):
    """Clean and format author text from PubMed."""
    cleaned = re.sub(r"\s+", " ", raw_text)
    return cleaned.strip()


def extract_abstract_from_xml(xml_content: str) -> str:
    """Extract abstract from PubMed XML response."""
    try:
        root = ET.fromstring(xml_content)
        abstract_elements = root.findall(".//AbstractText")
        if abstract_elements:
            abstract_parts = []
            for elem in abstract_elements:
                text = elem.text if elem.text else ""
                label = elem.get("Label", "")
                if label:
                    abstract_parts.append(f"{label}: {text}")
                else:
                    abstract_parts.append(text)
            return " ".join(abstract_parts).strip()
        return ""
    except Exception as e:
        logger.warning(f"Failed to parse XML abstract: {e}")
        return ""


def search_pubmed(query: str, model, max_results=1):
    """Search PubMed for biomedical literature based on the given query."""
    keywords = parse_query(query, model)
    encoded_query = urllib.parse.quote(keywords)
    
    # PubMed E-utilities API
    search_url = f"{BASE_URL}esearch.fcgi"
    search_params = {
        "db": "pubmed",
        "term": keywords,
        "retmax": max_results,
        "retmode": "json",
        "sort": "relevance"
    }
    
    # Add API key if available
    if PUBMED_API_KEY:
        search_params["api_key"] = PUBMED_API_KEY
    
    try:
        # Search for article IDs
        search_response = requests.get(search_url, params=search_params)
        search_response.raise_for_status()
        search_data = search_response.json()
        
        if "esearchresult" not in search_data or "idlist" not in search_data["esearchresult"]:
            return []
        
        pmids = search_data["esearchresult"]["idlist"]
        if not pmids:
            return []
        
        results = []
        
        # Fetch details for each PMID
        for pmid in pmids[:max_results]:
            try:
                # Fetch article details
                fetch_url = f"{BASE_URL}efetch.fcgi"
                fetch_params = {
                    "db": "pubmed",
                    "id": pmid,
                    "retmode": "xml"
                }
                
                # Add API key if available
                if PUBMED_API_KEY:
                    fetch_params["api_key"] = PUBMED_API_KEY
                
                # Rate limiting: faster with API key, slower without
                pause_time = 0.1 if PUBMED_API_KEY else 0.5
                time.sleep(pause_time)
                fetch_response = requests.get(fetch_url, params=fetch_params)
                fetch_response.raise_for_status()
                
                # Parse XML response
                root = ET.fromstring(fetch_response.text)
                article = root.find(".//PubmedArticle")
                
                if article is None:
                    continue
                
                # Extract title
                title_elem = article.find(".//ArticleTitle")
                title = title_elem.text if title_elem is not None and title_elem.text else "No title"
                
                # Extract authors
                authors = []
                author_list = article.find(".//AuthorList")
                if author_list is not None:
                    for author in author_list.findall("Author"):
                        last_name = author.find("LastName")
                        first_name = author.find("ForeName")
                        if last_name is not None and last_name.text:
                            author_name = last_name.text
                            if first_name is not None and first_name.text:
                                author_name = f"{first_name.text} {author_name}"
                            authors.append(author_name)
                
                authors_str = ", ".join(authors) if authors else "Unknown authors"
                
                # Extract abstract
                abstract = extract_abstract_from_xml(fetch_response.text)
                
                # Extract publication date
                pub_date = article.find(".//PubDate")
                date_str = "Unknown date"
                if pub_date is not None:
                    year_elem = pub_date.find("Year")
                    month_elem = pub_date.find("Month")
                    if year_elem is not None and year_elem.text:
                        date_str = year_elem.text
                        if month_elem is not None and month_elem.text:
                            date_str = f"{month_elem.text} {date_str}"
                
                # Extract journal info
                journal_elem = article.find(".//Journal/Title")
                journal = journal_elem.text if journal_elem is not None else "Unknown journal"
                
                # Create result
                result = {
                    "title": title,
                    "link": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    "abstract": abstract,
                    "authors": authors_str,
                    "date": date_str,
                    "journal": journal,
                    "pmid": pmid
                }
                
                results.append(result)
                
            except Exception as e:
                logger.warning(f"Skipping PMID {pmid} due to parsing error: {e}")
                continue
        
        return results
        
    except Exception as e:
        logger.error(f"PubMed search error: {e}")
        return []


@tool
@log_io
async def pubmed_tool(
    query: Annotated[
        str,
        "Free-text biomedical query (question, phrase, or research plan). Will be parsed into keyword search for PubMed.",
    ],
) -> str:
    """
    PubMed Literature Search Tool
    - Uses an LLM to extract keywords from a natural-language query
    - Searches PubMed for peer-reviewed biomedical literature
    - Returns paper title, abstract, authors, journal, and publication date
    """
    try:
        llm = get_llm_by_type("basic")

        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, lambda: search_pubmed(query, model=llm))

        if not results:
            return "No PubMed articles found for this query."

        output = "\n\n".join(
            f"Link: {r['link']}\n"
            f"**{i+1}. {r['title']}**\n"
            f"*Authors:* {r['authors']}  \n"
            f"*Journal:* {r['journal']}  \n"
            f"*Date:* {r['date']}  \n"
            f"*PMID:* {r['pmid']}  \n"
            f"{r['abstract']}"
            for i, r in enumerate(results[:5])
        )

        return output

    except Exception as e:
        error_msg = f"PubMed tool error: {str(e)}"
        logger.error(error_msg)
        return error_msg


if __name__ == "__main__":
    """Test the PubMed tool functionality."""
    import argparse
    
    async def test_pubmed():
        """Test the PubMed tool with a sample query."""
        parser = argparse.ArgumentParser(description="Test PubMed tool")
        parser.add_argument(
            "query",
            nargs="?",
            default="diabetes treatment guidelines",
            help="Biomedical query to search (default: 'diabetes treatment guidelines')"
        )
        args = parser.parse_args()
        
        print(f"🔍 Searching PubMed for: {args.query}")
        print("-" * 60)
        
        try:
            result = await pubmed_tool.ainvoke({"query": args.query})
            print("📄 Results:")
            print("=" * 60)
            print(result)
            print("=" * 60)
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Run the test
    asyncio.run(test_pubmed())
