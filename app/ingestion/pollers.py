"""Asyncio pollers: live game detection + slice-by-slice tracking.

- LiveGameTracker: every N seconds, asks the adapter for live games, and
  starts/stops a GamePoller coroutine per game.
- GamePoller: tracks a game, slice of 10 s by slice of 10 s, derives the
  events (diff engine) and persists them. Run logic aligned on the spike:
  204 before the start = we keep looking; 204 after = probable end.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from app.config import settings
from app.db.base import SessionLocal
from app.db.repository import Repository
from app.engine.diff import EventDeriver
from app.schemas.domain import DerivedEvent, GameRef, NormalizedFrame
from app.sources.base import SourceAdapter
from app.timeutil import round10, utcnow

log = logging.getLogger("ingestion")

# Empty slices in a row (after start) before declaring the game finished
MAX_IDLE_SLICES = 6


def _event_message(ev: DerivedEvent) -> dict:
    return {
        "type": "event",
        "game_id": ev.game_id,
        "ts": ev.ts.isoformat(),
        "event_type": ev.type,
        "side": ev.side,
        "info": ev.info,
    }


def _score_message(frame: NormalizedFrame) -> dict:
    return {
        "type": "score",
        "game_id": frame.game_id,
        "ts": frame.ts.isoformat(),
        "state": frame.state,
        "blue": {"kills": frame.blue.kills, "towers": frame.blue.towers, "gold": frame.blue.gold},
        "red": {"kills": frame.red.kills, "towers": frame.red.towers, "gold": frame.red.gold},
    }


class GamePoller:
    def __init__(self, adapter: SourceAdapter, game: GameRef, bus):
        self.adapter = adapter
        self.game = game
        self.bus = bus

    async def _publish(self, events: list[DerivedEvent], frame: NormalizedFrame) -> None:
        """Push to the live bus. Must never break ingestion: swallow + log failures."""
        try:
            for ev in events:
                await self.bus.publish(self.game.game_id, _event_message(ev))
            await self.bus.publish(self.game.game_id, _score_message(frame))
        except Exception:  # noqa: BLE001 - a bus blip must not stop persistence
            log.warning(
                "bus.publish failed for game %s; ingestion continues",
                self.game.game_id,
                exc_info=True,
            )

    async def run(self) -> None:
        deriver = EventDeriver()
        cursor = self.game.start_time  # None -> the adapter will use its default
        started, idle = False, 0
        async with SessionLocal() as session:
            repo = Repository(session)
            await repo.ensure_game(self.game)

            while True:
                sl = await self.adapter.fetch_slice(self.game.game_id, cursor)

                if sl.empty:
                    if not started:
                        # still in pre-game: we move forward to find the first frame
                        cursor = (cursor or utcnow()) + timedelta(seconds=60)
                        if cursor > utcnow() + timedelta(seconds=5):
                            await asyncio.sleep(settings.poll_frame_interval)
                        continue
                    idle += 1
                    if idle >= MAX_IDLE_SLICES:
                        break  # game finished
                    await asyncio.sleep(settings.poll_frame_interval)
                    continue

                idle, started = 0, True
                if sl.metadata:
                    await repo.save_metadata(self.game.game_id, sl.metadata)

                for frame in sl.frames:
                    events = deriver.push(frame)
                    await repo.save_events(events)
                    await repo.save_frame(frame)
                    await self._publish(events, frame)

                last = sl.frames[-1]
                if last.state == "finished":
                    break
                cursor = round10(last.ts) + timedelta(seconds=10)
                # catch up with the live stream: once we reach the present, wait
                # for what comes next
                if cursor > utcnow():
                    await asyncio.sleep(settings.poll_frame_interval)

            await repo.set_game_state(self.game.game_id, "finished")
            log.info("game %s finished", self.game.game_id)


class LiveGameTracker:
    def __init__(self, adapter: SourceAdapter, bus):
        self.adapter = adapter
        self.bus = bus
        self._tasks: dict[str, asyncio.Task] = {}

    async def run(self) -> None:
        log.info("tracker started (source=%s)", self.adapter.name)
        while True:
            try:
                live = await self.adapter.list_live_games()
            except Exception:  # noqa: BLE001
                log.exception("list_live_games failed")
                live = []

            for game in live:
                if game.game_id not in self._tasks:
                    log.info(
                        "new live game: %s (%s vs %s)",
                        game.game_id,
                        game.blue_code,
                        game.red_code,
                    )
                    self._tasks[game.game_id] = asyncio.create_task(
                        GamePoller(self.adapter, game, self.bus).run()
                    )

            for gid, task in list(self._tasks.items()):
                if task.done():
                    self._tasks.pop(gid)
                    if not task.cancelled() and task.exception() is not None:
                        log.error("game poller %s crashed: %r", gid, task.exception())

            await asyncio.sleep(settings.poll_live_interval)
