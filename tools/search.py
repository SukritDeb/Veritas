# tools/search.py
# -----------------------------------------------
# THE SEARCH TOOL
# This is NOT an agent — it's just a function.
# Agents CALL this function when they need web data.
# -----------------------------------------------

import os
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()

# Initialize Tavily client once (reused across calls)
tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


def search_news(query: str, num_results: int = 5) -> list[dict]:
    """
    Searches the web for news articles related to a query.

    Args:
        query      : the search query (e.g. "Elon Musk buys NASA")
        num_results: how many articles to return (default 5)

    Returns:
        A list of dicts, each containing:
        {
            "title"  : article headline,
            "url"    : link to article,
            "content": short summary of article
        }
    """

    print(f"  🌐 Searching web for: '{query}'")

    response = tavily.search(
        query=query,
        search_depth="advanced",    # thorough search (vs "basic")
        max_results=num_results,
        include_answer=False,       # we just want raw articles
        topic="news"                # focus on news sources
    )

    # Tavily returns a dict with a "results" key
    # Each result has: title, url, content, score
    results = []
    for article in response["results"]:
        results.append({
            "title"  : article.get("title", "No title"),
            "url"    : article.get("url", ""),
            "content": article.get("content", "No content available")
        })

    print(f"  ✅ Found {len(results)} articles\n")
    return results


def format_results_for_agent(results: list[dict]) -> str:
    """
    Converts the list of article dicts into a clean string
    that we can paste into an LLM prompt.

    Why? LLMs take TEXT as input, not Python dicts.
    """

    if not results:
        return "No articles found."

    formatted = ""
    for i, article in enumerate(results, 1):
        formatted += f"""
ARTICLE {i}:
Title   : {article['title']}
URL     : {article['url']}
Summary : {article['content']}
{'─' * 60}
"""
    return formatted.strip()


# -----------------------------------------------
# QUICK TEST — run this file directly to test
# -----------------------------------------------
if __name__ == "__main__":
    test_results = search_news("teleportation of humans 2025")
    print(format_results_for_agent(test_results))