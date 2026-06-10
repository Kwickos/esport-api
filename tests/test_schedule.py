"""Schedule ingestion tests (leagues + matches upsert)."""

from datetime import UTC, datetime

import pytest

from app.db import models
from app.db.base import Base, SessionLocal, engine
from app.db.repository import Repository
from app.schemas.domain import ScheduledMatch


@pytest.fixture
async def session():
    # Fresh schema per test so schedule rows don't leak into other tests.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with SessionLocal() as s:
        yield s
    await engine.dispose()


def _match(match_id, status="unstarted"):
    return ScheduledMatch(
        match_id=match_id,
        league_id="lck",
        league_name="LCK",
        league_region="KR",
        league_image=None,
        best_of=5,
        status=status,
        scheduled_at=datetime(2026, 6, 8, 15, tzinfo=UTC),
        blue_code="T1",
        red_code="GEN",
    )


async def test_upsert_inserts_league_and_match(session):
    n = await Repository(session).upsert_schedule([_match("M_A")])
    assert n == 1
    league = await session.get(models.League, "lck")
    assert league.name == "LCK" and league.region == "KR"
    match = await session.get(models.Match, "M_A")
    assert match.status == "unstarted" and match.best_of == 5
    assert [match.blue_code, match.red_code] == ["T1", "GEN"]


async def test_upsert_updates_status_idempotently(session):
    repo = Repository(session)
    await repo.upsert_schedule([_match("M_B", status="unstarted")])
    await repo.upsert_schedule([_match("M_B", status="inProgress")])
    match = await session.get(models.Match, "M_B")
    assert match.status == "inProgress"
