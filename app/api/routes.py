"""REST routes for the API (in-house normalized schema, reading from the database).

Phase 3 (upcoming): WebSocket /live/{game_id} to push live events in real time.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.db.base import SessionLocal

router = APIRouter()


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


@router.get("/leagues")
async def list_leagues(session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(select(models.League))).scalars().all()
    return [
        {"id": r.id, "slug": r.slug, "name": r.name, "region": r.region, "image": r.image}
        for r in rows
    ]


@router.get("/matches")
async def list_matches(
    status: str | None = Query(default=None, description="unstarted | inProgress | completed"),
    limit: int = Query(default=50, le=200),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(models.Match)
    if status:
        stmt = stmt.where(models.Match.status == status)
    rows = (await session.execute(stmt.limit(limit))).scalars().all()
    return [
        {
            "id": r.id,
            "league_id": r.league_id,
            "best_of": r.best_of,
            "status": r.status,
            "scheduled_at": r.scheduled_at,
            "teams": [r.blue_code, r.red_code],
        }
        for r in rows
    ]


@router.get("/matches/{match_id}")
async def get_match(match_id: str, session: AsyncSession = Depends(get_session)):
    match = await session.get(models.Match, match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="match not found")
    games = (
        (await session.execute(select(models.Game).where(models.Game.match_id == match_id)))
        .scalars()
        .all()
    )
    return {
        "id": match.id,
        "status": match.status,
        "teams": [match.blue_code, match.red_code],
        "games": [
            {"id": g.id, "number": g.number, "patch": g.patch, "state": g.state} for g in games
        ],
    }


@router.get("/games/{game_id}/events")
async def game_events(game_id: str, session: AsyncSession = Depends(get_session)):
    rows = (
        (
            await session.execute(
                select(models.Event)
                .where(models.Event.game_id == game_id)
                .order_by(models.Event.ts)
            )
        )
        .scalars()
        .all()
    )
    return [{"ts": e.ts, "type": e.type, "side": e.side, "info": e.info} for e in rows]


@router.get("/games/{game_id}/frames")
async def game_frames(
    game_id: str,
    limit: int = Query(default=500, le=2000),
    session: AsyncSession = Depends(get_session),
):
    rows = (
        (
            await session.execute(
                select(models.Frame)
                .where(models.Frame.game_id == game_id)
                .order_by(models.Frame.ts)
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )
    return [
        {
            "ts": f.ts,
            "state": f.state,
            "blue": {
                "kills": f.blue_kills,
                "towers": f.blue_towers,
                "barons": f.blue_barons,
                "inhibitors": f.blue_inhibitors,
                "gold": f.blue_gold,
                "dragons": f.blue_dragons,
            },
            "red": {
                "kills": f.red_kills,
                "towers": f.red_towers,
                "barons": f.red_barons,
                "inhibitors": f.red_inhibitors,
                "gold": f.red_gold,
                "dragons": f.red_dragons,
            },
        }
        for f in rows
    ]
