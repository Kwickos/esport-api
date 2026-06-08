"""Shared time helpers (the feed requires timestamps aligned to 10 s)."""

from __future__ import annotations

from datetime import UTC, datetime

_FORMATS = ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z")


def parse_ts(ts: str) -> datetime:
    """Parse an rfc460Timestamp ('...Z', with or without milliseconds)."""
    raw = ts.replace("Z", "+0000")
    for fmt in _FORMATS:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    raise ValueError(f"unreadable timestamp: {ts!r}")


def round10(dt: datetime) -> datetime:
    """Round down to the lower 10 s slice (required by the feed window)."""
    return dt.replace(second=(dt.second // 10) * 10, microsecond=0)


def iso_z(dt: datetime) -> str:
    """Format expected by startingTime: 'YYYY-MM-DDTHH:MM:SS.000Z'."""
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def utcnow() -> datetime:
    return datetime.now(UTC)
