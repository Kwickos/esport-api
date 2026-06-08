"""Contract that every data source must implement.

Implementing this Protocol means plugging in a new source without touching the
rest of the system:
- `LolFeedAdapter`  (current)  -> raw lolesports endpoints
- `Cs2VisionAdapter` (later)   -> computer vision on the stream
- `ScrapeAdapter`   (later)    -> scraping a community website
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.schemas.domain import GameMetadata, GameRef, NormalizedFrame


@dataclass(slots=True)
class SliceResult:
    """Result of a feed slice (~10 s for the LoL feed)."""

    frames: list[NormalizedFrame]
    metadata: GameMetadata | None
    empty: bool  # True if nothing at this timestamp (before the 1st frame or after the end)


class SourceAdapter(Protocol):
    name: str

    async def list_live_games(self) -> list[GameRef]:
        """Games currently in progress, covered by this source."""
        ...

    async def fetch_slice(self, game_id: str, starting_time: datetime | None) -> SliceResult:
        """Retrieve the slice of frames starting from `starting_time`."""
        ...
