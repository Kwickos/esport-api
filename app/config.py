"""Central configuration (12-factor: everything comes from the environment / .env)."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database: sqlite in dev, postgres in prod
    database_url: str = "sqlite+aiosqlite:///./esport.db"

    # LoL source (raw unofficial lolesports endpoints)
    lol_api_key: str = "0TvQnueqKa5mxJntVWt0w4LpLfEkrV1Ta8rQBb9Z"
    lol_api_base: str = "https://esports-api.lolesports.com/persisted/gw"
    lol_feed_base: str = "https://feed.lolesports.com/livestats/v1"
    hl: str = "en-US"

    # Polling cadences (seconds)
    poll_live_interval: float = 30.0  # detection of live games
    poll_frame_interval: float = 10.0  # native cadence of the window feed


settings = Settings()
