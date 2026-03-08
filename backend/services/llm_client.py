import json
import hashlib
import asyncio
import time
import logging
import threading
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


class StreamingTextExtractor:
    """Extracts user-facing text from streaming JSON responses.

    Watches for known text fields (teaching_content, explanation, etc.)
    and yields their string values as they stream in, allowing real-time
    display to users while the full JSON is still being generated.
    """

    DEFAULT_FIELDS = frozenset({
        "teaching_content", "explanation", "problem_statement",
        "question", "message", "opening_question",
        "misconception_explanation", "correct_explanation",
    })

    def __init__(self, fields=None):
        self._fields = fields or self.DEFAULT_FIELDS
        self._buffer = ""
        self._in_value = False
        self._escape_next = False

    def feed(self, chunk: str) -> str:
        """Feed a chunk of JSON text, return any extracted user-facing text."""
        extracted = []
        for ch in chunk:
            self._buffer += ch

            if self._in_value:
                if self._escape_next:
                    _MAP = {"n": "\n", "t": "\t", '"': '"', "\\": "\\", "/": "/"}
                    extracted.append(_MAP.get(ch, ch))
                    self._escape_next = False
                elif ch == "\\":
                    self._escape_next = True
                elif ch == '"':
                    self._in_value = False
                else:
                    extracted.append(ch)
            elif ch == '"':
                before = self._buffer[:-1].rstrip()
                if before.endswith(":"):
                    key_part = before[:-1].rstrip()
                    for field in self._fields:
                        if key_part.endswith(f'"{field}"'):
                            self._in_value = True
                            break

            # Keep buffer bounded
            if len(self._buffer) > 200:
                self._buffer = self._buffer[-100:]

        return "".join(extracted)


class LLMClient:

    def __init__(self):
        self.call_count = 0
        self.total_tokens = 0
        self._cache = LRUCache(CACHE_MAX)
        self._client = None

    def _get_client(self):
        if self._client is None:
            import boto3
            self._client = boto3.client(
                "bedrock-runtime",
                region_name=settings.aws_region,
            )
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
        return await self._generate_bedrock(system, prompt)

    async def _generate_bedrock(self, system: str, prompt: str) -> dict:
        client = self._get_client()
        model_id = settings.aws_bedrock_model_id

        messages = [{"role": "user", "content": [{"text": prompt}]}]
        system_prompt = "Respond ONLY with valid JSON. No markdown fences, no preamble."
        if system:
            system_prompt = f"{system}\n\n{system_prompt}"
        system_list = [{"text": system_prompt}]

        last_err = None
        for attempt, delay in enumerate(RETRY_DELAYS):
            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        client.converse,
                        modelId=model_id,
                        messages=messages,
                        system=system_list,
                        inferenceConfig={
                            "temperature": settings.llm_temperature,
                            "maxTokens": settings.llm_max_tokens,
                        },
                    ),
                    timeout=CALL_TIMEOUT,
                )
                break
            except (asyncio.TimeoutError, Exception) as e:
                last_err = e
                logger.warning(
                    "bedrock attempt %d/%d failed: %s — retrying in %ds",
                    attempt + 1, len(RETRY_DELAYS), str(e), delay,
                )
                if attempt < len(RETRY_DELAYS) - 1:
                    await asyncio.sleep(delay)
        else:
            logger.error("all %d bedrock attempts failed", len(RETRY_DELAYS))
            raise last_err

        usage = response.get("usage", {})
        prompt_tokens = usage.get("inputTokens", 0)
        completion_tokens = usage.get("outputTokens", 0)
        self.total_tokens += prompt_tokens + completion_tokens
        logger.info(
            "bedrock tokens: prompt=%d completion=%d total=%d",
            prompt_tokens, completion_tokens, prompt_tokens + completion_tokens,
        )

        text = response["output"]["message"]["content"][0]["text"]
        return self._parse_json(text)

    # ------------------------------------------------------------------
    # Streaming methods — real token-by-token delivery
    # ------------------------------------------------------------------

    async def generate_stream(self, prompt: str, system: str = "", on_chunk=None) -> dict:
        """Streaming LLM call. Calls on_chunk(text_delta) for each token.

        No caching — streaming is for user-facing content where
        real-time delivery matters more than cache hits.
        Falls back to non-streaming on error.
        """
        self.call_count += 1
        start = time.monotonic()

        try:
            result = await self._stream_bedrock(system, prompt, on_chunk)

            elapsed = time.monotonic() - start
            logger.info("streaming llm call #%d took %.2fs", self.call_count, elapsed)
            return result
        except Exception as e:
            logger.warning("streaming failed (%s), falling back to non-streaming", str(e))
            return await self._real_generate(system, prompt)

    async def _bridge_sync_stream(self, sync_fn, on_chunk) -> str:
        """Bridge a synchronous streaming function to async.

        sync_fn(loop, queue) should put ("chunk", text), ("done", None),
        or ("error", exception) into the queue.
        Returns the full concatenated text.
        """
        queue = asyncio.Queue()
        loop = asyncio.get_running_loop()

        thread = threading.Thread(target=sync_fn, args=(loop, queue), daemon=True)
        thread.start()

        full_text = ""
        while True:
            msg_type, data = await queue.get()
            if msg_type == "done":
                break
            if msg_type == "error":
                raise data
            full_text += data
            if on_chunk:
                await on_chunk(data)

        thread.join(timeout=5)
        return full_text

    async def _stream_bedrock(self, system: str, prompt: str, on_chunk) -> dict:
        client = self._get_client()
        model_id = settings.aws_bedrock_model_id

        messages = [{"role": "user", "content": [{"text": prompt}]}]
        system_prompt = "Respond ONLY with valid JSON. No markdown fences, no preamble."
        if system:
            system_prompt = f"{system}\n\n{system_prompt}"

        meta = {}

        def sync_fn(loop, q):
            try:
                resp = client.converse_stream(
                    modelId=model_id,
                    messages=messages,
                    system=[{"text": system_prompt}],
                    inferenceConfig={
                        "temperature": settings.llm_temperature,
                        "maxTokens": settings.llm_max_tokens,
                    },
                )
                for event in resp["stream"]:
                    if "contentBlockDelta" in event:
                        text = event["contentBlockDelta"]["delta"].get("text", "")
                        if text:
                            loop.call_soon_threadsafe(q.put_nowait, ("chunk", text))
                    elif "metadata" in event:
                        usage = event["metadata"].get("usage", {})
                        meta["input"] = usage.get("inputTokens", 0)
                        meta["output"] = usage.get("outputTokens", 0)
                loop.call_soon_threadsafe(q.put_nowait, ("done", None))
            except Exception as e:
                loop.call_soon_threadsafe(q.put_nowait, ("error", e))

        full_text = await self._bridge_sync_stream(sync_fn, on_chunk)

        inp, out = meta.get("input", 0), meta.get("output", 0)
        self.total_tokens += inp + out
        logger.info("bedrock stream tokens: prompt=%d completion=%d", inp, out)
        return self._parse_json(full_text)

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
