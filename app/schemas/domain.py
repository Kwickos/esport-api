"""Normalized domain types — the common language shared by ALL sources.

The core (diff engine, pollers, API) only knows about these types. A new source
(computer vision, scraping) only has to produce `NormalizedFrame` objects:
nothing else changes. This is what makes the architecture source-agnostic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

# Event types derived by the diff engine
EVENT_TYPES = ("KILL", "TOWER", "DRAGON", "BARON", "INHIBITOR")


@dataclass(slots=True)
class TeamState:
    """State of a team at a given instant (snapshot)."""

    kills: int = 0
    towers: int = 0
    barons: int = 0
    inhibitors: int = 0
    gold: int = 0
    dragons: list[str] = field(default_factory=list)  # list of types: infernal, elder...


@dataclass(slots=True)
class NormalizedFrame:
    """A normalized snapshot of the game, whatever its source."""

    game_id: str
    ts: datetime
    state: str  # in_game | finished | paused
    blue: TeamState
    red: TeamState


@dataclass(slots=True)
class PlayerPick:
    participant_id: int
    player_id: str
    summoner_name: str
    champion: str
    role: str


@dataclass(slots=True)
class GameMetadata:
    patch: str
    blue_team_id: str
    red_team_id: str
    blue_picks: list[PlayerPick]
    red_picks: list[PlayerPick]


@dataclass(slots=True)
class GameRef:
    """Lightweight pointer to a game (live or to be replayed)."""

    game_id: str
    match_id: str
    number: int
    league: str
    blue_code: str
    red_code: str
    start_time: datetime | None


@dataclass(slots=True)
class DerivedEvent:
    """An event derived by diffing two frames — the core of the value."""

    game_id: str
    ts: datetime
    type: str  # one of EVENT_TYPES
    side: str  # blue | red
    info: str  # e.g. "x2 (score 7-7)" or the dragon type
