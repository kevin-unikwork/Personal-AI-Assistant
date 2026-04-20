import httpx
import re
from langchain_core.tools import tool
from app.utils.logger import logger

@tool
def find_local_services(category: str, location: str) -> str:
    """Find the best local services, shops, malls, or businesses (menswear, restaurants, hospitals, dentists) in a specific location using Tavily Search.
    
    Args:
        category: The type of service or shop (e.g., 'Menswear shop', 'Hospital', 'Italian Restaurant')
        location: The city or area
    """
    from app.config import settings
    
    if not settings.tavily_api_key:
        return "Tavily API Key is missing. Please add TAVILY_API_KEY to your .env file."

    try:
        query = f"top rated {category} in {location} with ratings and contact details"
        
        # Use Tavily API via httpx
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": settings.tavily_api_key,
            "query": query,
            "search_depth": "advanced",
            "include_answer": True,
            "max_results": 5
        }

        with httpx.Client(timeout=15.0) as client:
            response = client.post(url, json=payload)

        if response.status_code != 200:
            return f"Failed to search for services via Tavily. Status: {response.status_code}"

        data = response.json()
        results = data.get("results", [])

        if not results:
            return f"Tavily couldn't find any specific list of {category} in {location}."

        formatted_results = []
        for i, res in enumerate(results):
            title = res.get("title", "Unknown Place")
            content = res.get("content", "No description available.")
            url = res.get("url", "")
            formatted_results.append(f"🏠 {title}\n   ℹ️ {content}\n   🔗 {url}\n")

        return f"📍 *Verified Options for {category} in {location}:*\n\n" + "\n".join(formatted_results) + "\nPlease let me know if you would like me to book an appointment or get more details for any of these."

    except Exception as e:
        logger.error(f"Tavily Service discovery failed: {e}")
        return f"Service discovery encountered an issue: {str(e)}"
