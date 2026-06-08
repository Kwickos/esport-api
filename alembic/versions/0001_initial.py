"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-08
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "leagues",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("slug", sa.String(), nullable=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("region", sa.String(), nullable=True),
        sa.Column("image", sa.String(), nullable=True),
    )
    op.create_table(
        "teams",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("code", sa.String(), nullable=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("image", sa.String(), nullable=True),
    )
    op.create_table(
        "players",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("handle", sa.String(), nullable=True),
        sa.Column("team_id", sa.String(), sa.ForeignKey("teams.id"), nullable=True),
        sa.Column("role", sa.String(), nullable=True),
    )
    op.create_table(
        "matches",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("league_id", sa.String(), sa.ForeignKey("leagues.id"), nullable=True),
        sa.Column("best_of", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("blue_code", sa.String(), nullable=True),
        sa.Column("red_code", sa.String(), nullable=True),
    )
    op.create_table(
        "games",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("match_id", sa.String(), sa.ForeignKey("matches.id"), nullable=False),
        sa.Column("number", sa.Integer(), nullable=True),
        sa.Column("patch", sa.String(), nullable=True),
        sa.Column("state", sa.String(), nullable=True),
        sa.Column("picks", sa.JSON(), nullable=True),
    )
    op.create_table(
        "frames",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("game_id", sa.String(), sa.ForeignKey("games.id"), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("state", sa.String(), nullable=True),
        sa.Column("blue_kills", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("blue_towers", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("blue_barons", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("blue_inhibitors", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("blue_gold", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("blue_dragons", sa.JSON(), nullable=True),
        sa.Column("red_kills", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("red_towers", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("red_barons", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("red_inhibitors", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("red_gold", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("red_dragons", sa.JSON(), nullable=True),
    )
    op.create_index(op.f("ix_frames_game_id"), "frames", ["game_id"])
    op.create_index(op.f("ix_frames_ts"), "frames", ["ts"])
    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("game_id", sa.String(), sa.ForeignKey("games.id"), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("side", sa.String(), nullable=False),
        sa.Column("info", sa.String(), nullable=True),
    )
    op.create_index(op.f("ix_events_game_id"), "events", ["game_id"])
    op.create_index(op.f("ix_events_ts"), "events", ["ts"])


def downgrade() -> None:
    op.drop_index(op.f("ix_events_ts"), table_name="events")
    op.drop_index(op.f("ix_events_game_id"), table_name="events")
    op.drop_table("events")
    op.drop_index(op.f("ix_frames_ts"), table_name="frames")
    op.drop_index(op.f("ix_frames_game_id"), table_name="frames")
    op.drop_table("frames")
    op.drop_table("games")
    op.drop_table("matches")
    op.drop_table("players")
    op.drop_table("teams")
    op.drop_table("leagues")
