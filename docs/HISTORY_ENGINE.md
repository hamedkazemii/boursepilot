# History Engine (Sprint 1)

موتور تاریخچه محلی صندوقچی — تبدیل snapshot روزانه به سری زمانی قابل query.

## هدف
- دریافت و ذخیره تاریخچه همه صندوق‌ها
- به‌روزرسانی incremental (upsert بر اساس `fund_id + trade_date`)
- SQLite محلی
- کش درخواست‌های تکراری (`request_cache`)

## جداول
| جدول | نقش |
|------|-----|
| `funds` | شناسنامه صندوق |
| `history` | OHLC، حجم، ارزش، orderbook qty، جریان حقیقی/حقوقی |
| `nav_history` | NAV و premium/discount |
| `market_snapshot` | خلاصه وضعیت کل بازار در هر اجرا |
| `daily_scores` | امتیاز و رتبه روزانه |
| `request_cache` | جلوگیری از درخواست تکراری |

## مسیر دیتابیس
```
DATABASE_PATH=data/database.db
HISTORY_CACHE_TTL_SECONDS=300
```

فایل `.db` در gitignore است.

## CLI
```bash
# همگام‌سازی همه صندوق‌ها از BRS
python tools/run_history_sync.py

# محدود برای تست
python tools/run_history_sync.py --limit 20 -v

# مسیر دیتابیس سفارشی
python tools/run_history_sync.py --db /tmp/bp.db
```

## استفاده در کد
```python
from core.history import HistoryEngine

engine = HistoryEngine()
result = engine.sync_daily()
series = engine.get_series("عیار", limit=120)
print(engine.stats())
```

## اتصال به Daily Rank
`DailyRankPipeline` بعد از امتیازدهی:
1. quotes همان روز را در `history` upsert می‌کند
2. `daily_scores` را ذخیره می‌کند

بدون درخواست شبکهٔ اضافه.

## تست
```bash
python -m unittest tests.test_history_engine -v
```
