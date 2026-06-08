# Roadmap

`esport-api` aims to be a comprehensive, self-hosted live data layer for
competitive gaming — **as many esports titles as possible, behind one normalized
API**. The source-agnostic architecture (every game is just an adapter producing
`NormalizedFrame`s) is what makes broad coverage realistic: the engine, storage,
and API never change when a new title is added.

> This roadmap is a direction, not a dated commitment. Coverage grows as adapters
> land. Want a title prioritized? Open a [feature request](https://github.com/Kwickos/esport-api/issues/new/choose).

## Capability milestones

| Version | Theme | Highlights |
|---------|-------|------------|
| **v0.1** | Foundations ✅ | source-agnostic core, diff engine, first game adapter, REST API, CI |
| **v0.2** | Real-time delivery | WebSocket / SSE live push, Redis pub/sub |
| **v0.3** | Access control | API keys, rate limiting, configurable usage tiers |
| **v0.4** | Hardening | Pydantic response schemas, pagination, Alembic migrations, OpenAPI docs |
| **v0.5** | Multi-game expansion | normalized cross-game schema, second & third adapters |
| **v0.6** | Computer-vision ingestion | read live broadcast overlays for titles without a public feed |
| **v0.7** | History & stats | post-game aggregates, player/team stats, head-to-head, standings |
| **v0.8** | Integrations | webhooks, Discord bot, push notifications |
| **v0.9** | Scale & reliability | horizontal workers, metrics & alerting, caching, backfill |
| **v1.0** | Stable release | documented, versioned public API |

## Game coverage

Ingestion method per title: **Feed** (official-ish data endpoints), **CV**
(computer vision on the broadcast), **Scrape** (community sites).
Status: ✅ Live · 🛠️ In progress · 🗓️ Planned · 🔬 Researching.
Help is welcome on any 🗓️ / 🔬 title — see [CONTRIBUTING](CONTRIBUTING.md).

### MOBA
| Title | Method | Status |
|-------|--------|--------|
| League of Legends | Feed | ✅ Live (first adapter) |
| Dota 2 | Feed (Valve WebAPI) | 🛠️ In progress |
| Mobile Legends: Bang Bang | CV / Scrape | 🗓️ Planned |
| Honor of Kings | CV | 🔬 Researching |
| Wild Rift | CV | 🔬 Researching |

### Tactical / FPS
| Title | Method | Status |
|-------|--------|--------|
| Counter-Strike 2 | CV / Scrape | 🗓️ Planned |
| VALORANT | CV / Scrape | 🗓️ Planned |
| Rainbow Six Siege | Scrape / CV | 🗓️ Planned |
| Overwatch 2 | CV | 🔬 Researching |
| Apex Legends | CV | 🔬 Researching |
| Call of Duty (CDL) | CV | 🔬 Researching |

### Sports / Racing
| Title | Method | Status |
|-------|--------|--------|
| Rocket League | Feed / CV | 🗓️ Planned |
| EA Sports FC | CV | 🔬 Researching |

### Fighting
| Title | Method | Status |
|-------|--------|--------|
| Street Fighter 6 | CV | 🔬 Researching |
| Tekken 8 | CV | 🔬 Researching |

### RTS
| Title | Method | Status |
|-------|--------|--------|
| StarCraft II | Scrape / CV | 🔬 Researching |
| Age of Empires IV | Scrape | 🔬 Researching |

### Battle Royale
| Title | Method | Status |
|-------|--------|--------|
| PUBG | Feed / CV | 🔬 Researching |
| Fortnite | Scrape | 🔬 Researching |

Don't see your game? [Request it.](https://github.com/Kwickos/esport-api/issues/new/choose)
