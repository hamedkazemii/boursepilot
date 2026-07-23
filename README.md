# صندوقچی (BoursePilot)

دستیار هوشمند صندوق‌های قابل‌معامله ایران.

**نسخه:** 0.7.0

## قابلیت‌های فعلی
- داده‌ زنده BrsApi
- کشف روزانه صندوق‌ها
- امتیاز چندعاملی + رنکینگ فارسی
- **History Engine** (SQLite incremental)
- پیش‌گشایش
- گزارش **هوشمند چندپیامی** به کانال تلگرام
- توضیح جدا برای صندوق برتر/ضعیف («چرا این رتبه؟»)
- **Indicator Engine + رتبه‌بندی نسبی روندی**
- پروفایل کاربر / پرتفو / واچ‌لیست
- مشاور AI با یادگیری روزانه
- ربات دستوری + **دکمه‌های اینلاین** (`/today` `/top` `/worst` `/market` ...)

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

python -m unittest \
  tests.test_textnorm tests.test_brs_mapper tests.test_brs_provider \
  tests.test_score_engine tests.test_telegram tests.test_smart_report \
  tests.test_history_engine -v

# تاریخچه
python tools/run_history_sync.py --limit 30

# رنکینگ هوشمند (چاپ)
python tools/run_telegram_rank.py --no-nav --smart --dry-run

# رنکینگ فشرده قدیمی
python tools/run_telegram_rank.py --no-nav --compact --dry-run

python tools/run_telegram_preopen.py --dry-run
```

## ساختار کلیدی (v0.6+)
```
boursepilot/
  core/
    database/      # SQLite
    history/       # Historical Engine
    analytics/     # market summary
    indicators/    # (Sprint 2)
    scoring/
    ranking/
    pipeline/
  services/
    providers/
    telegram/      # client + publisher + smart_report
    portfolio/     # (بعدی)
  workflows/
  reports/
  tools/
  tests/
```

## مستندات
- `docs/PROJECT_PROGRESS.md` ← گزارش جامع روند و ادامه مسیر
- `docs/BRS_API.md`
- `docs/DAILY_RANKING.md`
- `docs/TELEGRAM.md`
- `docs/HISTORY_ENGINE.md`
- `ARCHITECTURE.md` / `ROADMAP.md` / `PROJECT_STATE.md`
