# صندوقچی (BoursePilot)

دستیار هوشمند صندوق‌های قابل‌معامله ایران.

**نسخه:** 0.5.0

## قابلیت‌های فعلی
- داده زنده BrsApi
- کشف روزانه صندوق‌ها
- امتیاز چندعاملی + رنکینگ فارسی
- پیش‌سفارش
- ارسال گزارش به **کانال تلگرام**
- ربات دستوری (`/rank` `/preopen` `/fund` ...)

## Secrets
```
BRS_API_KEY
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
```

## اجرا
```bash
pip install -r requirements.txt
cp .env.example .env

python -m unittest tests.test_textnorm tests.test_brs_mapper tests.test_brs_provider tests.test_score_engine tests.test_telegram -v

python tools/run_telegram_rank.py --no-nav --dry-run
python tools/run_telegram_preopen.py --dry-run
```

## مستندات
- `docs/BRS_API.md`
- `docs/DAILY_RANKING.md`
- `docs/TELEGRAM.md`
