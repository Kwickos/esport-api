"""Process worker: init DB + live ingestion loop.

Run: `python -m app.ingestion.worker`.
"""

from __future__ import annotations

import asyncio
import logging

import httpx

from app.db.base import init_db
from app.ingestion.pollers import LiveGameTracker
from app.sources.lol_feed import LolFeedAdapter

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


async def main() -> None:
    await init_db()
    async with httpx.AsyncClient(timeout=20) as client:
        adapter = LolFeedAdapter(client)
        await LiveGameTracker(adapter).run()


if __name__ == "__main__":
    asyncio.run(main())
