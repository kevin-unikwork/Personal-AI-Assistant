import httpx
from langchain_core.tools import tool
from app.config import settings
from app.utils.logger import logger

@tool
async def get_morning_intel(location: str = "Surat") -> str:
    """Fetch real-time weather, top news, and market context for the morning briefing.
    
    Args:
        location: The user's city (default is Surat)
    """
    if not settings.tavily_api_key:
        return "Tavily API Key is missing for Intel Tool."

    try:
        # We perform a targeted search for weather and top local news
        query = f"current weather in {location} and top 3 headlines in India today"
        
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": settings.tavily_api_key,
            "query": query,
            "search_depth": "advanced",
            "include_answer": True,
            "max_results": 3
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, json=payload)

        if response.status_code != 200:
            return f"Intel failure: {response.status_code}"

        data = response.json()
        answer = data.get("answer", "")
        results = data.get("results", [])

        intel_summary = []
        if answer:
            intel_summary.append(f"🌤️ *Intel Summary*: {answer}")
        
        for res in results:
            intel_summary.append(f"- {res.get('title')}: {res.get('url')}")

        return "\n".join(intel_summary)

    except Exception as e:
        logger.error(f"Intel tool failed: {e}")
        return f"Could not fetch morning intel: {str(e)}"
