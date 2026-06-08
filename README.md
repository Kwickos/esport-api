<div align="center">

# esport-api

**Self-hosted, independent _live_ esports data API** — collect and serve your own competitive-gaming data, with no dependency on a third-party provider. Multi-game by design; League of Legends is the first supported game, with many more on the [roadmap](ROADMAP.md).

[![CI](https://github.com/Kwickos/esport-api/actions/workflows/ci.yml/badge.svg)](https://github.com/Kwickos/esport-api/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

</div>

> ⚠️ **Unofficial** project, not affiliated with, endorsed by, or sponsored by any game publisher, esports league, tournament organizer, or data provider. All game names, logos, and trademarks are the property of their respective owners. Read the [DISCLAIMER](DISCLAIMER.md) before use.

## Why

The free tiers of esports data providers are limited, especially for **live** data. `esport-api` collects the data itself (score + key events: kills, objectives, picks/bans, all timestamped) and exposes it through **your own** REST + WebSocket. You control your free tier.

> Full design: [`docs/plans/2026-06-08-esport-api-design.md`](docs/plans/2026-06-08-esport-api-design.md)

## Architecture

```
app/
├─ config.py · timeutil.py          settings + time helpers (10s alignment)
├─ schemas/domain.py                normalized types (the common language)
├─ sources/
│  ├─ base.py                       SourceAdapter — THE source-agnostic contract
│  └─ lol_feed.py                   LoL adapter (raw lolesports endpoints)
├─ engine/diff.py                   frames → events engine (the core of the value)
├─ db/ (base · models · repository) SQLAlchemy async, 7 tables
├─ ingestion/ (pollers · worker)    LiveGameTracker + GamePoller (asyncio)
├─ api/routes.py · main.py          REST + FastAPI app
tests/                              unit tests
spike/phase0_lol_spike.py           end-to-end proof (stdlib only)
```

**Key principle: source-agnostic.** Everything converges to `NormalizedFrame`. Adding a game via computer vision later = write a new adapter, nothing else moves.

## Quick start (dev, SQLite, zero setup)

```bash
make dev                 # venv + install + pre-commit  (or: pip install -e ".[dev]")
cp .env.example .env

make run                 # API    → http://localhost:8000/docs
make worker              # worker → ingests when a match is live
```

## Endpoints

| Method | Route | Returns |
|---------|-------|-------|
| GET | `/health` | ping |
| GET | `/leagues` | leagues |
| GET | `/matches?status=inProgress` | matches |
| GET | `/matches/{id}` | match + games |
| GET | `/games/{id}/events` | derived events (KILL/TOWER/DRAGON/BARON/INHIB) |
| GET | `/games/{id}/frames` | raw frames |
| WS | `/live/{id}` | live push: `subscribed` ack, then `event` / `score` messages |

## Prod (Docker, Postgres)

```bash
docker compose up --build
```

## Attribution

`esport-api` is **free for everyone** (MIT). In return, **if you use it** (app, service, research, video…), **please credit the project**:

> Data provided by [esport-api](https://github.com/Kwickos/esport-api).

Keeping the copyright notice from the [LICENSE](LICENSE) is also **mandatory**.

## Contributing

Contributions are welcome! Read the [contribution guide](CONTRIBUTING.md) and the [code of conduct](CODE_OF_CONDUCT.md). To report a vulnerability: [SECURITY.md](SECURITY.md).

## Roadmap

The goal is **broad multi-game coverage** behind a single normalized API — as many
esports titles as possible, added incrementally as adapters. The source-agnostic
core is what makes that realistic.

See the full [**ROADMAP**](ROADMAP.md) for capability milestones and the
game-coverage matrix (~20 titles across MOBA, FPS, sports, fighting, RTS, BR).

- **Now (v0.1)** — source-agnostic core, diff engine, first game adapter (League of Legends), REST API, CI ✅
- **Next** — real-time WebSocket push → access control (API keys & quotas) → hardening → multi-game expansion → computer-vision ingestion for titles without a public feed

## License

[MIT](LICENSE) © 2026 Kwickos
