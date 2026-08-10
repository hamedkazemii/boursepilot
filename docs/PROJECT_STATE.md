# BoursePilot (صندوقچی) — Project State v0.7.1

**Last Updated:** 2026-08-08  
**Branch:** `feature/architecture-v2-sync`  
**Commit:** `d73da22` (cleanup: legacy tests, tools, migrations, backups)

---

## 🎯 Current Status: Production-Ready Core + Clean Architecture

### ✅ What Works (Verified)

| Component | Status | Tests |
|-----------|--------|-------|
| **Iran Gateway API** | ✅ Live on 89.44.241.230:9000 | Manual verified |
| **Sync Pipeline (Iran → External)** | ✅ Chunked transfer, validation, reassembly | 156 tests pass |
| **External Receiver API** | ✅ Live on 82.115.8.100:8000 | 156 tests pass |
| **SQLite History Engine** | ✅ Incremental upsert, OHLC + orderbook + money_flow | Tests pass |
| **Indicator Engine** | ✅ EMA/RSI/MACD/ATR/Bollinger/Sharpe/Sortino/MaxDD | Tests pass |
| **ScoreEngine (6 factors)** | ✅ liquidity, orderbook, money_flow, momentum, volume, nav | Tests pass |
| **SmartRanker** | ✅ Percentile normalization, trend-aware, quality gate | Tests pass |
| **Daily Analysis Pipeline** | ✅ Live/snapshot/demo → history → indicators → rank → persist | Tests pass |
| **Telegram Bot Core** | ✅ Smart multi-message, inline keyboards, user/portfolio/watchlist | Tests pass |
| **AI Advisor** | ✅ Rule-based + optional LLM + daily learning (ai_memory/ai_lessons) | Tests pass |

---

## 🧪 Test Suite (156 passing)

```
tests/test_brs_mapper.py         ✅ 6 tests
tests/test_brs_provider.py       ✅ 7 tests
tests/test_daily_analysis.py     ✅ 2 tests
tests/test_gateway_provider.py   ✅ 15 tests (mock + factory)
tests/test_history_engine.py     ✅ 6 tests
tests/test_portfolio_ai.py       ✅ 2 tests
tests/test_receiver_v1.py        ✅ 38 tests
tests/test_score_engine.py       ✅ 3 tests
tests/test_smart_ranker.py       ✅ 2 tests
tests/test_smart_report.py       ✅ 5 tests
tests/test_sync_v1.py            ✅ 24 tests
tests/test_telegram.py           ✅ 7 tests
tests/test_textnorm.py           ✅ 3 tests
```

**Total: 156 tests, 0 failures**

---

## 📁 Clean Architecture (Post-Cleanup)

```
boursepilot/
├── config.py                    # Settings from env
├── config/scoring.yaml          # Factor weights & thresholds
├── core/
│   ├── database/                # connection + schema v2
│   ├── history/                 # engine + repository
│   ├── indicators/              # IndicatorEngine
│   ├── scoring/                 # ScoreEngine + models + weights
│   ├── factors/                 # 6 factor implementations
│   ├── ranking/                 # smart_ranker (source of truth)
│   ├── pipeline/                # daily_analysis + daily_rank
│   ├── analytics/               # explain + market_summary
│   ├── ai/                      # AIAdvisor (learning + advice)
│   └── preopen/                 # پیش‌گشایش
├── services/
│   ├── providers/               # BRS client/mapper/provider/factory + gateway_mock
│   ├── discovery/               # FundCatalog
│   ├── snapshot/                # JSON snapshots
│   ├── portfolio/               # PortfolioService
│   ├── telegram/                # client, keyboards, publisher, smart_report
│   ├── telegram_bot.py          # SandoghchiBot
│   └── sync/                    # chunker, transport, receiver, worker (NEW)
│       ├── worker/              # SyncWorker (Phase 5A)
│       └── ...
├── tools/                       # CLI entrypoints
│   ├── run_daily_analysis.py
│   ├── run_telegram_rank.py
│   ├── run_telegram_bot.py
│   ├── run_history_sync.py
│   └── run_telegram_preopen.py
├── reports/                     # Generated output
├── data/                        # SQLite + history JSON (gitignored)
├── tests/                       # 13 focused test files (156 tests)
└── docs/                        # Documentation
```

---

## 🗑️ Removed (Cleanup Complete)

| Category | Count | Examples |
|----------|-------|----------|
| Old test files | 22 | test_analyzer, test_bpi, test_classifier, test_collector, test_discovery, test_market, test_migration, test_parser, test_scanner, test_reliability, test_tsetmc_api, etc. |
| Old tools | 10 | build_fund_registry, classify_fund_registry, endpoint_explorer, fund_validator, generate_fund_report, reclassify_v2/v3, validate_fund_registry |
| Migration scripts | 7 | migrate_v020.sh, release_0_5_migration.sh, upgrade_* scripts |
| Backup files | 15+ | config.py.backup.*, market_gateway_api.py.backup.*, *.bak, *.tar.gz |
| Legacy sync sender | 1 folder | services/sync/sender/ (old chunker) |

---

## 🔄 Data Flow (Verified End-to-End)

```
BRS API (Iran)
    │
    ▼
Iran Server (89.44.241.230) — Gateway API :9000
    ├─ GET /symbols → AllSymbols
    ├─ GET /symbol/{symbol} → Quote + Orderbook + Money Flow
    ├─ GET /nav → NAV data
    ├─ Chunking (services/sync/chunker.py)
    └─ Sync Send (services/sync/worker/sender.py) → HTTPS
    │
    ▼ X-Sync-Key auth
External Server (82.115.8.100) — Receiver API :8000
    ├─ POST /sync/manifest
    ├─ POST /sync/chunk (×N)
    ├─ Validate checksum + decompress + reassemble
    └─ Store in SQLite (data/receiver/)
    │
    ▼
Daily Pipeline (08:50, 12:30, 16:30 Tehran)
    History upsert → Indicators → SmartRanker → Persist → Quality Gate
    │
    ▼
Telegram Smart Report (multi-message)
    Summary + Top 5 cards + Worst 5 cards + Inline buttons
    │
    ▼
User Commands: /today /top /worst /fund /portfolio /pf_add /watch /ask
```

---

## ⚙️ Configuration (Environment Variables)

### Iran Server (.env)
```bash
ROLE=collector
BRS_API_KEY=...
MARKET_GATEWAY_TOKEN=...
SYNC_RECEIVER_URL=http://82.115.8.100:8000
SYNC_API_KEY=...
SYNC_CHUNK_SIZE=50
SYNC_INTERVAL_SECONDS=900
```

### External Server (.env)
```bash
ROLE=receiver
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=182782238
BRS_API_KEY=...  # for fallback
MARKET_GATEWAY_URL=http://89.44.241.230:9000
MARKET_GATEWAY_TOKEN=...
SYNC_API_KEY=...
AI_API_URL=https://api.groq.com/openai/v1
AI_API_KEY=...
AI_MODEL=llama-3.1-8b-instant
```

---

## 🚀 Next Steps (Priority Order)

### P0 — Production Deployment (1-2 days)
| Task | Details |
|------|---------|
| **Systemd: Iran Gateway** | `market-gateway.service` on :9000 |
| **Systemd: Iran Sync Sender** | `sync-sender.service` (run_cycle every 15min) |
| **Systemd: External Receiver** | `sync-receiver.service` on :8000 |
| **Systemd: External Telegram Bot** | `telegram-bot.service` (polling) |
| **Cron: Daily Analysis** | 08:50, 12:30, 16:30 Tehran |
| **Cron: Telegram Rank** | After each analysis |
| **SSL/Reverse Proxy** | nginx + certbot for Receiver API |

### P1 — Telegram UX Polish (4 hours)
| Task | Status |
|------|--------|
| `/help` command + menu | ⬜ |
| Inline button handlers (refresh/details/add_to_portfolio) | ⬜ |
| Welcome message on `/start` | ⬜ |
| Friendly error messages (no stack traces) | ⬜ |
| Typing indicator for `/ask` | ⬜ |

### P2 — LLM Integration (30 min)
| Task | Status |
|------|--------|
| Configure `AI_API_URL` + `AI_API_KEY` (Groq/OpenRouter) | ⬜ |
| Test `/ask` with LLM fallback | ⬜ |

### P3 — Monitoring & Alerting (30 min)
| Task | Status |
|------|--------|
| Health endpoint + Telegram alert if sync fails | ⬜ |
| Quality gate alert (sane=false) | ⬜ |

### P4 — Advanced Features (Future)
- Smart Alerts (volume spike, EMA cross, money flow shift)
- `/compare` fund comparison
- Web App + Admin Panel
- Real history backfill (6+ months)

---

## 📊 Quality Metrics (Current)

| Metric | Value | Target |
|--------|-------|--------|
| Universe size | ~30 funds | 50+ |
| Top 5 avg score | ~70 | >60 |
| Worst 5 avg score | ~31 | <40 |
| Gap (top-worst) | ~39 | >8 (gate) |
| Ranking sane | ✅ true | true |
| Test coverage | 156 tests | >150 |

---

## 🔑 Key Files for Next Developer

| File | Purpose |
|------|---------|
| `docs/AGENT_HANDOFF.md` | Complete spec for any agent |
| `docs/ARCHITECTURE_V2.md` | Architecture details |
| `docs/PHASE5_CHECKLIST.md` | Sync worker implementation plan |
| `core/pipeline/daily_analysis.py` | Main pipeline entry |
| `services/telegram_bot.py` | Bot implementation |
| `services/sync/worker/` | New sync worker (Phase 5A) |
| `config/scoring.yaml` | Factor weights (adjustable) |

---

## 📝 Changelog (v0.7.1 - 2026-08-08)

- **Cleanup:** Removed 55 legacy files (tests, tools, migrations, backups, old sync sender)
- **Fix:** `gateway_mock.py` now handles `symbol/{symbol}` path parameter style
- **Tests:** All 156 core tests pass
- **Git:** Committed to `feature/architecture-v2-sync` (commit `d73da22`)
- **Sync Worker:** Phase 5A structure created in `services/sync/worker/`