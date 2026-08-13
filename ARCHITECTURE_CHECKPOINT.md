# Architecture Checkpoint

## Overview (from ARCHITECTURE.md)

# BoursePilot Architecture

## Data Flow (v0.6)

```
BRS API (AllSymbols / Symbol / Nav)
        │
        ▼
  providers/brs_*
        │
        ├──────────────► History Engine ──► SQLite
        │                 (funds, history, nav, scores, cache)
        ▼
  FundCatalog / SnapshotStore (JSON snapshots)
        │
        ▼
  ScoreEngine (factors: liquidity, orderbook, money_flow, momentum, volume, nav)
        │
        ▼
  FundRanker
        │
        ├──────────────► daily_scores (SQLite)
        ▼
  Analytics (MarketSummary)
        │
        ▼
  Telegram smart report (summary + top cards + worst cards)
        │
        ▼
  Channel / Bot
```

## Packages

| Path | Role |
|------|------|
| `core/database` | SQLite connection + schema |
| `core/history` | Incremental historical store |
| `core/analytics` | Market-level summary |
| `core/scoring` | Multi-factor score |
| `core/ranking` | Order assessments |
| `core/pipeline` | Daily rank orchestration |
| `core/preopen` | Pre-market pressure |
| `core/indicators` | *(Sprint 2)* technical/risk series |
| `services/providers` | Market data adapters |
| `services/telegram` | Send + format + publish |
| `services/discovery` | Fund catalog |
| `services/snapshot` | JSON snapshot IO |
| `workflows` | *(future)* scheduled job entrypoints |
| `reports` | Text/JSON human reports |
| `tools` | CLI entrypoints |

## Design rules
1. هیچ secret در کد hardcode نشود — فقط env / GitHub Secrets
2. هسته تحلیل به فرمت خام BRS وابسته نباشد — فقط DTOهای `SymbolQuote` / `NavData`
3. هر Feature: تست + dry-run + commit جدا روی `develop`
4. گزارش هوشمند = «دانش» نه فقط فهرست رتبه (دلایل قابل توضیح)

## Project Context (from PROJECT_AGENT_MASTER_CONTEXT.md)

# BoursePilot Agent Master Context v1.5

## Role
You are the official BoursePilot development agent.

You are a Senior Python Architect responsible for production-grade development.

## Communication
- User language is Persian.
- Explain technical topics clearly in Persian.
- Do not assume the user knows implementation details.
- Before major changes explain plan briefly.

## Project
BoursePilot is an intelligent investment assistant for Iranian ETF markets.

Repository:
~/projects/boursepilot

Current branch:
agent/v1.5-development

Current version:
v1.5 Intelligent Platform

## Completed Capabilities

- SQLite history engine
- Incremental market data storage
- Technical indicators
- Smart ranking engine
- Trend analysis
- Bubble analysis
- AI Advisor
- Portfolio management
- Watchlist
- Telegram intelligent reporting
- Human-readable Persian reports

## Architecture

Layers:

core/
- business logic
- scoring
- ranking
- intelligence

services/
- market providers
- BRS API
- TSETMC
- Telegram

data/
- SQLite
- snapshots
- cache

reports/
- user communication

## Infrastructure

Main development server:
Linux VPS

Market data server:
Iran server

The Iran server is used for:
- market data collection
- provider reliability
- reducing network dependency

## Development Rules

Always:

1. Check git status.
2. Check current branch.
3. Review architecture before coding.
4. Keep backward compatibility.
5. Write tests for new features.
6. Commit changes with meaningful messages.
7. Avoid unnecessary refactoring.

Never:
- rewrite architecture without approval
- remove existing features
- change APIs without migration plan

## Roadmap

### v1.6

Sprint A:
Provider Reliability Layer

Tasks:
- retry mechanism
- exponential backoff
- circuit breaker
- provider health monitoring
- fallback to cached data

Sprint B:
Real-time Intelligence

Tasks:
- market event scanner
- volume alerts
- price breakout detection
- Telegram notifications

Sprint C:
Comparison Engine

Tasks:
- compare funds
- comparative reports
- user portfolio analysis

## Product Direction

BoursePilot should become a Persian conversational investment assistant.

Focus:
- simple explanations
- personalized advice
- transparent analysis
- no financial guarantee

## Current First Task

Provider Reliability Layer.

Before implementation:
audit existing providers and architecture.

## Directory Structure (as of checkpoint)

- /config
- /core
- /data
- /docs
- /reports
- /services
- /tests
- /tools
- /workflows

## Key Files

- config/scoring.yaml
- data/database.db (SQLite)
- data/fund_registry.json
- data/fund_scores.json
- VERSION (0.7.0)
- ARCHITECTURE.md
- PROJECT_AGENT_MASTER_CONTEXT.md
- README.md
- CHANGELOG.md

## Current Git Status

- Branch: feature/architecture-v2-sync (up to date with origin)
- Untracked files:
  - .env.external.backup.20260730_183108
  - PROJECT_CONTEXT.md
  - data/history/2026-08-01.json
  - data/receiver/
  - docs/agents/
  - services/providers/gateway_provider.py.bak
  - services/receiver/api.py.backup.1785597771
  - services/receiver/models.py.final.1785602226
  - services/receiver/models.py.stable.1785601178
  - services/receiver/storage.py.backup.1785601912
  - services/receiver/storage.py.final.1785602226

## Pending Work / Notes

**Sync V1 implementation plan** (under review):
- Add atomic writes
- Add file locking
- Replace received_chunks with per-chunk tracking
- Add checksum verification
- Add cleanup service
- Add state migration v1 → v2
- Add tests

## Risks / TODOs (pre‑implementation)

- Ensure migration includes backup and rollback mechanism.
- Define lock granularity (per‑file vs per‑directory) to avoid unnecessary contention.
- Specify cleanup policy (age/size thresholds) to avoid premature deletion of active chunks.
- Choose checksum algorithm (e.g., SHA256) and define handling of mismatches (retry, alert, discard).
- Write unit tests for atomic write, lock, verification, and cleanup; integration tests for end‑to‑end pipeline.
- Update CHANGELOG.md and any relevant documentation (README, docs) after implementation.
- Verify that existing services (Telegram reporting, ranking_app, etc.) continue to function with the new storage layer.

---
*Checkpoint generated on 2026-08-02 14:40 UTC.*