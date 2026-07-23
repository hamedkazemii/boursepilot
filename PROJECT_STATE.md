# صندوقچی (BoursePilot)
## Project State
Last Update: 2026-07-23
Version: 0.6.0

# وضعیت

| بخش | وضعیت |
|-----|--------|
| BRS API | ✅ |
| کشف/اسنپ‌شات/رنکینگ فارسی | ✅ |
| پیش‌گشایش CLI | ✅ |
| تلگرام ارسال به کانال | ✅ |
| گزارش هوشمند چندپیامی | ✅ |
| History Engine + SQLite | ✅ (Sprint 1) |
| جاب GitHub daily/preopen/morning | ✅ |
| ربات دستوری | ✅ (long poll) |
| Indicator Engine | ❌ Sprint 2 |
| Smart Ranking سری‌زمانی | ❌ Sprint 3 |
| Market Analyzer پیشرفته | ❌ Sprint 4 |
| دستورهای کامل ربات (/today /portfolio ...) | ❌ Sprint 5 |
| پرتفوی شخصی | ❌ Sprint 6 |
| AI Advisor | ❌ Sprint 7 |
| Realtime alerts | ❌ Sprint 8 |
| وب‌اپ / لندینگ | ❌ |

# Secrets لازم در GitHub
- BRS_API_KEY
- TELEGRAM_BOT_TOKEN
- TELEGRAM_CHAT_ID

# Env مهم محلی
```
DATABASE_PATH=data/database.db
TELEGRAM_SMART_REPORT=true
TELEGRAM_TOP_N=5
TELEGRAM_WORST_N=5
```

# فاز بعد (Sprint 2)
Indicator Engine روی سری `history`:
EMA20/50/200, RSI, MACD, ATR, Bollinger, Sharpe, Sortino, Drawdown, Volatility
