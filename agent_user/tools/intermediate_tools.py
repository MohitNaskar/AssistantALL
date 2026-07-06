# importing the libraries
import html
import os
from typing import Any, Dict, List

import httpx
from livekit.agents import llm

from .common import logger

# Constants for search and news APIs
SEARCH_USER_AGENT = os.getenv(
    "SEARCH_USER_AGENT", "VoiceAssistant/1.0 (+https://example.com/contact)"
)
SUPERDEV_API_URL = os.getenv("SUPER_DEV_URL", "https://api.superdev.ai/v1/search")
SUPERDEV_API_KEY = os.getenv("SUPER_DEV_API")

NEWS_API_URL = os.getenv("NEWS_API_URL", "https://newsapi.org/v2")
NEWS_API_KEY = os.getenv("NEWS_API_KEY") or os.getenv("NEWSAPI_KEY")


# to normalize and parse the search results from Superdev API and return a list of dictionaries with title, link, and snippet
def _parse_superdev(data: Dict[str, Any], limit: int) -> List[Dict[str, str]]:
    results: List[Dict[str, str]] = []

    candidates = (
        data.get("results")
        or data.get("items")
        or (data.get("data") or {}).get("results")
        or (data.get("data") or {}).get("items")
        or (data.get("web") or {}).get("results")
        or data.get("organic")
        or []
    )

    for item in candidates:
        if not isinstance(item, dict):
            continue
        title = (
            item.get("title")
            or item.get("name")
            or item.get("headline")
            or "Superdev Result"
        )
        link = item.get("url") or item.get("link") or item.get("href") or ""
        snippet = (
            item.get("snippet")
            or item.get("description")
            or item.get("summary")
            or item.get("content")
            or ""
        )
        if title or link or snippet:
            results.append(
                {
                    "title": str(title),
                    "link": str(link),
                    "snippet": str(snippet),
                }
            )
        if len(results) >= limit:
            break

    return results[:limit]

# this function performs a search using Superdev API and falls back to Wikipedia if Superdev fails or returns no results. It returns a dictionary with the search results and metadata.
async def _search_superdev(
    client: httpx.AsyncClient, query: str, limit: int
) -> List[Dict[str, str]]:
    if not SUPERDEV_API_KEY:
        raise ValueError("Missing SUPERDEV_API_KEY or SUPERDEV_KEY")

    headers = {
        "Authorization": f"Bearer {SUPERDEV_API_KEY}",
        "X-API-Key": SUPERDEV_API_KEY,
    }
    params = {"q": query, "query": query, "num": limit, "limit": limit}

    response = await client.get(SUPERDEV_API_URL, headers=headers, params=params)
    response.raise_for_status()
    data = response.json()
    return _parse_superdev(data, limit)

# function to search Wikipedia using its API and return a list of dictionaries with title, link, and snippet for each result
async def _search_wikipedia(
    client: httpx.AsyncClient, query: str, limit: int
) -> List[Dict[str, str]]:
    response = await client.get(
        "https://en.wikipedia.org/w/api.php",
        params={
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": limit,
            "utf8": 1,
            "format": "json",
        },
    )
    response.raise_for_status()
    data = response.json()

    items = (data.get("query") or {}).get("search") or []

    results: List[Dict[str, str]] = []
    for item in items[:limit]:
        title = item.get("title", "")
        page_slug = title.replace(" ", "_") if title else ""
        snippet = html.unescape(item.get("snippet", ""))
        snippet = snippet.replace('<span class="searchmatch">', "").replace(
            "</span>", ""
        )
        results.append(
            {
                "title": title or "Wikipedia Result",
                "link": f"https://en.wikipedia.org/wiki/{page_slug}" if page_slug else "",
                "snippet": snippet,
            }
        )

    return results


@llm.function_tool(
    description="Search web results using Superdev with Wikipedia fallback."
)
async def google_search(query: str, num_results: int = 5) -> Dict[str, Any]:
    try:
        query = (query or "").strip()
        if not query:
            return {"success": False, "error": "Query cannot be empty."}

        num_results = max(1, min(num_results, 10))

        async with httpx.AsyncClient(
            timeout=12.0,
            headers={"User-Agent": SEARCH_USER_AGENT, "Accept": "application/json"},
        ) as client:
            superdev_results: List[Dict[str, str]] = []
            try:
                superdev_results = await _search_superdev(client, query, num_results)
                if superdev_results:
                    logger.info(
                        f"Superdev search success for query: {query} ({len(superdev_results)} results)"
                    )
                    return {
                        "success": True,
                        "provider": "superdev",
                        "query": query,
                        "count": len(superdev_results),
                        "results": superdev_results,
                    }
                logger.warning("Superdev returned no results, trying Wikipedia fallback")
            except Exception as superdev_error:
                logger.warning(f"Superdev search failed, trying Wikipedia fallback: {superdev_error}")

            try:
                wiki_results = await _search_wikipedia(client, query, num_results)
                logger.info(
                    f"Wikipedia fallback success for query: {query} ({len(wiki_results)} results)"
                )
                return {
                    "success": True,
                    "provider": "wikipedia",
                    "query": query,
                    "count": len(wiki_results),
                    "results": wiki_results,
                }
            except Exception as wiki_error:
                logger.warning(f"Wikipedia fallback failed: {wiki_error}")
                return {
                    "success": False,
                    "provider": "superdev",
                    "query": query,
                    "count": len(superdev_results),
                    "results": superdev_results,
                    "error": "Both Superdev and Wikipedia search failed",
                }

    except httpx.HTTPStatusError as e:
        body = ""
        try:
            body = e.response.text[:300]
        except Exception:
            pass
        logger.error(f"Search HTTP error: {e}")
        return {
            "success": False,
            "error": f"Search API HTTP error: {e.response.status_code}",
            "details": body,
        }
    except Exception as e:
        logger.error(f"Search tool failed: {e}")
        return {"success": False, "error": str(e)}


@llm.function_tool(
    description="Get latest news headlines by topic using NewsAPI."
)
async def get_news(
    query: str = "",
    category: str = "",
    country: str = "us",
    language: str = "en",
    num_results: int = 5,
) -> Dict[str, Any]:
    """Fetch latest headlines from NewsAPI.

    Environment:
    - NEWS_API_KEY (or NEWSAPI_KEY)
    - NEWS_API_URL (optional, defaults to https://newsapi.org/v2)
    """
    try:
        if not NEWS_API_KEY:
            return {
                "success": False,
                "error": "Missing NEWS_API_KEY (or NEWSAPI_KEY) environment variable.",
            }

        num_results = max(1, min(num_results, 20))
        country = (country or "us").strip().lower()
        language = (language or "en").strip().lower()
        query = (query or "").strip()
        category = (category or "").strip().lower()

        async with httpx.AsyncClient(
            timeout=12.0,
            headers={"User-Agent": SEARCH_USER_AGENT, "Accept": "application/json"},
        ) as client:
            headers = {"X-Api-Key": NEWS_API_KEY}

            # Use topic search when query is provided; otherwise fetch top headlines.
            if query:
                endpoint = f"{NEWS_API_URL}/everything"
                params = {
                    "q": query,
                    "language": language,
                    "pageSize": num_results,
                    "sortBy": "publishedAt",
                }
            else:
                endpoint = f"{NEWS_API_URL}/top-headlines"
                params = {
                    "country": country,
                    "pageSize": num_results,
                }
                if category:
                    params["category"] = category

            response = await client.get(endpoint, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

        if data.get("status") != "ok":
            return {
                "success": False,
                "error": data.get("message", "NewsAPI request failed."),
            }

        articles = data.get("articles") or []
        results: List[Dict[str, str]] = []
        for article in articles[:num_results]:
            source_name = ((article.get("source") or {}).get("name") or "")
            results.append(
                {
                    "title": article.get("title", ""),
                    "link": article.get("url", ""),
                    "snippet": article.get("description") or article.get("content") or "",
                    "source": source_name,
                    "published_at": article.get("publishedAt", ""),
                }
            )

        logger.info(f"NewsAPI success (query='{query}', count={len(results)})")
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

    except httpx.HTTPStatusError as e:
        body = ""
        try:
            body = e.response.text[:400]
        except Exception:
            pass
        logger.error(f"NewsAPI HTTP error: {e}")
        return {
            "success": False,
            "error": f"NewsAPI HTTP error: {e.response.status_code}",
            "details": body,
        }
    except Exception as e:
        logger.error(f"NewsAPI tool failed: {e}")
        return {"success": False, "error": str(e)}
    
