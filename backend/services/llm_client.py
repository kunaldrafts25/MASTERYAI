import json
import hashlib
import asyncio
import time
import logging
from collections import OrderedDict
from backend.config import settings

logger = logging.getLogger(__name__)

RETRY_DELAYS = settings.retry_delays
CALL_TIMEOUT = settings.call_timeout
CACHE_MAX = settings.cache_max


class LRUCache:

    def __init__(self, maxsize: int = CACHE_MAX):
        self._data: OrderedDict[str, str] = OrderedDict()
        self._maxsize = maxsize

    def get(self, key: str) -> str | None:
        if key in self._data:
            self._data.move_to_end(key)
            return self._data[key]
        return None

    def put(self, key: str, value: str):
        if key in self._data:
            self._data.move_to_end(key)
        else:
            if len(self._data) >= self._maxsize:
                self._data.popitem(last=False)
        self._data[key] = value

    def __len__(self):
        return len(self._data)


class LLMClient:

    def __init__(self):
        self.model = settings.llm_model
        self.provider = settings.llm_provider
        self.call_count = 0
        self.total_tokens = 0
        self._cache = LRUCache(CACHE_MAX)
        self._client = None

    def _get_client(self):
        if self._client is None:
            if self.provider == "gemini":
                from google import genai
                self._client = genai.Client(api_key=settings.gemini_api_key)
            else:
                from groq import AsyncGroq
                self._client = AsyncGroq(api_key=settings.groq_api_key)
        return self._client

    async def _redis_get(self, key: str) -> str | None:
        try:
            from backend.services.cache import cache
            if cache._redis:
                return await cache.get(f"llm:{key}")
        except Exception:
            pass
        return None

    async def _redis_set(self, key: str, value: str):
        try:
            from backend.services.cache import cache
            if cache._redis:
                await cache.set(f"llm:{key}", value, ttl=3600)
        except Exception:
            pass

    async def generate(self, prompt: str, system: str = "", response_format: str = "json") -> dict:
        self.call_count += 1
        cache_key = hashlib.md5((system + prompt).encode()).hexdigest()

        redis_val = await self._redis_get(cache_key)
        if redis_val is not None:
            logger.debug("redis cache hit for key=%s", cache_key[:8])
            return json.loads(redis_val)

        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.debug("memory cache hit for key=%s", cache_key[:8])
            return json.loads(cached)

        start = time.monotonic()
        result = await self._real_generate(system, prompt)
        elapsed = time.monotonic() - start
        logger.info("llm call #%d took %.2fs", self.call_count, elapsed)

        result_json = json.dumps(result)
        self._cache.put(cache_key, result_json)
        await self._redis_set(cache_key, result_json)
        return result

    async def _real_generate(self, system: str, prompt: str) -> dict:
        if self.provider == "gemini":
            return await self._generate_gemini(system, prompt)
        return await self._generate_groq(system, prompt)

    async def _generate_gemini(self, system: str, prompt: str) -> dict:
        client = self._get_client()
        from google.genai import types

        full_prompt = f"{system}\n\n{prompt}" if system else prompt

        last_err = None
        for attempt, delay in enumerate(RETRY_DELAYS):
            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        client.models.generate_content,
                        model=self.model,
                        contents=full_prompt,
                        config=types.GenerateContentConfig(
                            temperature=settings.llm_temperature,
                            max_output_tokens=settings.llm_max_tokens,
                            response_mime_type="application/json",
                        ),
                    ),
                    timeout=CALL_TIMEOUT,
                )
                break
            except (asyncio.TimeoutError, Exception) as e:
                last_err = e
                logger.warning(
                    "gemini attempt %d/%d failed: %s — retrying in %ds",
                    attempt + 1, len(RETRY_DELAYS), str(e), delay,
                )
                if attempt < len(RETRY_DELAYS) - 1:
                    await asyncio.sleep(delay)
        else:
            logger.error("all %d gemini attempts failed", len(RETRY_DELAYS))
            raise last_err

        usage = response.usage_metadata
        prompt_tokens = usage.prompt_token_count if usage else 0
        completion_tokens = usage.candidates_token_count if usage else 0
        self.total_tokens += prompt_tokens + completion_tokens
        logger.info(
            "gemini tokens: prompt=%d completion=%d total=%d",
            prompt_tokens, completion_tokens, prompt_tokens + completion_tokens,
        )

        text = response.text
        return self._parse_json(text)

    async def _generate_groq(self, system: str, prompt: str) -> dict:
        client = self._get_client()
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        last_err = None
        for attempt, delay in enumerate(RETRY_DELAYS):
            try:
                completion = await asyncio.wait_for(
                    client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        temperature=settings.llm_temperature,
                        max_tokens=settings.llm_max_tokens,
                        response_format={"type": "json_object"},
                    ),
                    timeout=CALL_TIMEOUT,
                )
                break
            except (asyncio.TimeoutError, Exception) as e:
                last_err = e
                logger.warning(
                    "groq attempt %d/%d failed: %s — retrying in %ds",
                    attempt + 1, len(RETRY_DELAYS), str(e), delay,
                )
                if attempt < len(RETRY_DELAYS) - 1:
                    await asyncio.sleep(delay)
        else:
            logger.error("all %d groq attempts failed", len(RETRY_DELAYS))
            raise last_err

        usage = completion.usage
        prompt_tokens = usage.prompt_tokens if usage else 0
        completion_tokens = usage.completion_tokens if usage else 0
        self.total_tokens += prompt_tokens + completion_tokens
        logger.info(
            "groq tokens: prompt=%d completion=%d total=%d",
            prompt_tokens, completion_tokens, prompt_tokens + completion_tokens,
        )

        text = completion.choices[0].message.content
        return self._parse_json(text)

    @staticmethod
    def _parse_json(text: str) -> dict:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])
            return {"raw": text}

    def get_stats(self) -> dict:
        return {
            "call_count": self.call_count,
            "total_tokens": self.total_tokens,
            "cache_size": len(self._cache),
        }


llm_client = LLMClient()
