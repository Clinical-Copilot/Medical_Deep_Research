# The project is built upon Bytedance MedDR
# SPDX-License-Identifier: MIT

import logging
import os
import re
from typing import Annotated, List, Dict, Any, Set
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode, unquote
from openai import OpenAI
from dotenv import load_dotenv
from .decorators import log_io
from langchain_core.tools import tool
from src.tools.decorators import process_queries
from src.utils.query_processor import QueryStrategy

load_dotenv()
logger = logging.getLogger(__name__)


def _clean_urls(urls: List[str]) -> List[str]:
    """Return unique, canonical URLs with tracking junk removed."""
    _TRACKING_KEYS = {"gclid", "fbclid", "ref", "ref_src"}

    seen: set[str] = set()
    cleaned: List[str] = []

    for raw in urls:
        if not raw:
            continue

        raw = unquote(raw.strip())

        parts = urlsplit(raw)

        scheme = parts.scheme.lower() or "https"
        netloc = parts.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]

        path = parts.path.rstrip("/") or "/"

        query_items = [
            (k, v)
            for k, v in parse_qsl(parts.query, keep_blank_values=True)
            if not (k.lower().startswith("utm_") or k.lower() in _TRACKING_KEYS)
        ]
        query = urlencode(sorted(query_items), doseq=True)

        canonical = urlunsplit((scheme, netloc, path, query, ""))

        if canonical not in seen:
            seen.add(canonical)
            cleaned.append(canonical)

    return cleaned


def _extract_urls_from_text(text: str) -> List[str]:
    """Return every http(s) URL in free-form text."""
    return re.findall(r"https?://[^\s)>\]\}]+", text)


def _extract_urls_from_metadata(msg: Any) -> List[str]:
    """
    Handle both documented citation formats:
      1. message.metadata["citations"] = [{"url": "..."}]
      2. message.tool_calls[*].citation = {"url": "..."}
    """
    urls: List[str] = []

    meta = getattr(msg, "metadata", None) or {}
    for c in meta.get("citations", []):
        if isinstance(c, dict) and c.get("url"):
            urls.append(c["url"])

    tool_calls = getattr(msg, "tool_calls", None) or []
    for call in tool_calls:
        citation = getattr(call, "citation", None)
        if citation and isinstance(citation, dict) and citation.get("url"):
            urls.append(citation["url"])

    return urls


@tool
@log_io
@process_queries(strategy=QueryStrategy.PARAPHRASE, max_variations=3)
async def openai_search_tool(
    query: Annotated[str, "The search query to send to OpenAI."],
) -> Dict[str, Any]:
    """
    Run a web search via OpenAI and return:
        {
          "query":  str,
          "answer": str,
          "urls":   List[str]   # unique, cleaned
        }
    """
    try:
        client = OpenAI()

        completion = client.chat.completions.create(
            model="gpt-4o-mini-search-preview",
            web_search_options={"search_context_size": "high"},
            messages=[{"role": "user", "content": query}],
        )

        msg = completion.choices[0].message
        answer = msg.content
        urls = _extract_urls_from_metadata(msg) or _extract_urls_from_text(answer)
        urls = _clean_urls(urls)

        return {"query": query, "answer": answer, "urls": urls}

    except Exception as exc:
        error = f"OpenAI search failed: {exc!r}"
        logger.error(error)
        return {"error": error}
