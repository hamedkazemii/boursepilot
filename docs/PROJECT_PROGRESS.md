# گزارش جامع روند پروژه صندوقچی (BoursePilot)

**تاریخ:** 2026-07-23  
**نسخه جاری:** 0.6.1 (در حال تثبیت روی `develop`)  
**ریپو:** https://github.com/hamedkazemii/boursepilot  
**PR اصلی v0.6:** https://github.com/hamedkazemii/boursepilot/pull/1

---

## 1) هدف محصول

صندوقچی فقط «فهرست رتبه» نیست؛ باید **دستیار هوشمند سرمایه‌گذاری** باشد:

- امروز چند صندوق بررسی شد؟
- وضعیت و قدرت بازار چیست؟
- کدام گروه قوی/ضعیف است؟
- هر صندوق **چرا** برتر یا ضعیف است؟
- بعداً: پرتفو، هشدار، پیشنهاد تخصیص، realtime

---

## 2) آنچه تا امروز ساخته شده

### لایه داده
| جزء | وضعیت | توضیح |
|-----|--------|--------|
| BRS Provider | ✅ | AllSymbols / Symbol / Nav / Shareholders |
| Fund Catalog + Snapshot | ✅ | JSON روزانه |
| History Engine + SQLite | ✅ Sprint 1 | funds, history, nav_history, market_snapshot, daily_scores, request_cache |
| Incremental upsert | ✅ | جلوگیری از duplicate روزانه |
| Request cache | ✅ | کاهش درخواست تکراری |

### لایه تحلیل/امتیاز
| جزء | وضعیت | توضیح |
|-----|--------|--------|
| Factors (liquidity, orderbook, money_flow, momentum, volume, nav) | ✅ | وزن‌ها در `config/scoring.yaml` |
| ScoreEngine + FundRanker | ✅ | Final score + recommendation |
| MarketSummary | ✅ | قدرت بازار، best/worst group |
| Explain engine (top/worst جدا) | ✅ 0.6.1 | `core/analytics/explain.py` |
| Indicator Engine (EMA/RSI/...) | ❌ Sprint 2 | اسکلت پکیج هست |
| Smart Ranking سری‌زمانی | ❌ Sprint 3 | هنوز snapshot-محور است |

### تلگرام
| جزء | وضعیت | توضیح |
|-----|--------|--------|
| ارسال کانال + chunk/retry | ✅ | `services/telegram/client.py` |
| گزارش هوشمند چندپیامی | ✅ | summary + top cards + worst cards |
| کیبورد اینلاین | ✅ | menu / after-report / fund actions |
| ربات long-poll + callback | ✅ | `/today /top /worst /market /gold ...` |
| Fallback snapshot/demo | ✅ | وقتی BRS از محیط در دسترس نیست |
| توضیح weak درست (نه کپی top) | ✅ 0.6.1 | اصلاح explain |

### اتوماسیون
| جزء | وضعیت |
|-----|--------|
| `morning.yml` | ✅ history + smart rank |
| `daily_rank.yml` | ✅ |
| `preopen.yml` | ✅ |
| Secrets: BRS / TELEGRAM_* | ✅ (محلی + GitHub) |

---

## 3) معماری فعلی (خلاصه)

```
BRS API
  → providers
    → HistoryEngine (SQLite)
    → Catalog/Snapshot (JSON)
      → ScoreEngine (factors)
        → Ranker
          → MarketSummary + Explain
            → Telegram smart report / Bot buttons
```

ساختار هدف‌مند:

```
core/database | history | analytics | scoring | ranking | pipeline | indicators* | ai*
services/providers | telegram | discovery | snapshot | portfolio*
workflows* | reports | tools | tests
```

---

## 4) مشکلات شناخته‌شده و وضعیت‌شان

| مشکل | وضعیت | اقدام |
|------|--------|--------|
| توضیح صندوق‌های ضعیف شبیه برترها بود | ✅ رفع شد | `explain_fund(kind=worst/top)` + summary_reasons نقش‌محور |
| دکمه‌ها بدون polling کار نمی‌کردند | ✅ رفع مفهومی | bot باید همیشه up باشد |
| BRS از sandbox Gumloop SSL error | ⚠️ محیطی | fallback snapshot؛ روی VPS/ایران باید live شود |
| `services/telegram.py` قدیمی روی remote ممکن است همزمان با پکیج باشد | ⚠️ | در سینک بعدی پاک/جایگزین شود |
| NAV premium گاهی outlier (مثلاً -90٪) | ⚠️ جزئی | فیلتر sane در explain؛ mapper/واحد قیمت بعداً |
| رتبه‌بندی هنوز بیشتر همان‌روز است | ⏳ | Sprint 2–3 |

---

## 5) تصمیم‌های معماری مهم

1. **Feature-based development:** هر قابلیت = تست + dry-run + commit جدا روی `develop`
2. **Secret فقط env/GitHub Secrets** — هیچ کلید در گیت
3. **هسته تحلیل به raw BRS وابسته نباشد** — فقط DTO
4. **گزارش = دانش:** «چرا این رتبه؟» اجباری است
5. **Telegram UX:** چندپیام هوشمند + دکمه؛ کانال برای broadcast، چت خصوصی برای تعامل

---

## 6) مسیر ادامه (اولویت‌بندی)

### همین هفته — تثبیت v0.6.x
1. Merge PR #1 به main (پس از review)
2. Deploy ربات روی VPS/systemd (polling دائمی)
3. یک بار `run_history_sync` + `run_telegram_rank --smart` روی شبکه ایران
4. پاکسازی فایل‌های legacy و یکدست‌سازی importها

### Sprint 2 — Indicator Engine (اولویت بالا)
از جدول `history`:
- بازده 1/5/20/60/90
- EMA20/50/200, RSI, MACD, ATR, Bollinger
- Sharpe, Sortino, MaxDD, Volatility
- میانگین حجم و نسبت حجم امروز/میانگین

خروجی در explain:
> «حجم امروز 2.3× میانگین ۲۰روزه»  
> «زیر EMA50 و RSI=32»

### Sprint 3 — Smart Ranking سری‌زمانی
امتیازهای پایدار:
Trend / MoneyFlow / Risk / Liquidity / Volume / NAV / Technical / HistoricalReturn / AI Confidence  
→ Final Score 0..100 با وزن‌های قابل تنظیم

### Sprint 4 — Market Analyzer 08:50
قدرت گروه، ورود/خروج پول، پیش‌سفارش، بیشترین نقدشوندگی

### Sprint 5 — Telegram Platform کامل
`/today /top /worst /gold /fixed /stock /search /compare /portfolio /watchlist`

### Sprint 6–8
Portfolio واقعی → AI Advisor → Realtime alerts

---

## 7) معیار آمادگی v1.0

- [ ] تاریخچه ≥ 60 روز معاملاتی برای اکثر صندوق‌ها
- [ ] اندیکاتورها در explain و score استفاده شوند
- [ ] گزارش صبحگاهی پایدار روی کانال (CI سبز)
- [ ] ربات دکمه‌ای 24/7
- [ ] پرتفو حداقل MVP
- [ ] تست‌های integration روی داده live (شبکه ایران/VPS)

---

## 8) دستورهای کلیدی

```bash
# تست
python -m unittest tests.test_explain tests.test_smart_report \
  tests.test_history_engine tests.test_telegram tests.test_score_engine -v

# تاریخچه
python tools/run_history_sync.py

# گزارش هوشمند
python tools/run_telegram_rank.py --no-nav --smart --dry-run
python tools/run_telegram_rank.py --no-nav --smart

# ربات دکمه‌ای (باید همیشه روشن بماند)
python tools/run_telegram_bot.py
```

---

## 9) جمع‌بندی یک‌خطی

**از اسکریپت‌های پراکنده به اسکلت محصولی v0.6 رسیدیم:** داده تاریخی SQLite + امتیاز چندعاملی + گزارش هوشمند چندپیامی + ربات دکمه‌ای.  
**گام بعدی حیاتی:** Indicator Engine روی سری زمانی تا توضیح‌ها و رتبه‌ها واقعاً «هوشمند» شوند، نه فقط snapshot امروز.
