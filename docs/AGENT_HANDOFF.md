# صندوقچی (BoursePilot) — Agent Handoff Complete Spec
**Version:** 0.7.0  
**Date:** 2026-07-23  
**Repo:** https://github.com/hamedkazemii/boursepilot  
**Active branch:** `develop`  
**PR:** https://github.com/hamedkazemii/boursepilot/pull/1  
**Owner:** hamed kazemi (`hamedkazemii`)  
**Product name (FA):** صندوقچی  

> این سند برای تحویل به **هر ایجنت/توسعه‌دهنده بعدی** نوشته شده.  
> هدف: بدون تاریخچه چت، کل محصول، وضعیت فعلی، محدودیت‌ها، و مسیر ساخت **پنل ادمین + وب‌اپ** را بفهمد و اجرا کند.

---

## 0) TL;DR برای ایجنت بعدی

### محصول چیست؟
دستیار هوشمند **صندوق‌های قابل‌معامله (ETF/صندوق) بازار ایران** که:
1. داده زنده از **BrsApi** می‌گیرد  
2. تاریخچه را در **SQLite** نگه می‌دارد  
3. اندیکاتور و رتبه‌بندی **نسبی + روندی** می‌سازد  
4. Top/Worst واقعی + توضیح «چرا این رتبه؟» می‌دهد  
5. از طریق **تلگرام** (کانال + ربات دکمه‌ای) منتشر می‌کند  
6. پروفایل/پرتفو/واچ‌لیست کاربر دارد  
7. مشاور AI (rule-based + LLM اختیاری) دارد  

### مسیر صحیح داده (اجباری — منحرف نشو)
```
BRS live API
  → History Engine (SQLite incremental)
  → Indicator Engine
  → Smart relative ranking (percentile across universe)
  → Top/Worst + trend recommendation + role-aware explain
  → Telegram channel/bot + (NEXT) Web App + Admin Panel
  → User profile / portfolio
  → AI Advisor (daily learning)
```

### وضعیت فعلی
| لایه | وضعیت |
|------|--------|
| BRS provider + DTO | ✅ |
| History SQLite v2 | ✅ |
| Indicators | ✅ |
| SmartRanker + quality gate | ✅ |
| DailyAnalysisPipeline | ✅ |
| Telegram smart report + bot | ✅ |
| User/portfolio/AI memory | ✅ |
| **Web App کاربر** | ❌ باید ساخته شود |
| **Admin Panel مدیریت محصول** | ❌ باید ساخته شود |
| Realtime alerts | ❌ |
| `/compare` کامل | ❌ |
| Deploy 24/7 پایدار | ⚠️ نیمه‌کاره (نیاز VPS) |

### قانون طلایی محصول
- **رتبه‌بندی لحظه‌ای snapshot کوچک = گمراه‌کننده** → ممنوع به‌عنوان منبع حقیقت  
- **Top و Worst باید واقعاً جدا** باشند (`top5_avg - worst5_avg > 8`, ideally ~30+)  
- توضیح صندوق ضعیف ≠ توضیح صندوق برتر  
- هیچ secret در کد hardcode نشود  
- تحلیل فقط روی DTO داخلی (`SymbolQuote` / `NavData`) نه JSON خام BRS  

---

## 1) چشم‌انداز محصول

### مشکل کاربر
سرمایه‌گذار خرد ایرانی برای انتخاب صندوق ETF:
- با ده‌ها/صدها نماد روبه‌روست  
- نمی‌داند روند واقعی چیست (فقط سبز/قرمز امروز)  
- توضیح شفاف «چرا بخرم/نفروشم» ندارد  
- پرتفو و ریسک شخصی‌سازی‌شده ندارد  

### ارزش پیشنهادی صندوقچی
«هر روز، با داده واقعی + تاریخچه + رتبه نسبی، بگو کدام صندوق‌ها واقعاً بهتر/بدترند، چرا، و با ریسک من چه کنم.»

### کاربران هدف
1. **کاربر نهایی** — تلگرام + وب‌اپ ساده  
2. **ادمین/صاحب محصول** — پنل مدیریت، مانیتور داده، انتشار، تنظیم وزن‌ها  
3. **ایجنت/اتوماسیون** — CLI + API داخلی  

### کانال‌های تحویل
| کانال | نقش |
|-------|-----|
| تلگرام کانال | گزارش صبح/روزانه عمومی |
| تلگرام ربات | تعامل شخصی + پرتفو + ask |
| وب‌اپ | داشبورد مدرن، جستجو، جزئیات صندوق، پرتفو |
| پنل ادمین | کنترل محصول، کیفیت داده، انتشار، کاربران، تنظیمات |

---

## 2) Git / محیط / Secrets

### ریپو
- GitHub: `hamedkazemii/boursepilot`
- Branch کاری: **`develop`**
- PR باز: #1 → بعداً merge به `main`
- Version file: `VERSION` = `0.7.0`

### Secrets / Env (هرگز در git نگذار)
```bash
# الزامی برای live
BRS_API_KEY=
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=          # کانال معمولاً -100...

# دیتابیس
DATABASE_PATH=data/database.db

# اختیاری AI
AI_API_URL=https://api.groq.com/openai/v1
AI_API_KEY=
AI_MODEL=llama-3.1-8b-instant

# BRS
BRS_BASE_URL=https://Api.BrsApi.ir/Tsetmc
BRS_USER_AGENT=Mozilla/5.0 ...
BRS_TIMEOUT_SECONDS=30
BRS_ALL_SYMBOLS_TYPE=1
MARKET_DATA_PROVIDER=brs

# گزارش
TELEGRAM_SMART_REPORT=true
TELEGRAM_TOP_N=5
TELEGRAM_WORST_N=5
SNAPSHOT_DIR=data/snapshots
SCORING_CONFIG_PATH=config/scoring.yaml
FETCH_NAV_IN_DAILY_RANK=false

# وب/ادمین (پیشنهادی برای فاز بعد — هنوز در config کامل نیست)
WEB_HOST=0.0.0.0
WEB_PORT=8080
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=
JWT_SECRET=
CORS_ORIGINS=*
```

فایل نمونه: `.env.example`  
لودر: `config.py` → `settings = Settings()`

### وابستگی‌ها (`requirements.txt` فعلی)
```
requests
pandas
openpyxl
python-dotenv
PyYAML
```
برای وب/ادمین باید اضافه شود (پیشنهاد):
```
fastapi
uvicorn[standard]
jinja2
python-multipart
passlib[bcrypt]
PyJWT
httpx
```

### محدودیت محیط
- در بعضی sandboxها (مثل Gumloop) **BRS SSL EOF** می‌دهد  
- Pipeline خودکار fallback دارد: `live → snapshot بزرگ → demo+seed history`  
- روی **VPS/ایران/GitHub Actions** مسیر live اولویت دارد  
- ربات long-poll نیاز به پروسه 24/7 دارد (`tools/run_telegram_bot.py`)

---

## 3) معماری فعلی (کد واقعی)

### Data flow v0.7
```
BRS API (AllSymbols / Symbol / Nav)
        │
        ▼
  services/providers/brs_*  → DTO SymbolQuote / NavData
        │
        ├──────────────► HistoryEngine ──► SQLite
        │
        ▼
  FundCatalog / SnapshotStore (JSON)
        │
        ▼
  ScoreEngine (factors) + IndicatorEngine (series)
        │
        ▼
  SmartRanker (percentile + trend recommend)
        │
        ├─► daily_scores / fund_indicators (SQLite)
        ├─► reports/daily_ranking.{json,txt}
        ▼
  Analytics explain + MarketSummary
        │
        ▼
  Telegram smart_report + SandoghchiBot
        │
        ▼
  PortfolioService + AIAdvisor
```

### درخت پکیج‌های مهم
```
boursepilot/
  config.py                 # Settings از env
  config/scoring.yaml       # وزن فاکتورها و آستانه‌ها
  app.py / ranking_app.py   # entry قدیمی/ساده
  core/
    database/               # connection + schema v2
    history/                # engine + repository
    indicators/             # IndicatorEngine
    scoring/                # ScoreEngine + models + weights
    factors/                # liquidity, orderbook, money_flow, momentum, volume, nav
    ranking/                # fund_ranker + smart_ranker
    pipeline/               # daily_rank + daily_analysis
    analytics/              # explain + market_summary
    ai/advisor.py           # AIAdvisor
    preopen/                # پیش‌گشایش
    classification/         # نوع صندوق
  services/
    providers/              # BRS client/mapper/provider/factory
    discovery/              # FundCatalog
    snapshot/               # JSON snapshots
    portfolio/service.py
    telegram/               # client, keyboards, publisher, smart_report
    telegram_bot.py         # SandoghchiBot
  tools/                    # CLI entrypoints
  reports/                  # خروجی متنی/JSON
  tests/
  docs/
  .github/workflows/        # preopen, morning, daily_rank
```

### جداول SQLite (schema v2)
| جدول | نقش |
|------|-----|
| `schema_meta` | نسخه schema |
| `funds` | شناسنامه صندوق |
| `history` | OHLC، حجم، ارزش، orderbook، حقیقی/حقوقی |
| `nav_history` | NAV و premium/discount |
| `market_snapshot` | خلاصه بازار هر اجرا |
| `daily_scores` | امتیاز و رتبه روزانه |
| `fund_indicators` | خروجی IndicatorEngine |
| `request_cache` | کش درخواست‌های تکراری |
| `users` | پروفایل تلگرام/کاربر |
| `portfolios` / `portfolio_items` | پرتفو |
| `watchlist` | واچ‌لیست |
| `ai_memory` / `ai_lessons` | حافظه و درس روزانه AI |
| `chat_messages` | تاریخچه گفتگو |

اعمال schema: `core/database/schema.py` → `apply_schema(conn)`  
مسیر DB پیش‌فرض: `data/database.db` (gitignore)

---

## 4) ماژول‌به‌ماژول (API ذهنی برای ایجنت)

### 4.1 Market data
```python
from services.providers import get_market_data_provider
provider = get_market_data_provider()  # brs
funds = provider.get_fund_symbols()
quote = provider.get_symbol("عیار")
nav = provider.get_nav("عیار")
```
- HTTP: `services/providers/brs_client.py`
- raw→DTO: `brs_mapper.py` + `textnorm.py` (یکسان‌سازی ی/ک)
- Docs: `docs/BRS_API.md`

### 4.2 History
```python
from core.history import HistoryEngine
engine = HistoryEngine()
engine.sync_daily()
series = engine.get_series("عیار", limit=120)
engine.stats()
```
CLI: `python tools/run_history_sync.py --limit 30`

### 4.3 Indicators
`core/indicators/engine.py` → `IndicatorEngine.compute(series)`  
خروجی نمونه: ret_1/5/20/60/90، EMA20/50/200، RSI14، MACD، ATR، Bollinger، Vol، Sharpe، Sortino، MaxDD، volume_ratio

### 4.4 Scoring (لحظه‌ای چندعاملی)
`ScoreEngine.assess(quote, nav=...)`  
فاکتورها و وزن‌ها از `config/scoring.yaml`:
- liquidity 0.18
- orderbook_pressure 0.20
- money_flow 0.18
- momentum 0.16
- volume_value 0.14
- nav_premium 0.14

### 4.5 Smart ranking (منبع حقیقت رتبه‌بندی)
`core/ranking/smart_ranker.py` → `SmartRanker.rank(assessments, indicators_by_symbol)`
- نرمال‌سازی **percentile روی کل جهان همان روز**
- اجزا: trend, hist momentum, liquidity, money flow, risk, technical, volume, nav
- توصیه: خرید قوی / خرید / نگهداری / کاهش / فروش
- reasons نقش‌محور

**Quality gate (اجباری در pipeline):**
```
top5_avg - worst5_avg > 8
sane == true
```
نمونه سالم v0.7: universe≈30، top≈70، worst≈31، gap≈39

### 4.6 Daily pipeline
`core/pipeline/daily_analysis.py` → `DailyAnalysisPipeline.run()`
```
live/snapshot/demo → history upsert → indicators → smart rank → persist → validate
```
CLI:
```bash
python tools/run_daily_analysis.py
python tools/run_telegram_rank.py --smart --dry-run
python tools/run_telegram_rank.py --smart
```

### 4.7 Explain
`core/analytics/explain.py` → `explain_fund(assessment, kind="top"|"worst")`  
ضعیف = ضعف/ریسک؛ برتر = قوت/جریان پول

### 4.8 Telegram
- Smart multi-message: `services/telegram/smart_report.py`
- Keyboards: `services/telegram/keyboards.py`
- Bot: `services/telegram_bot.py` → `SandoghchiBot`
- Run: `python tools/run_telegram_bot.py`

#### دستورات ربات
**بازار:**  
`/today` `/top` `/worst` `/market` `/preopen` `/gold` `/fixed` `/stock` `/fund عیار`

**کاربر:**  
`/start` (ساخت پروفایل)  
`/profile` `/risk low|medium|high` `/capital 50000000`  
`/portfolio` `/pf_add عیار 100 25000` `/pf_del عیار`  
`/watch عیار` `/watchlist`

**مشاور:**  
`/ask ۵۰ میلیون ریسک کم یک‌ساله`  
یا متن آزاد در چت خصوصی

### 4.9 Portfolio + AI
```python
from services.portfolio.service import PortfolioService
from core.ai.advisor import AIAdvisor
ps = PortfolioService()
ps.ensure_user(telegram_id=..., username=...)
ai = AIAdvisor()
ai.learn_from_ranking(ranked)
ai.answer(user_id, "۵۰ میلیون ریسک کم")
```

---

## 5) تست و کیفیت

حداقل تست‌های سبز قبل از هر PR:
```bash
python -m unittest \
  tests.test_smart_ranker \
  tests.test_daily_analysis \
  tests.test_portfolio_ai \
  tests.test_explain \
  tests.test_smart_report \
  tests.test_history_engine \
  tests.test_telegram \
  tests.test_score_engine \
  tests.test_brs_mapper \
  tests.test_textnorm -v
```

قوانین PR:
1. روی `develop` کار کن  
2. تست + dry-run  
3. secret commit نکن  
4. اگر ranking تغییر کرد، gap sanity را گزارش بده  

---

## 6) Workflowهای زمان‌بندی‌شده

| فایل | زمان تقریبی تهران | کار |
|------|-------------------|-----|
| `.github/workflows/preopen.yml` | 08:45 | پیش‌گشایش + ارسال |
| `.github/workflows/morning.yml` | 08:50 | history sync + ranking هوشمند |
| `.github/workflows/daily_rank.yml` | ~16:30 | ranking پایان روز |

CLI محلی متناظر:
- `tools/run_telegram_preopen.py`
- `tools/run_history_sync.py`
- `tools/run_daily_analysis.py` / `run_telegram_rank.py`

---

## 7) مشکلات حل‌شده (نکن دوباره)

| باگ/مسیر غلط | راه‌حل فعلی |
|--------------|-------------|
| snapshot کوچک → همه «خوب» | جهان بزرگ + percentile |
| top≈worst | SmartRanker + gate |
| explain ضعیف = explain برتر | `explain(kind=...)` |
| توصیه فقط change یک‌روزه | trend 20/60 + EMA/RSI/risk |
| بدون کاربر | users/portfolio/watchlist |
| بدون یادگیری | ai_memory + ai_lessons |
| SSL BRS در sandbox | fallback snapshot/demo+seed |

---

## 8) بدهی فنی / نقاط حساس

1. **دو لایه ranking قدیمی و جدید:** `ScoreEngine`/`FundRanker` هنوز هست؛ منبع حقیقت نمایش باید `SmartRanker` + `DailyAnalysisPipeline` باشد.  
2. **فایل‌های legacy:** `core/ranking.py`, `core/scoring.py`, `core/indicators.py` (مسطح) در کنار پکیج‌های جدید — گیج‌کننده؛ به‌مرور deprecate.  
3. **History واقعی چندماهه** هنوز کامل از منبع پایدار backfill نشده؛ seed مصنوعی فقط برای bootstrap.  
4. **Web/Admin وجود ندارد.**  
5. **Auth وب** تعریف نشده.  
6. **API HTTP عمومی** وجود ندارد — فقط CLI/ماژول پایتون.  
7. `ROADMAP.md` کمی عقب‌تر از واقعیت v0.7 است؛ `PROJECT_STATE.md` و این handoff مرجع‌ترند.

---

## 9) مسیر پیش‌رو (اولویت‌بندی اجرایی)

### P0 — پایدارسازی عملیات (۱–۲ روز)
1. VPS + systemd برای `run_telegram_bot.py`  
2. Cron:
   - 08:50 preopen  
   - 09:10 / 12:30 / 16:30 daily_analysis + telegram smart  
3. اتصال `AI_API_KEY` رایگان (Groq/OpenRouter)  
4. مانیتور: اگر `sane=false` → آلرت ادمین  
5. Merge `develop` → `main` بعد از smoke live

### P1 — Backend API برای وب و ادمین (۲–۴ روز)
ساخت `api/` با FastAPI روی همان core (بدون بازنویسی موتور):
- Read models از SQLite + آخرین `reports/daily_ranking.json`
- Write محدود برای ادمین (weights, publish, users flags)

### P2 — وب‌اپ کاربر (۳–۵ روز)
SPA یا SSR ساده، RTL، مدرن، موبایل‌اول

### P3 — پنل ادمین (۳–۵ روز)
مدیریت محصول، کیفیت، انتشار، تنظیمات

### P4 — محصول پیشرفته
- `/compare` و صفحه مقایسه  
- Realtime alerts (پول، شکست EMA، ورود به top/worst)  
- گزارش صبحگاهی شخصی‌سازی‌شده  
- Backfill history چندماهه واقعی  
- اعلان push وب  

---

# 10) مشخصات کامل Backend API (برای وب + ادمین)

> پیشنهاد مسیر کد: `api/main.py`, `api/deps.py`, `api/routers/*`, `api/auth.py`  
> موتور تحلیل را جابه‌جا نکن؛ فقط façade بساز.

## 10.1 اصول API
- Base: `/api/v1`
- JSON UTF-8
- زمان‌ها ISO-8601
- خطا: `{ "error": { "code": "...", "message": "..." } }`
- Pagination: `?limit=50&offset=0`
- زبان پیام‌های UI: فارسی (فیلدهای `label_fa`)
- Auth:
  - Public read: ranking روز، جزئیات صندوق (محدود)
  - User: JWT یا Telegram Login Widget
  - Admin: JWT جدا + role=admin

## 10.2 Public / User endpoints

### Market & Ranking
| Method | Path | توضیح |
|--------|------|--------|
| GET | `/health` | status, db_ok, last_analysis_at, sane, source(live/snapshot/demo) |
| GET | `/market/summary` | قدرت بازار، تعداد صندوق، best/worst group، gap |
| GET | `/ranking/today` | لیست رتبه‌بندی کامل یا top |
| GET | `/ranking/top?limit=10` | برترین‌ها |
| GET | `/ranking/worst?limit=10` | ضعیف‌ترین‌ها |
| GET | `/ranking/by-type/{gold\|stock\|fixed}` | فیلتر نوعی |
| GET | `/funds` | جستجو `?q=&type=&limit=` |
| GET | `/funds/{symbol}` | کارت کامل + score + recommend + reasons |
| GET | `/funds/{symbol}/history?days=120` | سری قیمت/حجم |
| GET | `/funds/{symbol}/indicators` | آخرین اندیکاتورها |
| GET | `/funds/compare?symbols=عیار,آگاس` | مقایسه چند نماد |
| GET | `/preopen` | خروجی پیش‌گشایش |

### User (auth required)
| Method | Path | توضیح |
|--------|------|--------|
| POST | `/auth/telegram` | login با داده Telegram Widget |
| GET | `/me` | پروفایل |
| PATCH | `/me` | risk_profile, capital, horizon_months |
| GET | `/me/portfolio` | موجودی + ارزش تقریبی |
| POST | `/me/portfolio/items` | `{symbol, units, avg_price}` |
| DELETE | `/me/portfolio/items/{symbol}` | حذف |
| GET | `/me/watchlist` | لیست |
| POST | `/me/watchlist` | `{symbol}` |
| DELETE | `/me/watchlist/{symbol}` | |
| POST | `/me/ask` | `{message}` → پاسخ AIAdvisor |
| GET | `/me/chat` | تاریخچه |

### Response shape نمونه — FundCard
```json
{
  "symbol": "عیار",
  "name": "صندوق ...",
  "fund_type": "gold",
  "rank": 3,
  "score": 71.2,
  "label": "خرید",
  "recommendation": "buy",
  "change_pct": 1.2,
  "last_price": 25400,
  "nav_premium_pct": -0.4,
  "reasons": ["روند ۲۰روزه مثبت", "نقدشوندگی بالا"],
  "explain_fa": "چرا این رتبه؟ ...",
  "indicators": {"rsi14": 58.1, "ret_20": 4.2, "sharpe": 1.1, "max_dd": -6.3},
  "as_of": "2026-07-23T12:30:00+03:30",
  "source": "live"
}
```

## 10.3 Admin endpoints (role=admin)

| Method | Path | توضیح |
|--------|------|--------|
| POST | `/admin/auth/login` | user/pass → JWT |
| GET | `/admin/overview` | KPI محصول |
| GET | `/admin/pipeline/runs` | تاریخچه اجراها (از logs/db) |
| POST | `/admin/pipeline/run` | `{mode: analysis\|preopen\|history_sync\|telegram_publish}` |
| GET | `/admin/pipeline/status` | در حال اجرا؟ آخرین نتیجه؟ sane؟ |
| GET | `/admin/data/quality` | coverage history، missing NAV، stale symbols |
| GET | `/admin/ranking/preview` | پیش‌نمایش قبل انتشار |
| POST | `/admin/telegram/publish` | `{type: smart_rank\|preopen\|custom, dry_run?}` |
| POST | `/admin/telegram/broadcast` | پیام دستی به کانال |
| GET | `/admin/config/scoring` | خواندن weights |
| PUT | `/admin/config/scoring` | به‌روزرسانی scoring.yaml (+ backup) |
| GET | `/admin/users` | لیست کاربران |
| GET | `/admin/users/{id}` | جزئیات + پرتفو |
| PATCH | `/admin/users/{id}` | ban/notes/flags |
| GET | `/admin/ai/lessons` | درس‌های یادگرفته |
| POST | `/admin/ai/lessons` | درس دستی |
| GET | `/admin/logs?tail=200` | لاگ‌های اخیر |
| GET | `/admin/system/env-status` | کدام env ست است (بدون افشای مقدار secret) |

### Admin overview KPI پیشنهادی
```json
{
  "universe_size": 312,
  "last_run_at": "...",
  "source": "live",
  "sane": true,
  "gap": 38.8,
  "top5_avg": 69.6,
  "worst5_avg": 30.7,
  "users_count": 120,
  "active_portfolios": 45,
  "telegram_last_publish_at": "...",
  "db_size_mb": 42.5,
  "history_coverage_days_p50": 18
}
```

---

# 11) مشخصات وب‌اپ کاربر (User Web App)

## 11.1 هدف
وب‌اپ **ساده، سریع، RTL، مدرن، موبایل‌اول** که همان ارزش تلگرام را با UI غنی‌تر بدهد:
- ببینم امروز بازار صندوق‌ها چطور است  
- Top/Worst و دلیل  
- جزئیات یک صندوق + نمودار  
- پرتفو و واچ‌لیست من  
- بپرس از مشاور  

نام محصول در UI: **صندوقچی**  
زبان: فارسی  
جهت: RTL  

## 11.2 استک پیشنهادی (ساده و کاربردی)
**گزینه A (پیشنهادی برای سرعت):**
- Backend: FastAPI (همان API بالا)
- Frontend: **HTML + Tailwind + Alpine/Vanilla** یا **Next.js RTL**  
- نمودار: lightweight-charts یا Chart.js  
- PWA اختیاری  

**گزینه B:** React/Vite + Tailwind + React Query  

> اگر ایجنت داخل Gumloop artifact می‌سازد: HTML چندفایلی scaffold + API proxy.  
> اگر روی VPS: FastAPI serve کند `web/` static یا SSR.

## 11.3 اصول UI/UX (اجباری)
- نه بنفش گرادیانی کلیشه‌ای AI  
- پالت پیشنهادی:
  - bg: `#0B1220` (dark) / `#F7F8FA` (light)
  - surface: `#111827` / `#FFFFFF`
  - primary: `#0E7C66` (سبز مالی ملایم)
  - danger: `#C23B3B`
  - warning: `#C2811A`
  - text: high-contrast
- فونت فارسی: Vazirmatn / IRANYekan / system-ui
- شعاع گوشه 12–16px، سایه خیلی ملایم
- کارت‌ها واضح، فاصله تنفس‌دار
- Skeleton loading
- Empty state فارسی دوستانه
- همه اعداد با جداکننده هزارگان فارسی/لاتین یکدست
- رنگ سبز/قرمز فقط برای perf نه کل UI
- Dark mode پیش‌فرض (با toggle)

## 11.4 نقشه صفحات

### A) `/` خانه (Dashboard)
بخش‌ها:
1. **هدر وضعیت بازار**  
   - تاریخ به‌روزرسانی  
   - منبع داده (live/snapshot)  
   - قدرت بازار 0..100  
   - chip: `sane` / فاصله top-worst  
2. **اقدام سریع:** جستجو، پرتفو، مشاور  
3. **۵ برتر** (کارت افقی اسکرول موبایل / گرید دسکتاپ)  
4. **۵ ضعیف**  
5. **خلاصه گروهی** طلا / سهامی / درآمد ثابت  
6. **نکته روز AI** (از ai_lessons)

### B) `/ranking`
- تب: همه | طلا | سهامی | ثابت  
- سوییچ: برتر / ضعیف / همه  
- جدول+کارت ریسپانسیو: رتبه، نماد، امتیاز، تغییر، توصیه، نقدشوندگی  
- فیلتر score/recommend  
- دکمه «جزئیات»

### C) `/funds/[symbol]`
- هدر: نماد، نام، نوع، rank/score، recommendation badge  
- قیمت، تغییر، حجم، premium NAV  
- **چرا این رتبه؟** (explain_fa + reasons chips)  
- تب نمودار: قیمت ۱M/۳M، volume  
- تب اندیکاتور: RSI/EMA/Sharpe/MaxDD  
- CTA: افزودن به واچ / پرتفو  
- صندوق‌های مشابه (همان type نزدیک امتیاز)

### D) `/compare`
- تا ۴ نماد  
- جدول متریک‌ها + sparkline  

### E) `/portfolio`
- خلاصه ارزش، سود/زیان تقریبی (اگر قیمت موجود)  
- لیست holdings  
- افزودن سریع  
- پیشنهاد بازتنظیم از AI (risk-based)

### F) `/watchlist`
- لیست + rank/score live  
- سوییچ هشدار (فاز بعد)

### G) `/advisor`
- چت ساده  
- suggestion chips: «۵۰ میلیون ریسک کم»، «فقط طلا»، «درآمد ثابت یک‌ساله»  
- نمایش allocation پیشنهادی به‌صورت کارت درصدی  

### H) `/profile`
- ریسک، سرمایه، افق  
- اتصال تلگرام  

### I) `/login`
- Telegram Login Widget (اولویت)  
- یا کد یک‌بارمصرف بعدی  

## 11.5 کامپوننت‌های UI مشترک
- `AppShell` (nav پایین موبایل + ساید دسکتاپ)
- `FundCard`
- `ScoreBadge` (0–100 رنگی)
- `RecommendChip`
- `ReasonList`
- `MarketHero`
- `Sparkline`
- `SearchBox` (نماد/نام)
- `EmptyState`
- `DataSourcePill` (live/snapshot/demo)
- `SaneGapIndicator`

## 11.6 ناوبری موبایل (پایین)
خانه | رتبه‌بندی | پرتفو | مشاور | بیشتر

## 11.7 حالت‌های داده
| state | UI |
|-------|----|
| loading | skeleton |
| live ok | pill سبز «زنده» |
| snapshot | pill زرد «آخرین ذخیره» |
| demo | pill نارنجی «نمونه» + توضیح |
| sane=false | بنر هشدار: کیفیت رتبه پایین است |
| error | retry |

## 11.8 دسترسی‌پذیری و کیفیت
- کنتراست AA  
- دکمه‌ها min 44px  
- پشتیبانی کیبورد  
- صفحات < 200ms بعد از cache API  
- SEO ساده فقط برای صفحات عمومی صندوق  

## 11.9 خروجی MVP وب‌اپ (Definition of Done)
- [ ] خانه با top/worst واقعی از API  
- [ ] صفحه صندوق + explain  
- [ ] ranking فیلتر نوع  
- [ ] login تلگرام یا dev-login  
- [ ] پرتفو CRUD  
- [ ] ask مشاور  
- [ ] ریسپانسیو 375px و 1280px  
- [ ] dark mode  
- [ ] نشان‌دادن source و as_of  

---

# 12) مشخصات پنل مدیریت محصول (Admin Panel)

## 12.1 هدف
پنل برای **صاحب محصول** تا بدون SSH:
- سلامت داده و pipeline را ببیند  
- ranking را قبل از انتشار بررسی کند  
- به تلگرام publish کند  
- وزن امتیازدهی را تنظیم کند  
- کاربران/پرتفو را ببیند  
- کیفیت محصول (gap/sane/coverage) را مانیتور کند  

مخاطب: ۱–۳ ادمین (نه کاربر عادی)  
زبان: فارسی RTL  
استایل: denser از وب‌اپ؛ بیشتر جدول/KPI تا مارکتینگ

## 12.2 دسترسی
- URL: `/admin` (جدا از وب‌اپ یا subdomain `admin.`)
- Login password + JWT  
- Session timeout  
- Audit log برای publish و تغییر weights  
- 2FA فاز بعد  

## 12.3 نقشه صفحات ادمین

### 1) Overview `/admin`
KPI cards:
- آخرین اجرا + duration  
- source: live/snapshot/demo  
- universe size  
- sane + gap + top5/worst5 avg  
- users / portfolios  
- آخرین publish تلگرام  
- خطاهای ۲۴ساعته  

Charts:
- gap روزانه ۷ روز  
- تعداد صندوق تحلیل‌شده  
- نسبت source  

CTA:
- اجرای تحلیل الآن  
- انتشار گزارش الآن  
- مشاهده کیفیت داده  

### 2) Pipeline `/admin/pipeline`
- دکمه‌های Run:
  - History Sync  
  - Daily Analysis  
  - Preopen  
  - Telegram Publish (smart)  
- جدول run history: time, type, status, source, sane, gap, n_funds, error  
- لاگ زنده/آخرین لاگ  
- dry-run toggle  

### 3) Ranking QA `/admin/ranking`
- پیش‌نمایش top/worst  
- بررسی explain ضعیف‌ها (نباید شبیه برتر باشد)  
- فیلتر type  
- دکمه Approve & Publish  
- نمایش quality gate pass/fail  
- مقایسه با دیروز (اختیاری)

### 4) Data Quality `/admin/data`
- coverage: چند روز history per fund (p50/p90)  
- نمادهای stale  
- NAV missing rate  
- cache hit  
- DB size  
- دکمه purge cache  
- دکمه re-seed ممنوع در production مگر confirm  

### 5) Funds catalog `/admin/funds`
- جدول همه صندوق‌ها  
- type classification override  
- active/inactive  
- search  

### 6) Scoring config `/admin/scoring`
- ادیتور وزن‌ها (sum≈1 validation)  
- آستانه‌های recommendation  
- preview روی آخرین snapshot بدون publish  
- versioning/backup فایل yaml  
- دکمه reset to default  

### 7) Telegram `/admin/telegram`
- وضعیت bot/token/chat (masked)  
- آخرین پیام‌ها  
- publish smart/compact/preopen  
- ارسال پیام دستی Markdown  
- تست dry-run  

### 8) Users `/admin/users`
- لیست کاربران تلگرام/وب  
- risk/capital  
- تعداد holdings  
- ban/suspend  
- impersonate read-only (اختیاری)

### 9) AI `/admin/ai`
- lessons اخیر  
- memory keys  
- تست `/ask` با کاربر نمونه  
- وضعیت LLM env  

### 10) System `/admin/system`
- env flags present?  
- versions (app, schema)  
- disk  
- toggle maintenance mode  
- link to docs/handoff  

## 12.4 کامپوننت‌های ادمین
- `KpiStat`
- `RunButton` + confirm modal
- `LogViewer`
- `GateBadge` (sane/gap)
- `WeightsEditor`
- `FundMiniTable`
- `PublishWizard` (preview → confirm → result)

## 12.5 قواعد ایمنی ادمین
1. Publish واقعی نیاز به confirm دو مرحله‌ای  
2. تغییر weights بدون backup ممنوع  
3. هیچ secret خام در UI  
4. همه actionها audit: who/when/what  
5. Runهای سنگین queue تکی (lock) تا هم‌زمانی dup نشود  
6. اگر `sane=false`، Publish هشدار قرمز بدهد (force فقط با type عبارت CONFIRM)

## 12.6 MVP ادمین — DoD
- [ ] login امن  
- [ ] overview KPI واقعی از DB/reports  
- [ ] run daily analysis از UI  
- [ ] preview ranking + gate  
- [ ] publish telegram با dry-run  
- [ ] مشاهده users  
- [ ] ویرایش weights با validation  
- [ ] log آخرین اجرا  

---

# 13) مدل دامنه برای UI (Shared Types)

```ts
type DataSource = "live" | "snapshot" | "demo" | "offline";

type Recommend = "strong_buy" | "buy" | "hold" | "reduce" | "sell" | "neutral" | "weak";

interface MarketSummary {
  as_of: string;
  source: DataSource;
  universe_size: number;
  market_power: number; // 0..100
  top5_avg: number;
  worst5_avg: number;
  gap: number;
  sane: boolean;
  best_group?: string;
  worst_group?: string;
}

interface FundCard {
  symbol: string;
  name?: string;
  fund_type?: "gold" | "stock" | "fixed" | "other" | string;
  rank?: number;
  score: number;
  recommendation: Recommend;
  label_fa: string;
  change_pct?: number;
  last_price?: number;
  tval?: number;
  nav_premium_pct?: number;
  reasons: string[];
  explain_fa?: string;
}

interface UserProfile {
  id: number;
  telegram_id?: string;
  display_name?: string;
  risk_profile: "low" | "medium" | "high";
  capital?: number;
  horizon_months?: number;
}
```

---

## 14) پیشنهاد ساختار کد فاز وب/ادمین

```
boursepilot/
  api/
    main.py
    deps.py
    auth.py
    schemas.py
    routers/
      health.py
      market.py
      ranking.py
      funds.py
      me.py
      admin_pipeline.py
      admin_config.py
      admin_users.py
      admin_telegram.py
  web/                 # user app static or frontend project
    index.html
    ...
  admin_ui/            # admin frontend
    index.html
    ...
  core/                # دست نزن مگر bugfix موتور
  services/
  tools/
    run_api.py         # uvicorn launcher
```

`tools/run_api.py`:
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8080
```

---

## 15) سناریوهای پذیرش end-to-end

1. **صبح بازار:** cron analysis → sane=true → publish کانال → وب خانه همان top را نشان دهد  
2. **کاربر جدید:** Telegram login → set risk low → ask «۳۰ میلیون یک‌ساله» → allocation محافظه‌کار  
3. **ادمین:** weights را کمی تغییر دهد → preview → publish نکند تا confirm  
4. **BRS down:** source=snapshot/demo → UI pill هشدار → ربات نخوابد  
5. **کیفیت بد:** gap<8 → admin banner + block publish پیش‌فرض  

---

## 16) دستورات روزمره برای ایجنت/اپراتور

```bash
# نصب
pip install -r requirements.txt
cp .env.example .env  # پر کردن secrets

# تست موتور
python -m unittest tests.test_smart_ranker tests.test_daily_analysis tests.test_portfolio_ai -v

# تحلیل
python tools/run_daily_analysis.py

# تلگرام dry-run / real
python tools/run_telegram_rank.py --smart --dry-run
python tools/run_telegram_rank.py --smart

# ربات
python tools/run_telegram_bot.py

# history
python tools/run_history_sync.py --limit 50
```

---

## 17) لحن و قوانین پاسخ محصول

- فارسی روان، دقیق، غیرگمراه‌کننده  
- هرگز وعده سود قطعی نده  
- توصیه = تحلیلی/آموزشی نه سیگنال تضمینی  
- وقتی داده demo/snapshot است شفاف بگو  
- برای صندوق ضعیف از ادبیات ضعف/ریسک استفاده کن  

متن حقوقی کوتاه پیشنهادی در فوتر وب و /start:
> «صندوقچی ابزار تحلیلی است و توصیه مالی قطعی یا سبدگردانی رسمی محسوب نمی‌شود.»

---

## 18) چک‌لیست شروع کار ایجنت بعدی (اولین جلسه)

1. Clone/`develop` pull  
2. خواندن: این فایل + `PROJECT_STATE.md` + `docs/PROJECT_PROGRESS.md`  
3. اجرای تست‌های هسته  
4. یک `run_daily_analysis` و بررسی `sane/gap`  
5. تصمیم: P0 ops یا P1 API؟ (اگر هدف UI است → API اول)  
6. پیاده‌سازی FastAPI read-only ranking  
7. اسکلت وب‌اپ خانه + ranking  
8. اسکلت ادمین overview + run analysis  
9. اتصال publish تلگرام به ادمین  
10. تست E2E با dry-run  

---

## 19) چیزهایی که نباید انجام دهی

- بازنویسی کامل موتور ranking بدون دلیل  
- تکیه به snapshot ۵تایی به‌عنوان truth  
- hardcode نماد/امتیاز/کلید  
- یکی‌کردن متن top و worst  
- افزودن UI بدون quality gate  
- commit کردن `data/database.db` یا `.env`  
- ساخت microservice پیچیده در MVP  

---

## 20) خلاصه تصمیم محصول برای UI

| سطح | ابزار | تمرکز |
|-----|-------|-------|
| کاربر عادی روزمره | تلگرام + وب‌اپ | سادگی، سرعت، توضیح، پرتفو |
| صاحب محصول | پنل ادمین | کنترل کیفیت، انتشار، تنظیم مدل |
| هسته هوشمند | Python core فعلی | history→indicator→smart rank→AI |

**وب‌اپ نباید موتور جدا داشته باشد.**  
فقط همان `DailyAnalysisPipeline` / SQLite / reports را نمایش دهد.

---

## 21) مراجع داخل ریپو

| فایل | محتوا |
|------|--------|
| `docs/AGENT_HANDOFF.md` | همین سند |
| `docs/PROJECT_PROGRESS.md` | پیشرفت v0.7 |
| `PROJECT_STATE.md` | وضعیت خلاصه |
| `ARCHITECTURE.md` | جریان داده |
| `ROADMAP.md` | نقشه (قدیمی‌تر از v0.7 در بخش sprint) |
| `CHANGELOG.md` | تاریخچه نسخه |
| `docs/BRS_API.md` | API بازار |
| `docs/HISTORY_ENGINE.md` | تاریخچه |
| `docs/TELEGRAM.md` | تلگرام |
| `docs/DAILY_RANKING.md` | رنک قدیمی/CLI |
| `config/scoring.yaml` | وزن‌ها |
| `core/pipeline/daily_analysis.py` | قلب اجرا |
| `core/ranking/smart_ranker.py` | قلب رتبه‌بندی |
| `services/telegram_bot.py` | ربات |

---

## 22) پیام آماده برای پیست به ایجنت بعدی

```
تو روی ریپوی hamedkazemii/boursepilot شاخه develop کار می‌کنی.
محصول: صندوقچی — دستیار صندوق‌های ETF ایران.
موتور فعلی v0.7 آماده است: BRS → History SQLite → Indicators → SmartRanker
(percentile + trend) → Telegram + Portfolio + AIAdvisor.
منبع حقیقت رتبه‌بندی SmartRanker است نه snapshot کوچک.
Quality gate: top5_avg - worst5_avg > 8 و sane=true.
اسناد: docs/AGENT_HANDOFF.md را کامل بخوان و اجرا کن.

هدف فعلی:
1) FastAPI /api/v1 روی core موجود
2) وب‌اپ کاربر RTL مدرن (خانه، ranking، fund detail، portfolio، advisor)
3) پنل ادمین (overview، pipeline run، ranking QA، publish تلگرام، scoring weights، users)
بدون بازنویسی موتور. secret هاردکد نکن. تست‌ها را سبز نگه دار.
```

---

**پایان Handoff v0.7.0**  
اگر فقط یک کار باید شروع شود: **API خواندنی ranking + Admin overview + Web home** روی همان DB/report موجود.
