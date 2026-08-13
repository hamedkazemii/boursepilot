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
