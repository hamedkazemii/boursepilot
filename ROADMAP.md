# BoursePilot Roadmap

## Version 0.1 - Foundation ✅

انجام شده:

- ساخت ساختار پروژه
- ایجاد Core Engine
- ایجاد Service Layer
- اتصال اولیه به TSETMC
- ساخت Scanner اولیه
- ساخت Ranking Engine
- ساخت Scoring Engine


---

# Version 0.2 - Real Market Discovery ✅

انجام شده:

- اتصال به Endpoint قدیمی TSETMC Search
- کشف خودکار نمادها
- حذف وابستگی به funds.json دستی
- استخراج InsCode واقعی


---

# Version 0.3 - Fund Registry 🔄

در حال انجام:

هدف:

ساخت مرجع اصلی صندوق‌های بازار


مراحل:

1. دریافت 194 نماد کشف شده

2. دریافت InstrumentInfo برای هر نماد

3. بررسی:

- cgrValCotTitle
- sector
- faraDesc


4. حذف:

- سهام عادی
- حق تقدم
- اوراق
- ابزارهای غیر صندوق


5. ذخیره:

data/fund_registry.json



خروجی:

لیست کامل صندوق‌های واقعی


---

# Version 0.4 - Market Analyzer

هدف:

تحلیل واقعی بازار


اضافه می‌شود:


## OrderBook Analysis

- قدرت خریدار
- قدرت فروشنده
- صف خرید
- صف فروش


## Liquidity

- حجم معاملات
- ارزش معاملات
- گردش


## Trend

- روند کوتاه مدت
- روند میان مدت
- روند بلند مدت


---

# Version 0.5 - NAV Engine

هدف:

تحلیل ارزش واقعی صندوق


محاسبات:


NAV

Market Price

Premium

Discount


خروجی:

حباب مثبت / منفی


---

# Version 0.6 - BPI Score Engine


امتیاز نهایی:

BoursePilot Index


فرمول:


Performance

+

Liquidity

+

Smart Money

+

NAV

+

Risk

+

Trend



خروجی:

Score 0-100


---

# Version 0.7 - Recommendation Engine


تولید پیشنهاد:


Strong Buy

Buy

Hold

Avoid

Sell



بر اساس:

Score

Risk

Trend

NAV


---

# Version 0.8 - Reporting


گزارش روزانه:


- بهترین صندوق‌ها
- ضعیف‌ترین صندوق‌ها
- فرصت‌ها
- ریسک‌ها


---

# Version 0.9 - Automation


- Scheduler
- Daily Scan
- Telegram Bot
- Notification


---

# Version 1.0


سیستم کامل تحلیل هوشمند صندوق‌های بورس ایران
