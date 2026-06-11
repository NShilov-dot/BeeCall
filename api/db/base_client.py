from typing import Any, AsyncIterator

from sqlalchemy import text
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession

from api.constants import DATABASE_URL


class BaseDBClient:
    def __init__(self):
        self.engine = create_async_engine(DATABASE_URL)
        self.async_session = async_sessionmaker(
            bind=self.engine, expire_on_commit=False)
        

    @asynccontextmanager
    async def _session(self) -> AsyncIterator[AsyncSession]:
        async with self.async_session() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            
    
    async def fetch_all(self, query: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Fetch all results for a given SQL query."""
        async with self._session() as session:
            result = await session.execute(text(query), params or {})
            return [dict(row) for row in result.mappings().all()]
        

    async def fetch_one(self, query: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
        """Fetch a single result for a given SQL query."""
        async with self._session() as session:
            result = await session.execute(text(query), params or {})
            row = result.mappings().first()
            return dict(row) if row else None
        
    
    async def execute(self, query: str, params: dict[str, Any] | None = None) -> int:
        """Execute a SQL query and return the number of affected rows."""
        async with self._session() as session:
            result = await session.execute(text(query), params or {})
            await session.commit()
            return result.rowcount
        

    async def close(self) -> None:
        """Close the database engine."""
        await self.engine.dispose()