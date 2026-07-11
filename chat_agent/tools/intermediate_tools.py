import html
import os
from typing import Any

import requests
from langchain_core.tools import tool

from tools.common import logger

SEARCH_USER_AGENT = os.getenv("SEARCH_USER_AGENT", "ChatAssistant/1.0")
SUPERDEV_API_URL = os.getenv("SUPER_DEV_URL", "https://api.superdev.ai/v1/search")
SUPERDEV_API_KEY = os.getenv("SUPER_DEV_API")

NEWS_API_URL = os.getenv("NEWS_API_URL", "https://newsapi.org/v2")
NEWS_API_KEY = os.getenv("NEWS_API_KEY") or os.getenv("NEWSAPI_KEY")


def _parse_superdev(data: dict, limit: int) -> list[dict[str, str]]:
    candidates = (
        data.get("results")
        or data.get("items")
        or (data.get("data") or {}).get("results")
        or (data.get("data") or {}).get("items")
        or (data.get("web") or {}).get("results")
        or data.get("organic")
        or []
    )
    results = []
    for item in candidates:
        if not isinstance(item, dict):
            continue
        title = item.get("title") or item.get("name") or item.get("headline") or "Result"
        link = item.get("url") or item.get("link") or item.get("href") or ""
        snippet = (
            item.get("snippet")
            or item.get("description")
            or item.get("summary")
            or item.get("content")
            or ""
        )
        results.append({"title": str(title), "link": str(link), "snippet": str(snippet)})
        if len(results) >= limit:
            break
    return results


def _search_superdev(query: str, limit: int) -> list[dict[str, str]]:
    if not SUPERDEV_API_KEY:
        raise ValueError("Missing SUPER_DEV_API environment variable.")
    headers = {
        "Authorization": f"Bearer {SUPERDEV_API_KEY}",
        "X-API-Key": SUPERDEV_API_KEY,
        "User-Agent": SEARCH_USER_AGENT,
        "Accept": "application/json",
    }
    resp = requests.get(
        SUPERDEV_API_URL,
        headers=headers,
        params={"q": query, "query": query, "num": limit, "limit": limit},
        timeout=12,
    )
    resp.raise_for_status()
    return _parse_superdev(resp.json(), limit)


def _search_wikipedia(query: str, limit: int) -> list[dict[str, str]]:
    resp = requests.get(
        "https://en.wikipedia.org/w/api.php",
        params={
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": limit,
            "utf8": 1,
            "format": "json",
        },
        headers={"User-Agent": SEARCH_USER_AGENT},
        timeout=12,
    )
    resp.raise_for_status()
    items = (resp.json().get("query") or {}).get("search") or []
    results = []
    for item in items[:limit]:
        title = item.get("title", "")
        slug = title.replace(" ", "_") if title else ""
        snippet = html.unescape(item.get("snippet", ""))
        snippet = snippet.replace('<span class="searchmatch">', "").replace("</span>", "")
        results.append({
            "title": title or "Wikipedia Result",
            "link": f"https://en.wikipedia.org/wiki/{slug}" if slug else "",
            "snippet": snippet,
        })
    return results


@tool
def google_search(query: str, num_results: int = 5) -> dict[str, Any]:
    """Search the web using Superdev API with Wikipedia as a fallback.

    Requires SUPER_DEV_API environment variable for Superdev. Falls back to
    Wikipedia automatically if Superdev fails or returns no results.

    Args:
        query: The search query string.
        num_results: Number of results to return (1–10, default 5).

    Returns:
        Dict with 'success' (bool), 'provider' (str), 'results' (list of
        {title, link, snippet} dicts), and 'count' (int).
    """
    query = (query or "").strip()
    if not query:
        return {"success": False, "error": "Query cannot be empty."}

    num_results = max(1, min(num_results, 10))

    # Try Superdev first
    try:
        results = _search_superdev(query, num_results)
        if results:
            logger.info(f"Superdev search: '{query}' → {len(results)} results")
            return {"success": True, "provider": "superdev", "query": query, "count": len(results), "results": results}
        logger.warning("Superdev returned no results, falling back to Wikipedia.")
    except Exception as e:
        logger.warning(f"Superdev failed ({e}), falling back to Wikipedia.")

    # Wikipedia fallback
    try:
        results = _search_wikipedia(query, num_results)
        logger.info(f"Wikipedia fallback: '{query}' → {len(results)} results")
        return {"success": True, "provider": "wikipedia", "query": query, "count": len(results), "results": results}
    except Exception as e:
        logger.error(f"Wikipedia fallback failed: {e}")
        return {"success": False, "error": f"Both Superdev and Wikipedia search failed: {e}", "results": []}


@tool
def get_news(
    query: str = "",
    category: str = "",
    country: str = "us",
    language: str = "en",
    num_results: int = 5,
) -> dict[str, Any]:
    """Get the latest news headlines by topic or category using NewsAPI.

    Requires NEWS_API_KEY (or NEWSAPI_KEY) environment variable.

    Args:
        query: Topic to search for. When provided, searches all articles.
        category: News category (business, technology, sports, etc.). Used only
                  when query is empty.
        country: Two-letter country code for top headlines (default 'us').
        language: Two-letter language code (default 'en').
        num_results: Number of articles to return (1–20, default 5).

    Returns:
        Dict with 'success' (bool), 'results' (list of {title, link, snippet,
        source, published_at} dicts), and metadata fields.
    """
    if not NEWS_API_KEY:
        return {"success": False, "error": "Missing NEWS_API_KEY environment variable."}

    num_results = max(1, min(num_results, 20))
    query = (query or "").strip()
    category = (category or "").strip().lower()
    country = (country or "us").strip().lower()
    language = (language or "en").strip().lower()

    headers = {"X-Api-Key": NEWS_API_KEY, "User-Agent": SEARCH_USER_AGENT}

    if query:
        endpoint = f"{NEWS_API_URL}/everything"
        params = {"q": query, "language": language, "pageSize": num_results, "sortBy": "publishedAt"}
    else:
        endpoint = f"{NEWS_API_URL}/top-headlines"
        params = {"country": country, "pageSize": num_results}
        if category:
            params["category"] = category

    try:
        resp = requests.get(endpoint, headers=headers, params=params, timeout=12)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        logger.error(f"NewsAPI request failed: {e}")
        return {"success": False, "error": str(e)}

    if data.get("status") != "ok":
        return {"success": False, "error": data.get("message", "NewsAPI request failed.")}

    results = []
    for article in (data.get("articles") or [])[:num_results]:
        results.append({
            "title": article.get("title", ""),
            "link": article.get("url", ""),
            "snippet": article.get("description") or article.get("content") or "",
            "source": ((article.get("source") or {}).get("name") or ""),
            "published_at": article.get("publishedAt", ""),
        })

    logger.info(f"NewsAPI: query='{query}', {len(results)} articles")
    return {
        "success": True,
        "provider": "newsapi",
        "query": query,
        "category": category,
        "country": country,
        "language": language,
        "count": len(results),
        "results": results,
    }
