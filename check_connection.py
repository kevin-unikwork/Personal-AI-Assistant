import asyncio
from sqlalchemy import text
from app.database import engine
from app.config import settings

async def test_connection():
    print(f"🔗 Attempting to connect to: {settings.database_url.split('@')[-1]}")
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version();"))
            version = result.scalar()
            print(f"✅ CONNECTION SUCCESSFUL!")
            print(f"📊 Database Version: {version}")
            
            # Check if tables exist
            result = await conn.execute(text("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = 'public';"))
            tables = [row[0] for row in result]
            print(f"📂 Tables Found: {', '.join(tables) if tables else 'None'}")
            
    except Exception as e:
        print(f"❌ CONNECTION FAILED!")
        print(f"Error: {e}")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_connection())
