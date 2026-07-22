# Changelog

## 2026-07-22 — v0.4.0 (کشف روزانه + امتیاز + رنکینگ فارسی)

### Added
- `config/scoring.yaml` — وزن‌ها و آستانه‌های قابل تنظیم
- کشف روزانه صندوق‌ها: `services/discovery/fund_catalog.py`
- اسنپ‌شات: `services/snapshot/store.py`
- فاکتورهای تحلیلی:
  - نقدشوندگی، فشار پیش‌سفارش، جریان پول، مومنتوم، حجم/ارزش، NAV premium
- `ScoreEngine` + `FundAssessment` با دلایل فارسی
- `FundRanker` (کلی و per-type)
- `DailyRankPipeline`
- گزارش فارسی: `reports/persian_ranking.py`
- تحلیل پیش‌سفارش: `core/preopen/`
- CLI:
  - `tools/run_snapshot.py`
  - `tools/run_daily_rank.py`
  - `tools/run_preopen_scan.py`
- تست: `tests/test_score_engine.py`
- مستند: `docs/DAILY_RANKING.md`

### Notes
- مسیر داده همچنان BRS است
- NAV در رنکینگ روزانه اختیاری (`FETCH_NAV_IN_DAILY_RANK` / `--nav`)
- هنوز تلگرام/وب‌اپ/پرتفوی شخصی پیاده نشده

---

## 2026-07-22 — v0.3.0 (صندوقچی / BRS API Layer)

### Product
- نام محصول کاربر-محور: **صندوقچی**
- مسیر داده اصلی: **BrsApi.ir** (نه اسکرپ TSETMC)

### Added
- لایه provider استاندارد BRS + DTO + تست + smoke tool
- `docs/BRS_API.md`

---

## 2026-07-20

### Added
- Real TSETMC InstrumentInfo connection
- Real ClosingPrice connection
- Real OrderBook connection
- FundDiscovery module
