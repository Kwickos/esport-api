"""API endpoint tests: Pydantic response shapes + pagination envelope."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.db import models
from app.db.base import SessionLocal, engine, init_db
from app.main import app


@pytest.fixture
async def client():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    await engine.dispose()  # fresh connections per test (avoids cross-loop reuse)


async def test_health(client):
    assert (await client.get("/health")).json() == {"status": "ok"}


async def test_matches_returns_pagination_envelope(client):
    body = (await client.get("/matches")).json()
    assert body == {"items": [], "total": 0, "limit": 50, "offset": 0}


async def test_match_not_found(client):
    assert (await client.get("/matches/does-not-exist")).status_code == 404


async def test_events_pagination_params(client):
    body = (await client.get("/games/g1/events?limit=10&offset=5")).json()
    assert body == {"items": [], "total": 0, "limit": 10, "offset": 5}


async def test_league_roundtrip(client):
    async with SessionLocal() as session:
        session.add(models.League(id="L1", slug="lck", name="LCK", region="KR"))
        await session.commit()
    data = (await client.get("/leagues")).json()
    assert {"id": "L1", "slug": "lck", "name": "LCK", "region": "KR", "image": None} in data
