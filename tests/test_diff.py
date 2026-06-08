"""Tests for the diff engine (pure logic, no external dependencies)."""

from datetime import UTC, datetime

from app.engine.diff import EventDeriver
from app.schemas.domain import NormalizedFrame, TeamState

_T = datetime(2026, 1, 1, tzinfo=UTC)


def _frame(blue: TeamState, red: TeamState) -> NormalizedFrame:
    return NormalizedFrame("g", _T, "in_game", blue, red)


def test_first_frame_emits_nothing():
    d = EventDeriver()
    assert d.push(_frame(TeamState(), TeamState())) == []


def test_derives_kills_towers_dragons():
    d = EventDeriver()
    d.push(_frame(TeamState(kills=3, towers=1, dragons=["infernal"]), TeamState()))
    events = d.push(
        _frame(
            TeamState(kills=5, towers=2, dragons=["infernal", "elder"]),
            TeamState(kills=1),
        )
    )
    kinds = sorted((e.type, e.side) for e in events)
    assert kinds == [
        ("DRAGON", "blue"),
        ("KILL", "blue"),
        ("KILL", "red"),
        ("TOWER", "blue"),
    ]
    blue_kill = next(e for e in events if e.type == "KILL" and e.side == "blue")
    assert "x2" in blue_kill.info and "5-1" in blue_kill.info
    dragon = next(e for e in events if e.type == "DRAGON")
    assert dragon.info == "elder"  # only the NEW dragon is emitted


def test_no_phantom_events_when_state_stable():
    d = EventDeriver()
    d.push(_frame(TeamState(kills=2), TeamState(kills=2)))
    assert d.push(_frame(TeamState(kills=2), TeamState(kills=2))) == []
