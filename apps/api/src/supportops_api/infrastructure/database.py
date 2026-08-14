from __future__ import annotations

import os
from collections.abc import AsyncIterator

from dotenv import find_dotenv, load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

load_dotenv(find_dotenv(usecwd=True))


def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    user = os.getenv("DB_USER", "supportops")
    password = os.getenv("DB_PASSWORD", "supportops_dev")
    name = os.getenv("DB_NAME", "supportops")
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{name}"


engine = create_async_engine(get_database_url(), pool_pre_ping=True)
AsyncSessionFactory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionFactory() as session:
        yield session
