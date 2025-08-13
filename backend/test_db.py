import asyncio
from sqlalchemy import text
from app.core.config import settings
from sqlalchemy.ext.asyncio import create_async_engine

async def test_connection():
    engine = create_async_engine(settings.DATABASE_URL)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            print("Connection successful:", result.scalar())
    except Exception as e:
        print("Connection failed:", str(e))

asyncio.run(test_connection())