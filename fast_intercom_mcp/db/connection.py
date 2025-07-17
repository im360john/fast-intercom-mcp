"""Database connection manager using asyncpg."""
import asyncpg
from contextlib import asynccontextmanager
from typing import AsyncIterator
import os

class DatabasePool:
    def __init__(self):
        self.pool = None
        self.database_url = os.getenv("DATABASE_URL")
        if not self.database_url:
            from ..config import Config
            config = Config.load()
            self.database_url = config.database_url
        
    async def initialize(self):
        """Initialize the database connection pool."""
        self.pool = await asyncpg.create_pool(
            self.database_url,
            min_size=10,
            max_size=20,
            max_queries=50000,
            max_inactive_connection_lifetime=300
        )
    
    async def close(self):
        """Close the database connection pool."""
        if self.pool:
            await self.pool.close()
    
    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[asyncpg.Connection]:
        """Acquire a database connection from the pool."""
        async with self.pool.acquire() as connection:
            yield connection

# Global instance
db_pool = DatabasePool()