import logging
from backend.config import settings

logger = logging.getLogger(__name__)


class CacheService:

    def __init__(self):
        self._redis = None

    async def connect(self):
        try:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(
                settings.redis_url,
                decode_responses=True,
            )
            await self._redis.ping()
            logger.info("Redis connected")
        except Exception as e:
            logger.warning("Redis connection failed: %s — running without cache", e)
            self._redis = None

    async def disconnect(self):
        if self._redis:
            await self._redis.close()
            self._redis = None
            logger.info("Redis disconnected")

    async def get(self, key: str) -> str | None:
        if not self._redis:
            return None
        try:
            return await self._redis.get(key)
        except Exception as e:
            logger.warning("cache get failed for key=%s: %s", key, e)
            return None

    async def set(self, key: str, value: str, ttl: int = 3600):
        if not self._redis:
            return
        try:
            await self._redis.set(key, value, ex=ttl)
        except Exception as e:
            logger.warning("cache set failed for key=%s: %s", key, e)



cache = CacheService()
