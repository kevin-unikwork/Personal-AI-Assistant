from sqlalchemy import select
from langchain_core.tools import tool
from app.database import async_session
from app.models.user import User
from app.utils.logger import logger

@tool
async def update_user_location(phone_number: str, new_location: str) -> str:
    """Update the user's current city/location for personalized weather and news.
    
    Args:
        phone_number: User's WhatsApp number
        new_location: The new city or location name (e.g. 'Mumbai', 'London')
    """
    try:
        async with async_session() as session:
            result = await session.execute(select(User).where(User.phone_number == phone_number))
            user = result.scalars().first()
            if not user:
                return "User not found."

            user.location = new_location
            await session.commit()
            
            logger.info(f"User {phone_number} updated location to {new_location}")
            return f"🌍 *Location Updated!* \n\nI've set your current base to *{new_location}*. Your next morning briefing will include local weather and news for this area."
    except Exception as e:
        logger.error(f"Failed to update location: {e}")
        return f"Failed to update location: {e}"
