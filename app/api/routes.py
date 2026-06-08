"""REST routes for the public API (in-house normalized schema, reads from the DB).

Responses are typed with Pydantic models (`schemas/api.py`) and list endpoints are
paginated with a `Page` envelope. Phase 3 (planned): WebSocket `/live/{game_id}`
to push events in real time.
"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bus import get_bus
from app.db import models
from app.db.base import SessionLocal
from app.schemas.api import (
    EventOut,
    FrameOut,
    GameOut,
    LeagueOut,
    MatchDetailOut,
    MatchOut,
    Page,
    TeamSideFrame,
)

router = APIRouter()


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


async def _count(session: AsyncSession, model, *where) -> int:
    stmt = select(func.count()).select_from(model)
    for clause in where:
        stmt = stmt.where(clause)
    return (await session.execute(stmt)).scalar_one()


@router.get("/leagues", response_model=list[LeagueOut], tags=["catalog"], summary="List leagues")
async def list_leagues(session: AsyncSession = Depends(get_session)):
    rows = (
        (await session.execute(select(models.League).order_by(models.League.name))).scalars().all()
    )
    return [LeagueOut.model_validate(r) for r in rows]


@router.get("/matches", response_model=Page[MatchOut], tags=["matches"], summary="List matches")
async def list_matches(
    status: str | None = Query(None, description="unstarted | inProgress | completed"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    where = [models.Match.status == status] if status else []
    total = await _count(session, models.Match, *where)
    stmt = select(models.Match)
    for clause in where:
        stmt = stmt.where(clause)
    rows = (
        (
            await session.execute(
                stmt.order_by(models.Match.scheduled_at.desc()).limit(limit).offset(offset)
            )
        )
        .scalars()
        .all()
    )
    items = [
        MatchOut(
            id=r.id,
            league_id=r.league_id,
            best_of=r.best_of,
            status=r.status,
            scheduled_at=r.scheduled_at,
            teams=[r.blue_code, r.red_code],
        )
        for r in rows
    ]
    return Page[MatchOut](items=items, total=total, limit=limit, offset=offset)


@router.get(
    "/matches/{match_id}",
    response_model=MatchDetailOut,
    tags=["matches"],
    summary="Match details (with games)",
)
async def get_match(match_id: str, session: AsyncSession = Depends(get_session)):
    match = await session.get(models.Match, match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="match not found")
    games = (
        (
            await session.execute(
                select(models.Game)
                .where(models.Game.match_id == match_id)
                .order_by(models.Game.number)
            )
        )
        .scalars()
        .all()
    )
    return MatchDetailOut(
        id=match.id,
        league_id=match.league_id,
        best_of=match.best_of,
        status=match.status,
        scheduled_at=match.scheduled_at,
        teams=[match.blue_code, match.red_code],
        games=[GameOut.model_validate(g) for g in games],
    )


@router.get(
    "/games/{game_id}/events",
    response_model=Page[EventOut],
    tags=["games"],
    summary="Derived events for a game",
)
async def game_events(
    game_id: str,
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    total = await _count(session, models.Event, models.Event.game_id == game_id)
    rows = (
        (
            await session.execute(
                select(models.Event)
                .where(models.Event.game_id == game_id)
                .order_by(models.Event.ts)
                .limit(limit)
                .offset(offset)
            )
        )
        .scalars()
        .all()
    )
    items = [EventOut.model_validate(e) for e in rows]
    return Page[EventOut](items=items, total=total, limit=limit, offset=offset)


@router.get(
    "/games/{game_id}/frames",
    response_model=Page[FrameOut],
    tags=["games"],
    summary="Raw frames for a game",
)
async def game_frames(
    game_id: str,
    limit: int = Query(500, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    total = await _count(session, models.Frame, models.Frame.game_id == game_id)
    rows = (
        (
            await session.execute(
                select(models.Frame)
                .where(models.Frame.game_id == game_id)
                .order_by(models.Frame.ts)
                .limit(limit)
                .offset(offset)
            )
        )
        .scalars()
        .all()
    )
    items = [
        FrameOut(
            ts=f.ts,
            state=f.state,
            blue=TeamSideFrame(
                kills=f.blue_kills,
                towers=f.blue_towers,
                barons=f.blue_barons,
                inhibitors=f.blue_inhibitors,
                gold=f.blue_gold,
                dragons=f.blue_dragons or [],
            ),
            red=TeamSideFrame(
                kills=f.red_kills,
                towers=f.red_towers,
                barons=f.red_barons,
                inhibitors=f.red_inhibitors,
                gold=f.red_gold,
                dragons=f.red_dragons or [],
            ),
        )
        for f in rows
    ]
    return Page[FrameOut](items=items, total=total, limit=limit, offset=offset)


@router.websocket("/live/{game_id}")
async def live_feed(websocket: WebSocket, game_id: str):
    """Stream derived events and score snapshots for a game in real time.

    On connect, sends a `{"type": "subscribed"}` ack, then forwards each
    `event` / `score` message published by the ingestion worker for this game.
    """
    await websocket.accept()
    await websocket.send_json({"type": "subscribed", "game_id": game_id})
    bus = get_bus()

    async with bus.subscribe(game_id) as subscription:

        async def _forward() -> None:
            while True:
                await websocket.send_json(await subscription.get())

        async def _watch_disconnect() -> None:
            # No inbound messages expected; this just detects the client closing
            # the socket so we can stop forwarding.
            with contextlib.suppress(WebSocketDisconnect):
                while True:
                    await websocket.receive_text()

        tasks = [asyncio.create_task(_forward()), asyncio.create_task(_watch_disconnect())]
        _, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
