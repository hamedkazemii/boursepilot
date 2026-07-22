# Changelog

## 2026-07-22 — v0.5.0 (تلگرام V1 + جاب‌های کانال)

### Added
- `services/telegram.py` — ارسال با chunk و retry
- `services/telegram_publisher.py` — فرمت/ارسال رنکینگ و پیش‌سفارش
- `services/telegram_bot.py` — دستورهای /rank /worst /preopen /fund /market
- CLI:
  - `tools/run_telegram_rank.py`
  - `tools/run_telegram_preopen.py`
  - `tools/run_telegram_bot.py`
- GitHub Actions:
  - `daily_rank.yml`
  - `preopen.yml`
  - `morning.yml` به مسیر جدید
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
