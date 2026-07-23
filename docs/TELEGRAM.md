# تلگرام صندوقچی

## Secretهای GitHub (Repository secrets)
- `BRS_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`  ← برای **کانال** معمولاً شبیه `-100xxxxxxxxxx`

## تنظیم کانال
1. ربات را بسازید (@BotFather)
2. ربات را **ادمین کانال** کنید (حق پست)
3. `chat_id` کانال را در `TELEGRAM_CHAT_ID` بگذارید

## فرمت گزارش هوشمند (پیش‌فرض)
صبح / رنکینگ روزانه به صورت **چندپیامی** ارسال می‌شود:

1. **پیام خلاصه بازار**
   - تعداد صندوق بررسی‌شده
   - وضعیت بازار / قدرت بازار (0..100)
   - بهترین و ضعیف‌ترین گروه
   - قدرت گروه‌ها
2. **۵ پیام جدا** برای صندوق‌های برتر (با «چرا این رتبه؟»)
3. **۵ پیام جدا** برای صندوق‌های ضعیف

تنظیمات:
```
TELEGRAM_SMART_REPORT=true
TELEGRAM_TOP_N=5
TELEGRAM_WORST_N=5
```

فرمت تک‌پیامی قدیمی:
```bash
python tools/run_telegram_rank.py --no-nav --compact --dry-run
```

## Workflowها
| فایل | زمان (تقریبی تهران) | کار |
|------|----------------------|-----|
| `.github/workflows/preopen.yml` | ۸:۴۵ | پیش‌گشایش + ارسال |
| `.github/workflows/morning.yml` | ۸:۵۰ | history sync + رنکینگ هوشمند |
| `.github/workflows/daily_rank.yml` | ~۱۶:۳۰ | رنکینگ هوشمند پایان روز |

دستی از تب Actions → Run workflow هم قابل اجراست.

## CLI محلی
```bash
export BRS_API_KEY=...
export TELEGRAM_BOT_TOKEN=...
export TELEGRAM_CHAT_ID=-100...

# فقط متن (smart)
python tools/run_telegram_rank.py --no-nav --smart --dry-run
python tools/run_telegram_preopen.py --dry-run

# ارسال واقعی
python tools/run_telegram_rank.py --no-nav --smart
python tools/run_telegram_preopen.py

# ربات دستوری (long poll) — روی سرور/لوکال
python tools/run_telegram_bot.py
```

## دستورهای ربات
- `/start` `/help`
- `/rank` `/worst`
- `/preopen`
- `/fund عیار`
- `/market`

> برای پاسخ خصوصی به کاربر، کاربر باید حداقل یک‌بار به ربات `/start` بدهد.
> گزارش‌های زمان‌بندی‌شده به `TELEGRAM_CHAT_ID` (کانال) می‌روند.

## ماژول‌ها
```
services/telegram/
  client.py        # ارسال + chunk + retry
  publisher.py     # publish ranking/preopen/smart
  smart_report.py  # فرمت چندپیامی
services/telegram_bot.py   # long-poll commands
```
