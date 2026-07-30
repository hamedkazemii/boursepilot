# گزارش جامع پروژه صندوقچی — v0.7.0

**تاریخ:** 2026-07-23  
**ریپو:** https://github.com/hamedkazemii/boursepilot  
**شاخه توسعه:** `develop`  
**PR:** https://github.com/hamedkazemii/boursepilot/pull/1

---

## ۱) مسیر صحیح محصول (از این نسخه)

```
API زنده (BRS)
   ↓
ذخیره History هر صندوق (SQLite, incremental)
   ↓
Indicator Engine (بازده/EMA/RSI/Sharpe/Drawdown/...)
   ↓
Score لحظه‌ای + SmartRank نسبی (صدک بین همه صندوق‌ها)
   ↓
۵ برتر واقعی + ۵ ضعیف واقعی + توصیه روندی
   ↓
تلگرام / ربات دکمه‌ای
   ↓
پروفایل کاربر + پرتفو + واچ‌لیست
   ↓
AI Advisor (یادگیری روزانه + پاسخ سوال)
```

---

## ۲) مشکل قبلی که حل شد

| مشکل | قبل | بعد |
|------|-----|-----|
| صندوق ضعیف امتیاز بالا | snapshot ۵تایی؛ همه «نسبتاً خوب» | جهان ≥۲۰/۳۰+ و صدک نسبی |
| توضیح ضعیف = توضیح برتر | summary strength-first | `explain(kind=worst/top)` + reasons نسبی |
| توصیه فقط لحظه‌ای | change یک‌روزه | trend 20/60d + EMA/RSI/risk |
| top/worst هم‌پوشان | ممکن بود | hard disjoint + gap sanity |
| بدون کاربر/پرتفو | ❌ | users/portfolios/watchlist |
| بدون یادگیری | ❌ | ai_memory + ai_lessons |

### سنجه کیفیت اجباری
```
top5_avg - worst5_avg > 8
sane = true
```
نمونه اجرا:
- n=30
- top5_avg ≈ 69.6
- worst5_avg ≈ 30.7
- gap ≈ 38.8
- sane=True

---

## ۳) ماژول‌های جدید v0.7

### Data / History
- `core/database/schema.py` → **v2**
  - `fund_indicators`
  - `users`, `portfolios`, `portfolio_items`, `watchlist`
  - `ai_memory`, `ai_lessons`, `chat_messages`
- `core/history/*` — upsert روزانه + seed هوشمند وقتی تاریخچه کم است

### Indicators
- `core/indicators/engine.py`
  - ret 1/5/20/60/90
  - EMA20/50/200, RSI14, MACD, ATR, Bollinger
  - Volatility, Sharpe, Sortino, MaxDD
  - avg volume + volume_ratio

### Smart Ranking
- `core/ranking/smart_ranker.py`
  - ترکیب: trend, hist momentum, liquidity, money flow, risk, technical, volume, nav
  - نرمال‌سازی **percentile** روی کل جهان همان روز
  - توصیه: خرید قوی / خرید / نگهداری / کاهش / فروش

### Pipeline
- `core/pipeline/daily_analysis.py`
- CLI: `tools/run_daily_analysis.py`
- `tools/run_telegram_rank.py` روی همین پایپلاین

### User platform
- `services/portfolio/service.py`
  - ensure_user روی /start
  - risk/capital/horizon
  - portfolio add/del + watchlist

### AI
- `core/ai/advisor.py`
  - یادگیری روزانه از ranking
  - پاسخ rule-based قوی
  - اتصال اختیاری LLM رایگان با:
    - `AI_API_URL` (OpenAI-compatible)
    - `AI_API_KEY`
    - `AI_MODEL` (پیش‌فرض llama-3.1-8b-instant)

---

## ۴) دستورهای ربات

### بازار
`/today` `/top` `/worst` `/market` `/preopen` `/gold` `/fixed` `/stock` `/fund عیار`

### کاربر
`/start` (ساخت پروفایل)  
`/profile` `/risk low|medium|high` `/capital 50000000`  
`/portfolio` `/pf_add عیار 100 25000` `/pf_del عیار`  
`/watch عیار` `/watchlist`

### مشاور
`/ask ۵۰ میلیون ریسک کم یک‌ساله`  
یا متن آزاد در چت خصوصی

---

## ۵) محدودیت محیط فعلی Gumloop

- BRS از این sandbox اغلب **SSL EOF** می‌دهد.
- پایپلاین خودکار fallback می‌کند:
  1. live
  2. snapshot بزرگ
  3. demo universe + history seed
- روی **VPS/ایران/GitHub Actions** باید live شود.

برای LLM رایگان پیشنهادی:
- Groq / OpenRouter / Together (endpoint سازگار با OpenAI)
```
AI_API_URL=https://api.groq.com/openai/v1
AI_API_KEY=...
AI_MODEL=llama-3.1-8b-instant
```

---

## ۶) تست‌ها

```bash
python -m unittest \
  tests.test_smart_ranker \
  tests.test_daily_analysis \
  tests.test_portfolio_ai \
  tests.test_explain \
  tests.test_smart_report \
  tests.test_history_engine \
  tests.test_telegram \
  tests.test_score_engine -v
```
وضعیت: سبز

---

## ۷) ادامه مسیر (اولویت)

### فوری عملیاتی
1. Deploy ربات 24/7 روی VPS (`systemd` + `run_telegram_bot.py`)
2. Cron:
   - 08:50 preopen
   - 09:10 / 12:30 / 16:30 `run_daily_analysis` + telegram smart
3. اتصال AI_API_KEY رایگان
4. Merge `develop` → `main`

### محصولی بعدی
1. دریافت history واقعی چندماهه از منبع پایدار (BRS/TSETMC export)
2. حذف تدریجی seed مصنوعی وقتی bars کافی شد
3. مقایسه دو صندوق `/compare`
4. هشدار realtime ورود پول / شکست EMA
5. گزارش شخصی صبحگاهی برای هر کاربر بر اساس پرتفو

---

## ۸) جمع‌بندی یک خط

**v0.7 صندوقچی را از «لیست امتیاز لحظه‌ای» به «موتور تحلیلی نسبی+روندی با پروفایل کاربر و مشاور یادگیرنده» تبدیل کرد؛ قدم بعدی فقط داده زنده پایدار روی سرور شماست.**


---

## 9) Handoff برای ایجنت بعدی (2026-07-23)

اسناد کامل تحویل:
- `docs/AGENT_HANDOFF.md` — وضعیت موتور + مسیر + API + وب + ادمین
- `docs/PRODUCT_UI_SPEC.md` — مشخصات فشرده UI

هدف بعدی پیشنهادی: FastAPI + وب‌اپ کاربر + پنل ادمین روی همان core، بدون بازنویسی ranking.
