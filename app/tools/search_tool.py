import httpx
from langchain_core.tools import tool
from app.utils.logger import logger


@tool
def web_search(query: str) -> str:
    """Search the web for current information, facts, or news using Tavily Search."""
    from app.config import settings
    
    if not settings.tavily_api_key:
        return "Tavily API Key is missing. Please add TAVILY_API_KEY to your .env file."

    try:
        # Use Tavily API via httpx
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": settings.tavily_api_key,
            "query": query,
            "search_depth": "basic",
            "max_results": 5
        }

        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, json=payload)

        if response.status_code != 200:
            return f"Search failed via Tavily. Status: {response.status_code}"

        data = response.json()
        results = data.get("results", [])

        if not results:
            return f"No search results found for '{query}'."

        formatted_results = []
        for i, res in enumerate(results):
            title = res.get("title", "No Title")
            content = res.get("content", "No snippet available.")
            url = res.get("url", "")
            formatted_results.append(f"{i+1}. {title}: {content}\n   🔗 {url}")

        return f"Search results for '{query}':\n" + "\n".join(formatted_results)

    except Exception as e:
        logger.error(f"Tavily search failed: {e}")
        return f"Search encountered an issue: {str(e)}"
