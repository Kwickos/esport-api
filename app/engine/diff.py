"""Diff engine: frames -> events. THE core of the added value.

The upstream API provides snapshots (frames), not events. We derive events by
comparing a frame to the previous one: a counter that increases = an event.
Ported directly from the Phase 0 spike (validated on a full game).
"""

from __future__ import annotations

from app.schemas.domain import DerivedEvent, NormalizedFrame, TeamState


def _team_events(
    game_id: str, ts, side: str, prev: TeamState, cur: TeamState, score: str
) -> list[DerivedEvent]:
    out: list[DerivedEvent] = []

    dk = cur.kills - prev.kills
    if dk > 0:
        out.append(DerivedEvent(game_id, ts, "KILL", side, f"x{dk} (score {score})"))

    dt_ = cur.towers - prev.towers
    if dt_ > 0:
        out.append(DerivedEvent(game_id, ts, "TOWER", side, f"x{dt_}"))

    db = cur.barons - prev.barons
    if db > 0:
        out.append(DerivedEvent(game_id, ts, "BARON", side, f"x{db}"))

    di = cur.inhibitors - prev.inhibitors
    if di > 0:
        out.append(DerivedEvent(game_id, ts, "INHIBITOR", side, f"x{di}"))

    if len(cur.dragons) > len(prev.dragons):
        for dragon in cur.dragons[len(prev.dragons) :]:
            out.append(DerivedEvent(game_id, ts, "DRAGON", side, dragon))

    return out


def diff_frames(prev: NormalizedFrame, cur: NormalizedFrame) -> list[DerivedEvent]:
    """Events that appeared between `prev` and `cur`."""
    score = f"{cur.blue.kills}-{cur.red.kills}"
    return _team_events(cur.game_id, cur.ts, "blue", prev.blue, cur.blue, score) + _team_events(
        cur.game_id, cur.ts, "red", prev.red, cur.red, score
    )


class EventDeriver:
    """Stateful version: push frames in order, it emits the events."""

    def __init__(self) -> None:
        self._prev: NormalizedFrame | None = None

    def push(self, frame: NormalizedFrame) -> list[DerivedEvent]:
        events = diff_frames(self._prev, frame) if self._prev is not None else []
        self._prev = frame
        return events
