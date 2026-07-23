# صندوقچی — مشخصات محصول UI
**نسخه:** 0.7.0-spec  
**همراه با:** `docs/AGENT_HANDOFF.md`

این فایل فقط **وب‌اپ کاربر** و **پنل مدیریت** را مشخص می‌کند تا ایجنت UI بدون درگیر شدن با کل تاریخچه موتور کار کند.

---

## 1. اصول مشترک

- فارسی، RTL، موبایل‌اول
- داده فقط از API/`DailyAnalysisPipeline` — بدون موتور موازی
- همیشه `as_of` + `source` (live/snapshot/demo) نمایش داده شود
- اگر `sane=false` بنر هشدار کیفیت
- لحن تحلیلی؛ بدون تضمین سود
- پالت: تیره حرفه‌ای + سبز مالی `#0E7C66` + قرمز فقط برای perf منفی
- فونت: Vazirmatn

---

## 2. وب‌اپ کاربر

### صفحات MVP
| مسیر | اولویت | شرح |
|------|--------|-----|
| `/` | P0 | داشبورد بازار + top5 + worst5 + گروهها |
| `/ranking` | P0 | جدول/کارت رتبه‌بندی + فیلتر نوع |
| `/funds/:symbol` | P0 | جزئیات + explain + indicators + CTA |
| `/portfolio` | P0 | CRUD ساده |
| `/advisor` | P1 | چت/پرسش |
| `/watchlist` | P1 | لیست پیگیری |
| `/compare` | P2 | تا ۴ نماد |
| `/profile` | P1 | ریسک/سرمایه/افق |
| `/login` | P0 | Telegram Login یا dev login |

### ناوبری موبایل
`خانه | رتبه‌ها | پرتفو | مشاور | بیشتر`

### کامپوننت‌های حیاتی
FundCard, ScoreBadge, RecommendChip, MarketHero, ReasonList, DataSourcePill, SaneGapIndicator, SearchBox

### DoD وب
- top/worst با gap منطقی
- explain نقش‌محور
- پرتفو کار می‌کند
- source شفاف است
- 375px و desktop سالم

---

## 3. پنل ادمین

### صفحات MVP
| مسیر | اولویت | شرح |
|------|--------|-----|
| `/admin` | P0 | KPI سلامت محصول |
| `/admin/pipeline` | P0 | Run analysis/history/preopen/publish |
| `/admin/ranking` | P0 | QA قبل انتشار + gate |
| `/admin/telegram` | P0 | dry-run و publish |
| `/admin/scoring` | P1 | ویرایش weights |
| `/admin/data` | P1 | coverage/quality |
| `/admin/users` | P1 | کاربران و پرتفو |
| `/admin/ai` | P2 | lessons/memory |
| `/admin/system` | P2 | env/version/maintenance |

### ایمنی
- publish دو مرحله‌ای
- force publish وقتی sane=false فقط با تأیید قوی
- audit log
- secret masking
- lock اجرای همزمان pipeline

### DoD ادمین
- login
- overview واقعی
- run analysis
- preview+publish
- weights edit با validation

---

## 4. API لازم (حداقلی)

### Public
- `GET /api/v1/health`
- `GET /api/v1/market/summary`
- `GET /api/v1/ranking/top|worst|today`
- `GET /api/v1/funds/{symbol}`
- `GET /api/v1/funds/{symbol}/history`
- `GET /api/v1/funds/{symbol}/indicators`

### User
- auth telegram
- me/profile/portfolio/watchlist/ask

### Admin
- login
- overview
- pipeline/run + status
- ranking/preview
- telegram/publish
- config/scoring
- users

جزئیات فیلدها: `docs/AGENT_HANDOFF.md` بخش 10–13.

---

## 5. ترتیب پیاده‌سازی پیشنهادی

1. FastAPI read endpoints از `reports/daily_ranking.json` + SQLite  
2. Web home + ranking + fund detail (بدون auth)  
3. Admin login + overview + run/publish  
4. User auth + portfolio  
5. Advisor + scoring editor + compare + alerts  

---

## 6. پیام کوتاه برای ایجنت UI

```
docs/AGENT_HANDOFF.md و docs/PRODUCT_UI_SPEC.md را بخوان.
موتور v0.7 آماده است؛ UI/API بساز نه موتور جدید.
اول FastAPI خواندنی ranking، بعد وب‌اپ RTL، بعد پنل ادمین.
Quality gate و source/as_of را در UI نشان بده.
```
