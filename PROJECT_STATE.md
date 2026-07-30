# صندوقچی (BoursePilot)
## Project State
Last Update: 2026-07-23
Version: 0.7.0

# وضعیت

| بخش | وضعیت |
|-----|--------|
| BRS live provider | ✅ (در شبکه ایران/VPS) / ⚠️ SSL در sandbox |
| History SQLite + incremental | ✅ |
| Indicator Engine | ✅ |
| Smart relative ranking | ✅ |
| Top5/Worst5 sanity gap | ✅ |
| Trend-aware recommendation | ✅ |
| Smart telegram multi-message | ✅ |
| Inline bot buttons | ✅ |
| User profile on /start | ✅ |
| Portfolio + watchlist | ✅ |
| AI advisor + daily learning | ✅ |
| Optional free LLM API | ✅ (env) |
| Realtime alerts | ❌ next |
| Compare funds | ❌ next |

# کیفیت رنکینگ (نمونه)
- universe: 30
- top5_avg: ~70
- worst5_avg: ~31
- gap: ~39
- sane: true

# Secrets / Env
```
BRS_API_KEY
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
DATABASE_PATH=data/database.db
AI_API_URL=   # optional
AI_API_KEY=   # optional
AI_MODEL=llama-3.1-8b-instant
```

# Run
```bash
python tools/run_daily_analysis.py
python tools/run_telegram_rank.py --smart
python tools/run_telegram_bot.py
```

# Handoff
- docs/AGENT_HANDOFF.md
- docs/PRODUCT_UI_SPEC.md
