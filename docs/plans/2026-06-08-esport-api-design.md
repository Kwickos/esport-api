# esport-api — Design

> **Live** esports data API, self-built and self-operated. Multi-game by design.
> Design document — 2026-06-08.

## 1. Context & goal

Free tiers of existing esports data providers are limited (live-data caps). Goal: **build our own collection pipeline**, without depending on any third-party data provider.

**Locked-in decisions:**

| Topic | Decision |
|-------|----------|
| Game #1 | **League of Legends** (first supported game; the platform is multi-game by design) |
| Granularity | **Score + key events** (kills, objectives, picks/bans) with timestamps |
| LoL source | **Unofficial raw lolesports endpoints** (free) |
| Computer vision | **Set aside for LoL**; reserved for games **without a feed** (CS2/Valorant), later |
| Stack | **Python / FastAPI** (a single language until the future CV module) |
| Deployment | **Railway** (Docker), Postgres + Redis |

## 2. Data sources (validated live, June 2026)

Common header: `x-api-key: 0TvQnueqKa5mxJntVWt0w4LpLfEkrV1Ta8rQBb9Z` (well-known public key, the one used by lolesports.com).

| Endpoint | Provides | Validated |
|----------|----------|-----------|
| `esports-api.lolesports.com/persisted/gw/getSchedule?hl=en-US` | Schedule, leagues, matches, teams | ✅ 45 KB |
| `.../getLive?hl=en-US` | Matches in progress | ✅ |
| `.../getEventDetails?hl=en-US&id={matchId}` | Match → games (ids, sides, VODs) | ✅ |
| `feed.lolesports.com/livestats/v1/window/{gameId}` | Telemetry: `gameMetadata` (picks/roles/patch) + `frames` (~10 s: gold/kills/towers/dragons) | ✅ 16 KB |
| `feed.lolesports.com/livestats/v1/details/{gameId}` | Same but more granular (per second, player/item stats) | to confirm in spike |

**Latency note**: the feed isn't instantaneous (anti-spoiler delay, a few dozen seconds), vs ~300 ms for stream-based computer vision. Acceptable for "score + events".

### 2.1 Actual semantics of the `window` feed (validated in the Phase 0 spike)

Concrete findings from running the pipeline against real games:

- **`window/{gameId}` without `startingTime`** = "live now" frames (zeros if nothing is in progress) — **unusable for replay**. You MUST pass `startingTime`.
- **`window/{gameId}?startingTime=T`** returns **a single ~10 s slice** (~30-45 frames at a ~0.2 s cadence). `startingTime` must be a **multiple of 10 s** (otherwise 400).
- **HTTP 204 (empty body)** = `T` is **before the 1st frame** (pre-game/draft, ~10-15 min after the match's `startTime`) **or after the last one** (game finished).
- **Replaying a full game** = walking slice by slice (`cursor += 10 s`), ~180-260 calls for 30-45 min. **LIVE, it's a single call / 10 s / game** → very cheap. The batch is only heavy when replaying the past.
- **Coverage per league**: LCS/LEC/LCK OK; **the LPL (China) has NO livestats** (204 everywhere) → ingestion must detect and skip games without a feed.
- **Sufficient resolution**: we keep **1 frame / 10 s slice**; more than enough for "score + events" (a double KILL within the same slice = 1 grouped event).
- `gameState` ∈ {`in_game`, `finished`, `paused`}; useful team fields: `totalKills`, `towers`, `barons`, `inhibitors`, `dragons` (**list of types**: hextech/mountain/infernal/elder…), `totalGold`.

Reproducible spike: [`spike/phase0_lol_spike.py`](../../spike/phase0_lol_spike.py) (stdlib only, `python3 spike/phase0_lol_spike.py`).

## 3. Architecture

### 3.1 Core principle: source-agnostic

The source API provides **frames** (snapshots), not events. We **derive** events by diffing frame N vs N-1. Everything goes through a normalized format so that a new source (CV, scraping) is just a simple adapter.

```python
class SourceAdapter(Protocol):
    async def list_live_games(self) -> list[GameRef]: ...
    async def pull_frames(self, game_id: str) -> list[NormalizedFrame]: ...

# LolFeedAdapter (now) → Cs2VisionAdapter (later) → ...
```

The engine (diff → events) and the API know **only** `NormalizedFrame`.

### 3.2 Flow

```
SchedulePoller (~2 min) ─→ upsert matches (upcoming/live)
LiveDetector            ─→ getEventDetails → which game is live
GamePoller (1/live game, ~10 s) ─→ window feed
     ↓ dedup by rfc460Timestamp
     ↓ DIFF ENGINE → events
     ↓ writes frames + events; publishes on Redis
REST API + WebSocket ─→ serves / pushes to the client
```

### 3.3 Diff engine (the core of the value)

```
frame N-1: blue.totalKills = 3     frame N: blue.totalKills = 4
   → EVENT { type: KILL, team: blue, ts: rfc460Timestamp }
```

Same for `towers`, `dragons`, `barons`, `inhibitors`, gold leads. Picks/bans from `gameMetadata`.

## 4. Data model

| Table | Key columns |
|-------|-------------|
| `leagues` | id, slug, name, region, image |
| `teams` | id, code, name, logo |
| `players` | id, handle, team_id, role |
| `matches` | id, league_id, format (BO1/3/5), status, scheduled_at |
| `games` | id, match_id, number, patch, winner, sides |
| `frames` | game_id, ts, (gold/kills/towers/dragons per team) — raw trace |
| `events` | game_id, ts, type, team, payload — **exposed as a priority by the API** |

- **Internal** IDs (source-id → internal-id mapping in the adapter) to decouple the public schema from the source.
- `frames` = audit/replayability; `events` = the main product.

## 5. Public API

**REST (FastAPI)**: `/leagues`, `/matches?status=live`, `/matches/{id}`, `/games/{id}/events`, `/games/{id}/frames` (paginated, in-house normalized schema).

**Real-time**: `WebSocket /live/{gameId}` (or SSE) — pushes each event as soon as it's detected.

**Auth & quotas**: API keys + rate limiting via Redis → **a free plan defined by ourselves**.

## 6. Deployment

```
Service "api"    — uvicorn FastAPI (REST + WS)
Service "worker" — asyncio pollers (continuous)
Postgres         — data
Redis            — live bus (worker→api) + rate limiting
```

Same codebase, 2 processes. ~5-15 €/month to start. MVP: worker+api can be merged, to be split later.

## 7. Roadmap

| Phase | Content | Effort |
|-------|---------|--------|
| 0 — Spike | schedule→eventDetails→window→derived events script | ½ day |
| 1 — LoL ingestion | Postgres schema (SQLAlchemy/Alembic), `LolFeedAdapter`, 3 pollers, diff engine | a few days |
| 2 — REST API | Endpoints, pagination, normalized schema | a few days |
| 3 — Live push | WebSocket + Redis pub/sub | a few days |
| 4 — Auth & quotas | API keys, rate limiting | 1-2 days |
| 5 — Deployment | Docker + Railway | 1 day |
| 6+ | Multi-game expansion (more adapters), CV ingestion for feed-less titles | ongoing |

> Product-level milestones and the full game-coverage matrix (~20 titles) live in [`ROADMAP.md`](../../ROADMAP.md).

## 8. Risks & mitigations

- **Unofficial endpoint** → may be throttled/cut off. Mitigation: reasonable polling, caching, monitoring; source-agnostic architecture = a pivot is possible.
- **Feed latency** (dozens of s) → accepted for the desired granularity.
- **Legal**: gray area is fine for personal/learning use; to be revisited in case of commercialization.
- **Asset mapping**: `championId` is already a readable name ("Sion"); images via Data Dragon.

## Appendix — Live proof (June 2026)

`getSchedule` → 45 KB (events/leagues/teams). `getLive` → OK. `getEventDetails` (BO5 match) → 5 games + ids. `window/{gameId}` → patch 16.11, rosters, picks (Sion/Nocturne/Anivia/Lucian/Yuumi…), gold/kills/towers/dragons frames. Full pipeline validated.
