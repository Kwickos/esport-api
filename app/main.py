"""FastAPI app (process API). Run with: `uvicorn app.main:app --reload`."""

from __future__ import annotations

import asyncio
import contextlib
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.bus import get_bus
from app.config import settings
from app.db.base import init_db
from app.ingestion.pollers import LiveGameTracker, SchedulePoller
from app.sources.lol_feed import LolFeedAdapter

TAGS_METADATA = [
    {"name": "catalog", "description": "Leagues, teams and players."},
    {"name": "matches", "description": "Matches and their games."},
    {"name": "games", "description": "Per-game live data: derived events and raw frames."},
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Dev convenience: create tables on startup (SQLite). In production, use the
    # Alembic migrations (see `alembic/`) as the source of truth instead.
    await init_db()

    worker_task: asyncio.Task | None = None
    client: httpx.AsyncClient | None = None
    if settings.run_worker_in_api:
        # Single-process mode: run ingestion in-process so the in-process bus
        # bridges worker -> WebSocket without Redis.
        client = httpx.AsyncClient(timeout=20)
        adapter = LolFeedAdapter(client)

        async def _run_ingestion() -> None:
            await asyncio.gather(
                SchedulePoller(adapter).run(),
                LiveGameTracker(adapter, get_bus()).run(),
            )

        worker_task = asyncio.create_task(_run_ingestion())

    try:
        yield
    finally:
        if worker_task is not None:
            worker_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await worker_task
        if client is not None:
            await client.aclose()


app = FastAPI(
    title="esport-api",
    version="0.1.0",
    description=(
        "Self-hosted, independent live esports data API. Multi-game by design, "
        "League of Legends first."
    ),
    license_info={"name": "MIT", "url": "https://github.com/Kwickos/esport-api/blob/main/LICENSE"},
    contact={"name": "esport-api", "url": "https://github.com/Kwickos/esport-api"},
    openapi_tags=TAGS_METADATA,
    lifespan=lifespan,
)
app.include_router(router)


@app.get("/health", tags=["catalog"], summary="Health check")
async def health():
    return {"status": "ok"}


# Test dashboard (static, no build step) — served at /dashboard if web/ exists.
_WEB_DIR = Path(__file__).resolve().parent.parent / "web"
if _WEB_DIR.is_dir():
    app.mount("/dashboard", StaticFiles(directory=_WEB_DIR, html=True), name="dashboard")

    @app.get("/", include_in_schema=False)
    async def root() -> RedirectResponse:
        return RedirectResponse(url="/dashboard/")
