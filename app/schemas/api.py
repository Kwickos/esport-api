"""Pydantic response models for the public REST API.

Kept separate from the internal domain types (`schemas/domain.py`): these define
the *wire* shape returned to clients, decoupled from both the ORM and the sources.
"""

from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """Generic pagination envelope."""

    items: list[T]
    total: int
    limit: int
    offset: int


class _ORM(BaseModel):
    """Base for models populated directly from ORM rows."""

    model_config = ConfigDict(from_attributes=True)


class LeagueOut(_ORM):
    id: str
    slug: str | None = None
    name: str | None = None
    region: str | None = None
    image: str | None = None


class GameOut(_ORM):
    id: str
    number: int | None = None
    patch: str | None = None
    state: str | None = None


class MatchOut(BaseModel):
    id: str
    league_id: str | None = None
    best_of: int | None = None
    status: str | None = None
    scheduled_at: datetime | None = None
    teams: list[str | None]


class MatchDetailOut(MatchOut):
    games: list[GameOut] = []


class EventOut(_ORM):
    ts: datetime
    type: str
    side: str
    info: str | None = None


class TeamSideFrame(BaseModel):
    kills: int
    towers: int
    barons: int
    inhibitors: int
    gold: int
    dragons: list[str]


class FrameOut(BaseModel):
    ts: datetime
    state: str | None = None
    blue: TeamSideFrame
    red: TeamSideFrame
