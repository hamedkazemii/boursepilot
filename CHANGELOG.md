# Changelog

## 2026-07-23 — v0.6.1 (Explain fix + bot buttons)

### Fixed
- توضیح صندوق‌های **ضعیف** دیگر کپی برترها نیست
- `core/analytics/explain.py` با kind=`top|worst|neutral`
- کارت تلگرام: «چرا در برترین‌هاست؟» / «چرا در ضعیف‌هاست؟»
- `ScoreEngine._summary_reasons` برای امتیاز پایین weakness-first
- فیلتر premium غیرواقعی در متن توضیح
- callbackهای منقضی دکمه بدون noise لاگ می‌شوند
- warmup ربات: پیش‌فرض snapshot-first (سریع)، live با `/refresh`

### Added
- کیبورد اینلاین منو/گزارش (`services/telegram/keyboards.py`)
- `services/telegram/rank_loader.py` — live → snapshot → demo
- `tests/test_explain.py`
- `docs/PROJECT_PROGRESS.md`
- ابزارها: `run_button_smoke_test.py`, `send_menu_now.py`, `run_telegram_live_test.py`

---

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
  - `morning.yml` → history sync + smart rank
- اسکلت پکیج‌های آینده: `core/indicators/`, `core/ai/`, `services/portfolio/`, `workflows/`

### Changed
- `services/telegram/` به پکیج تفکیک شد (`client`, `publisher`, `smart_report`)
- shim سازگاری: `services.telegram_publisher`
- `config.py`: `DATABASE_PATH`, `HISTORY_CACHE_TTL_SECONDS`, `TELEGRAM_SMART_REPORT`, `TELEGRAM_TOP_N/WORST_N`
- رفع import دایره‌ای در `core.scoring` / `core.factors`

### Secrets
- `BRS_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

---

## 2026-07-22 — v0.5.0 (تلگرام V1 + جاب‌های کانال)

### Added
- ارسال تلگرام، publisher، bot commands اولیه
- CLI telegram rank/preopen/bot
- docs/TELEGRAM.md
- tests/test_telegram.py

---

## 2026-07-22 — v0.4.0 (کشف روزانه + امتیاز + رنکینگ فارسی)
- discovery/snapshot/score factors/ranking/preopen CLI

---

## 2026-07-22 — v0.3.0 (BRS API Layer)
- BrsProvider + DTO + tests
