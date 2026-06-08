# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2026-06-08

### Added

- **Phase 0 — spike** (`spike/phase0_lol_spike.py`): end-to-end proof of the
  LoL pipeline on a full game (schedule → eventDetails → window → derived
  events), with no dependencies.
- **Phase 1 — scaffold**:
  - Source-agnostic core: `SourceAdapter` + `NormalizedFrame` /
    `DerivedEvent` / `GameRef` types.
  - `LolFeedAdapter`: raw unofficial lolesports endpoints.
  - `frames → events` diff engine (KILL / TOWER / DRAGON / BARON / INHIBITOR).
  - Async SQLAlchemy models (SQLite dev / Postgres prod) + repository.
  - asyncio pollers: `LiveGameTracker` + `GamePoller`.
  - FastAPI REST API (read) + ingestion worker.
  - Unit tests for the diff engine.
- **Open-source flow**: MIT license, CONTRIBUTING, code of conduct, SECURITY,
  DISCLAIMER, GitHub Actions CI (lint + tests), pre-commit, Dependabot,
  issue/PR templates.

[Unreleased]: https://github.com/Kwickos/esport-api/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Kwickos/esport-api/releases/tag/v0.1.0
