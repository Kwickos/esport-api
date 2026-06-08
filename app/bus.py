"""Live event bus: bridges the ingestion worker to WebSocket clients.

Two implementations:
- `InProcessBus`: asyncio-only, for single-process dev/test (and the optional
  worker-in-API mode). Subscribers get an in-memory queue.
- `RedisBus`: Redis pub/sub, for production where the worker and the API run as
  separate processes and need a broker between them.

`get_bus()` selects one based on `settings.redis_url`.
"""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import Any

from app.config import settings

Message = dict[str, Any]


class _QueueSubscription:
    def __init__(self) -> None:
        self._queue: asyncio.Queue[Message] = asyncio.Queue()

    def push(self, message: Message) -> None:
        self._queue.put_nowait(message)

    async def get(self) -> Message:
        return await self._queue.get()


class InProcessBus:
    name = "in-process"

    def __init__(self) -> None:
        self._subs: dict[str, set[_QueueSubscription]] = defaultdict(set)

    async def publish(self, game_id: str, message: Message) -> None:
        for sub in list(self._subs.get(game_id, ())):
            sub.push(message)

    @asynccontextmanager
    async def subscribe(self, game_id: str):
        sub = _QueueSubscription()
        self._subs[game_id].add(sub)
        try:
            yield sub
        finally:
            self._subs[game_id].discard(sub)
            if not self._subs[game_id]:
                self._subs.pop(game_id, None)


class _RedisSubscription:
    def __init__(self, pubsub) -> None:
        self._pubsub = pubsub

    async def get(self) -> Message:
        while True:
            msg = await self._pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if msg and msg.get("type") == "message":
                return json.loads(msg["data"])


class RedisBus:
    name = "redis"

    def __init__(self, url: str) -> None:
        import redis.asyncio as aioredis

        self._redis = aioredis.from_url(url, decode_responses=True)

    @staticmethod
    def _channel(game_id: str) -> str:
        return f"live:{game_id}"

    async def publish(self, game_id: str, message: Message) -> None:
        await self._redis.publish(self._channel(game_id), json.dumps(message))

    @asynccontextmanager
    async def subscribe(self, game_id: str):
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(self._channel(game_id))
        try:
            yield _RedisSubscription(pubsub)
        finally:
            await pubsub.unsubscribe(self._channel(game_id))
            await pubsub.aclose()


_bus: InProcessBus | RedisBus | None = None


def get_bus() -> InProcessBus | RedisBus:
    """Process-wide singleton bus (Redis in prod, in-process otherwise)."""
    global _bus
    if _bus is None:
        _bus = RedisBus(settings.redis_url) if settings.redis_url else InProcessBus()
    return _bus
