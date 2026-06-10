"""Database access: simple upserts used by the pollers.

Intentionally minimal for the scaffold (Phase 1). Possible optimizations
later: batch inserts, native Postgres ON CONFLICT, cache of already-seen ids.
"""

from __future__ import annotations

from dataclasses import asdict

from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.schemas.domain import (
    DerivedEvent,
    GameMetadata,
    GameRef,
    NormalizedFrame,
    ScheduledMatch,
)


class Repository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert_schedule(self, matches: list[ScheduledMatch]) -> int:
        """Insert/update leagues and matches from the schedule. Returns the count."""
        for sm in matches:
            if await self.session.get(models.League, sm.league_id) is None:
                self.session.add(
                    models.League(
                        id=sm.league_id,
                        slug=sm.league_id,
                        name=sm.league_name,
                        region=sm.league_region,
                        image=sm.league_image,
                    )
                )
            match = await self.session.get(models.Match, sm.match_id)
            if match is None:
                self.session.add(
                    models.Match(
                        id=sm.match_id,
                        league_id=sm.league_id,
                        best_of=sm.best_of,
                        status=sm.status,
                        scheduled_at=sm.scheduled_at,
                        blue_code=sm.blue_code,
                        red_code=sm.red_code,
                    )
                )
            else:
                match.status = sm.status
                match.scheduled_at = sm.scheduled_at
                match.best_of = sm.best_of
        await self.session.commit()
        return len(matches)

    async def ensure_game(self, game: GameRef) -> None:
        """Create the match and the game if they do not exist yet."""
        if await self.session.get(models.Match, game.match_id) is None:
            self.session.add(
                models.Match(
                    id=game.match_id,
                    status="inProgress",
                    scheduled_at=game.start_time,
                    blue_code=game.blue_code,
                    red_code=game.red_code,
                )
            )
        if await self.session.get(models.Game, game.game_id) is None:
            self.session.add(
                models.Game(
                    id=game.game_id,
                    match_id=game.match_id,
                    number=game.number,
                    state="in_game",
                )
            )
        await self.session.commit()

    async def save_metadata(self, game_id: str, md: GameMetadata) -> None:
        row = await self.session.get(models.Game, game_id)
        if row is None:
            return
        row.patch = md.patch
        row.picks = {
            "blue": [asdict(p) for p in md.blue_picks],
            "red": [asdict(p) for p in md.red_picks],
        }
        await self.session.commit()

    async def save_frame(self, f: NormalizedFrame) -> None:
        self.session.add(
            models.Frame(
                game_id=f.game_id,
                ts=f.ts,
                state=f.state,
                blue_kills=f.blue.kills,
                blue_towers=f.blue.towers,
                blue_barons=f.blue.barons,
                blue_inhibitors=f.blue.inhibitors,
                blue_gold=f.blue.gold,
                blue_dragons=f.blue.dragons,
                red_kills=f.red.kills,
                red_towers=f.red.towers,
                red_barons=f.red.barons,
                red_inhibitors=f.red.inhibitors,
                red_gold=f.red.gold,
                red_dragons=f.red.dragons,
            )
        )
        await self.session.commit()

    async def save_events(self, events: list[DerivedEvent]) -> None:
        if not events:
            return
        self.session.add_all(
            models.Event(game_id=e.game_id, ts=e.ts, type=e.type, side=e.side, info=e.info)
            for e in events
        )
        await self.session.commit()

    async def set_game_state(self, game_id: str, state: str) -> None:
        row = await self.session.get(models.Game, game_id)
        if row is not None:
            row.state = state
            await self.session.commit()
