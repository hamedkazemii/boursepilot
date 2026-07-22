# تلگرام صندوقچی

## Secretهای GitHub (Repository secrets)
- `BRS_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`  ← برای **کانال** معمولاً شبیه `-100xxxxxxxxxx`

## تنظیم کانال
1. ربات را بسازید (@BotFather)
2. ربات را **ادمین کانال** کنید (حق پست)
3. `chat_id` کانال را در `TELEGRAM_CHAT_ID` بگذارید

## Workflowها
| فایل | زمان (تقریبی تهران) | کار |
|------|----------------------|-----|
| `.github/workflows/daily_rank.yml` | ~۱۶:۳۰ | رنکینگ + ارسال کانال |
| `.github/workflows/preopen.yml` | ۸:۴۵–۹:۰۰ | چند اسکن پیش‌سفارش + ارسال |
| `.github/workflows/morning.yml` | میراثی | به preopen وصل شده |

دستی از تب Actions → Run workflow هم قابل اجراست.

## CLI محلی
```bash
export BRS_API_KEY=...
export TELEGRAM_BOT_TOKEN=...
export TELEGRAM_CHAT_ID=-100...

# فقط متن
python tools/run_telegram_rank.py --no-nav --dry-run
python tools/run_telegram_preopen.py --dry-run

# ارسال واقعی
python tools/run_telegram_rank.py --no-nav
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
