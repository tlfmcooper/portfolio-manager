"""
Script to create all tables in the database using SQLAlchemy models.
"""

import asyncio
from app.core.database import engine, Base


async def create_all_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("All tables created successfully.")


if __name__ == "__main__":
    asyncio.run(create_all_tables())
