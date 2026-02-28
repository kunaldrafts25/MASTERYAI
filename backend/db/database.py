import logging
import asyncpg
from backend.config import settings

logger = logging.getLogger(__name__)


class Database:

    def __init__(self):
        self._pool: asyncpg.Pool | None = None

    @property
    def pool(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError("database not connected — call await db.connect() first")
        return self._pool

    async def connect(self):
        logger.info("connecting to PostgreSQL")
        self._pool = await asyncpg.create_pool(
            dsn=settings.database_url,
            min_size=2,
            max_size=10,
            command_timeout=30,
        )
        logger.info("PostgreSQL pool created")

    async def disconnect(self):
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("PostgreSQL pool closed")


db = Database()
