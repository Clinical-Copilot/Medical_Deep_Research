import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import urllib.parse
import time

def parse_query(query: str, model) -> str:
    prompt = f"""
        You are helping prepare search queries for a biomedical literature retrieval system (medRxiv).

        Given a free-text question or task, extract 3–7 **important biomedical keywords or phrases** that will help find relevant academic papers. Focus on drugs, diseases, symptoms, mechanisms, or study targets. Ignore vague words like "explore", "investigate", or "effect of".

        Return only a comma-separated list of keywords.

        Query: "{query}"
    """
    response = model.invoke(prompt)
    keywords = response.content.strip().replace(",", " ").split()
    return "+".join(keywords)

import re

def clean_author_text(raw_text):
    cleaned = re.sub(r"(View ORCID Profile)+", "", raw_text)
    cleaned = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", cleaned)
    cleaned = re.sub(r"(?<=[A-Z])\.?(?=[A-Z][a-z])", ". ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)

    return cleaned.strip()



def search_medrxiv(query: str, model, max_results=10):
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
            link = "https://www.medrxiv.org" + title_tag.find("a")["href"]

            # Fetch article page
            time.sleep(0.5)
            article_page = requests.get(link)
            article_soup = BeautifulSoup(article_page.text, "html.parser")

            # Authors
            authors_tag = article_soup.find("div", class_="highwire-cite-authors")
            authors = ", ".join([
                clean_author_text(span.get_text(strip=True))
                for span in authors_tag.find_all("span", class_="highwire-citation-author")
            ]) if authors_tag else None

            # Abstract
            abstract_div = article_soup.find("div", class_="section abstract")
            abstract = None
            if abstract_div:
                abstract_text = abstract_div.get_text(separator=" ", strip=True)
                abstract = abstract_text.replace("Abstract", "", 1).strip()

            # Date
            date = None
            for div in article_soup.find_all("div", class_="pane-content"):
                text = div.get_text(separator=" ", strip=True)  # normalize spacing
                match = re.search(r"Posted\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})", text)
                if match:
                    try:
                        date_obj = datetime.strptime(match.group(1), "%B %d, %Y")
                        date = date_obj.strftime("%Y-%m-%d")
                        break
                    except Exception:
                        continue

            results.append({
                "title": title,
                "link": link,
                "abstract": abstract,
                "authors": authors,
                "date": date
            })

        except Exception as e:
            print(f"[WARN] Skipping article due to parsing error: {e}")

    return results
