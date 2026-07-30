# BoursePilot Roadmap

## Done

### v0.1–0.5 Foundation → Telegram V1 ✅
- ساختار پروژه، BRS provider، discovery، scoring factors، ranking
- پیش‌گشایش، تلگرام کانال، ربات long-poll

### v0.6 History Engine + Smart Report ✅ (Sprint 1)
- SQLite: funds / history / nav_history / market_snapshot / daily_scores / request_cache
- sync incremental + cache
- گزارش هوشمند چندپیامی تلگرام
- workflows واقعی daily/preopen/morning

---

## Sprint 2 — Indicator Engine
برای هر صندوق از سری `history`:
- EMA20 / EMA50 / EMA200
- RSI / MACD / ATR / Bollinger
- Sharpe / Sortino / Max Drawdown / Volatility
- Momentum / Liquidity series / Premium NAV series
- بازده ۱/۵/۲۰/۶۰/۹۰ روز

خروجی: `core/indicators/` + جدول یا JSON جانبی indicators

---

## Sprint 3 — Smart Ranking Engine
امتیاز چندبُعدی پایدار (نه فقط snapshot امروز):
- Trend / Money Flow / Risk / Liquidity / Volume / NAV / Technical / Historical Return / AI Confidence
- Final Score 0..100
- توضیح «چرا این رتبه؟» مبتنی بر سری زمانی

---

## Sprint 4 — Market Analyzer (۸:۵۰)
- قدرت کل بازار و گروه‌ها
- ورود/خروج پول
- پیش‌سفارش‌ها
- بیشترین حجم و نقدشوندگی

---

## Sprint 5 — Telegram Platform
دستورها:
`/today` `/top` `/worst` `/gold` `/fixed` `/stock`
`/search` `/compare` `/portfolio` `/watchlist` `/help`

---

## Sprint 6 — Portfolio
- پرتفو، هدف، ریسک، افق زمانی هر کاربر
- گزارش شخصی صبحگاهی

---

## Sprint 7 — AI Advisor
پیشنهاد تخصیص بر اساس سرمایه / ریسک / افق

---

## Sprint 8 — Realtime
اسکن دوره‌ای + هشدار ورود پول / صف خرید / شکست سطح

---

## v1.0
دستیار هوشمند سرمایه‌گذاری صندوق‌های بورس ایران — نه فقط فهرست رتبه
