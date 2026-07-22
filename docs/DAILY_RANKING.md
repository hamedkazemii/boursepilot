# رنکینگ روزانه صندوقچی

## اجرا

```bash
# فقط کاتالوگ/اسنپ‌شات
python tools/run_snapshot.py

# رنکینگ بدون NAV (سریع)
python tools/run_daily_rank.py --no-nav

# رنکینگ با NAV
python tools/run_daily_rank.py --nav

# پیش‌سفارش (برای ۸:۴۵–۹)
python tools/run_preopen_scan.py
```

## خروجی‌ها
- `data/snapshots/YYYY-MM-DD/fund_catalog.json`
- `data/snapshots/YYYY-MM-DD/daily_ranking.json`
- `data/snapshots/YYYY-MM-DD/daily_ranking.txt`
- `data/snapshots/latest/*`
- `reports/daily_ranking.*`

## فاکتورها
نقدشوندگی، فشار پیش‌سفارش، جریان پول، مومنتوم، حجم/ارزش، حباب/تخفیف NAV

وزن‌ها: `config/scoring.yaml`
