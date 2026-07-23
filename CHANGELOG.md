# Changelog

## 2026-07-23 — v0.6.0 (History Engine + Smart Telegram Report)

### Added
- **History Engine (Sprint 1)**
  - `core/database/` — SQLite connection + schema v1
  - `core/history/` — repository + incremental sync engine
  - جداول: `funds`, `history`, `nav_history`, `market_snapshot`, `daily_scores`, `request_cache`
  - CLI: `tools/run_history_sync.py`
  - اتصال به `DailyRankPipeline` برای persist خودکار
  - تست: `tests/test_history_engine.py`
  - مستند: `docs/HISTORY_ENGINE.md`
- **Smart multi-message Telegram report**
  - `services/telegram/smart_report.py`
  - خلاصه بازار + ۵ پیام برتر + ۵ پیام ضعیف (جداگانه)
  - `TelegramPublisher.publish_smart_morning`
  - CLI: `--smart` / `--compact`
  - تست: `tests/test_smart_report.py`
- **Market summary analytics**
  - `core/analytics/market_summary.py`
- **Workflows**
  - `daily_rank.yml`, `preopen.yml`
  - `morning.yml` → history sync + smart rank (دیگر `app.py` خام نیست)
- اسکلت پکیج‌های آینده: `core/indicators/`, `core/ai/`, `services/portfolio/`, `workflows/`

### Changed
- `services/telegram/` به پکیج تفکیک شد (`client`, `publisher`, `smart_report`)
- shim سازگاری: `services.telegram_publisher` و importهای قبلی
- `config.py`: `DATABASE_PATH`, `HISTORY_CACHE_TTL_SECONDS`, `TELEGRAM_SMART_REPORT`, `TELEGRAM_TOP_N/WORST_N`
- رفع import دایره‌ای در `core.scoring` / `core.factors`

### Secrets
- `BRS_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

---

## 2026-07-22 — v0.5.0 (تلگرام V1 + جاب‌های کانال)

### Added
- `services/telegram.py` — ارسال با chunk و retry
- `services/telegram_publisher.py` — فرمت/ارسال رنکینگ و پیش‌گشایش
- `services/telegram_bot.py` — دستورهای /rank /worst /preopen /fund /market
- CLI:
  - `tools/run_telegram_rank.py`
  - `tools/run_telegram_preopen.py`
  - `tools/run_telegram_bot.py`
- `docs/TELEGRAM.md`
- `tests/test_telegram.py`

### Secrets
- `BRS_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID` (کانال)

---

## 2026-07-22 — v0.4.0 (کشف روزانه + امتیاز + رنکینگ فارسی)

### Added
- discovery/snapshot/score factors/ranking/preopen CLI

---

## 2026-07-22 — v0.3.0 (BRS API Layer)
- BrsProvider + DTO + tests
