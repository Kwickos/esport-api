"""LoL adapter - raw unofficial lolesports endpoints (validated during the Phase 0 spike).

Endpoints:
- esports-api.lolesports.com/persisted/gw/{getLive,getEventDetails}  (header x-api-key)
- feed.lolesports.com/livestats/v1/window/{gameId}?startingTime=...  (~10 s slices)

Behaviors learned during the spike:
- window WITHOUT startingTime = "live now" frames (zeros if nothing is in progress)
  -> not useful.
- window WITH startingTime (a multiple of 10 s) = ONE ~10 s slice.
- HTTP 204 = before the first frame (pre-game) or after the last one (finished).
- The LPL has no feed -> list_live_games simply will not surface it.
"""

from __future__ import annotations

from datetime import datetime

import httpx

from app.config import settings
from app.schemas.domain import (
    GameMetadata,
    GameRef,
    NormalizedFrame,
    PlayerPick,
    TeamState,
)
from app.sources.base import SliceResult
from app.timeutil import iso_z, parse_ts, round10


def _team(raw: dict) -> TeamState:
    return TeamState(
        kills=raw.get("totalKills", 0),
        towers=raw.get("towers", 0),
        barons=raw.get("barons", 0),
        inhibitors=raw.get("inhibitors", 0),
        gold=raw.get("totalGold", 0),
        dragons=list(raw.get("dragons") or []),
    )


def _frame(game_id: str, raw: dict) -> NormalizedFrame:
    return NormalizedFrame(
        game_id=game_id,
        ts=parse_ts(raw["rfc460Timestamp"]),
        state=raw.get("gameState", "in_game"),
        blue=_team(raw.get("blueTeam", {})),
        red=_team(raw.get("redTeam", {})),
    )


def _picks(team_md: dict) -> list[PlayerPick]:
    return [
        PlayerPick(
            participant_id=p.get("participantId", 0),
            player_id=p.get("esportsPlayerId", ""),
            summoner_name=p.get("summonerName", ""),
            champion=p.get("championId", ""),
            role=p.get("role", ""),
        )
        for p in team_md.get("participantMetadata", [])
    ]


def _metadata(raw: dict) -> GameMetadata:
    blue, red = raw.get("blueTeamMetadata", {}), raw.get("redTeamMetadata", {})
    return GameMetadata(
        patch=raw.get("patchVersion", ""),
        blue_team_id=blue.get("esportsTeamId", ""),
        red_team_id=red.get("esportsTeamId", ""),
        blue_picks=_picks(blue),
        red_picks=_picks(red),
    )


class LolFeedAdapter:
    name = "lol-feed"

    def __init__(self, client: httpx.AsyncClient):
        self._client = client

    async def _api(self, path: str, **params) -> dict:
        params.setdefault("hl", settings.hl)
        r = await self._client.get(
            f"{settings.lol_api_base}/{path}",
            params=params,
            headers={"x-api-key": settings.lol_api_key},
        )
        r.raise_for_status()
        return r.json()

    async def list_live_games(self) -> list[GameRef]:
        data = await self._api("getLive")
        events = (data.get("data", {}).get("schedule", {}) or {}).get("events") or []
        out: list[GameRef] = []
        for ev in events:
            if ev.get("state") not in ("inProgress", "in_progress"):
                continue
            match = ev.get("match") or {}
            match_id = match.get("id")
            if not match_id:
                continue
            detail = await self._api("getEventDetails", id=match_id)
            games = detail["data"]["event"]["match"]["games"]
            live = next((g for g in games if g.get("state") == "inProgress"), None)
            if not live:
                continue
            teams = match.get("teams", [])
            out.append(
                GameRef(
                    game_id=live["id"],
                    match_id=match_id,
                    number=live.get("number", 0),
                    league=(ev.get("league") or {}).get("name", ""),
                    blue_code=teams[0]["code"] if teams else "",
                    red_code=teams[1]["code"] if len(teams) > 1 else "",
                    start_time=parse_ts(ev["startTime"]) if ev.get("startTime") else None,
                )
            )
        return out

    async def fetch_slice(self, game_id: str, starting_time: datetime | None) -> SliceResult:
        url = f"{settings.lol_feed_base}/window/{game_id}"
        params = {}
        if starting_time is not None:
            params["startingTime"] = iso_z(round10(starting_time))
        r = await self._client.get(url, params=params)
        if r.status_code == 204 or not r.content.strip():
            return SliceResult(frames=[], metadata=None, empty=True)
        r.raise_for_status()
        data = r.json()
        frames = [_frame(game_id, f) for f in data.get("frames", [])]
        md = _metadata(data["gameMetadata"]) if data.get("gameMetadata") else None
        return SliceResult(frames=frames, metadata=md, empty=not frames)
