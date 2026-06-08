"""FastAPI app (process API). Run with: `uvicorn app.main:app --reload`."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.db.base import init_db

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
    yield


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
