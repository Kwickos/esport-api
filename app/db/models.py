"""ORM models. Internal IDs = upstream provider IDs (string) to decouple from the
public schema.

`frames` = raw trace (audit / replayability). `events` = the API's main product.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class League(Base):
    __tablename__ = "leagues"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    slug: Mapped[str | None] = mapped_column(String)
    name: Mapped[str | None] = mapped_column(String)
    region: Mapped[str | None] = mapped_column(String)
    image: Mapped[str | None] = mapped_column(String)


class Team(Base):
    __tablename__ = "teams"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    code: Mapped[str | None] = mapped_column(String)
    name: Mapped[str | None] = mapped_column(String)
    image: Mapped[str | None] = mapped_column(String)


class Player(Base):
    __tablename__ = "players"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    handle: Mapped[str | None] = mapped_column(String)
    team_id: Mapped[str | None] = mapped_column(ForeignKey("teams.id"))
    role: Mapped[str | None] = mapped_column(String)


class Match(Base):
    __tablename__ = "matches"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    league_id: Mapped[str | None] = mapped_column(ForeignKey("leagues.id"))
    best_of: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str | None] = mapped_column(String)  # unstarted | inProgress | completed
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    blue_code: Mapped[str | None] = mapped_column(String)
    red_code: Mapped[str | None] = mapped_column(String)


class Game(Base):
    __tablename__ = "games"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    match_id: Mapped[str] = mapped_column(ForeignKey("matches.id"))
    number: Mapped[int | None] = mapped_column(Integer)
    patch: Mapped[str | None] = mapped_column(String)
    state: Mapped[str | None] = mapped_column(String)  # in_game | finished | paused
    picks: Mapped[dict | None] = mapped_column(JSON)  # normalized draft (blue/red)


class Frame(Base):
    __tablename__ = "frames"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[str] = mapped_column(ForeignKey("games.id"), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    state: Mapped[str | None] = mapped_column(String)
    blue_kills: Mapped[int] = mapped_column(Integer, default=0)
    blue_towers: Mapped[int] = mapped_column(Integer, default=0)
    blue_barons: Mapped[int] = mapped_column(Integer, default=0)
    blue_inhibitors: Mapped[int] = mapped_column(Integer, default=0)
    blue_gold: Mapped[int] = mapped_column(Integer, default=0)
    blue_dragons: Mapped[list | None] = mapped_column(JSON)
    red_kills: Mapped[int] = mapped_column(Integer, default=0)
    red_towers: Mapped[int] = mapped_column(Integer, default=0)
    red_barons: Mapped[int] = mapped_column(Integer, default=0)
    red_inhibitors: Mapped[int] = mapped_column(Integer, default=0)
    red_gold: Mapped[int] = mapped_column(Integer, default=0)
    red_dragons: Mapped[list | None] = mapped_column(JSON)


class Event(Base):
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[str] = mapped_column(ForeignKey("games.id"), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    type: Mapped[str] = mapped_column(String)
    side: Mapped[str] = mapped_column(String)
    info: Mapped[str | None] = mapped_column(String)
