# BoursePilot
## Project State
Last Update: 2026-07-20

---

# هدف پروژه

ساخت یک سیستم هوشمند تحلیل بازار بورس ایران که بتواند:

- کل بازار را اسکن کند
- تمام ETF ها را به صورت خودکار کشف کند
- صندوق‌ها را طبقه‌بندی کند
- اطلاعات واقعی بازار را دریافت کند
- قدرت خریدار و فروشنده را تحلیل کند
- NAV را تحلیل کند
- حباب صندوق را محاسبه کند
- نقدشوندگی را بررسی کند
- رتبه‌بندی انجام دهد
- پیشنهاد خرید و فروش واقعی ارائه کند
- گزارش روزانه تولید کند
- در آینده به تلگرام متصل شود.

---

# وضعیت فعلی

پروژه وارد فاز Real Market شده است.

دیگر از داده Mock استفاده نمی‌شود.

تمام داده‌ها باید از TSETMC دریافت شوند.

---

# ساختار پروژه

core/

decision.py

market_analyzer.py

market_engine.py

market_loader.py

market_universe.py

ranking.py

scanner.py

scoring.py

services/

tsetmc_client.py

tsetmc_market.py

fund_loader.py

fund_discovery.py

fund_registry.py

fund_classifier.py

providers/

collectors/

parsers/

tools/

endpoint_explorer.py

fund_validator.py

build_fund_registry.py

tests/

...

---

# API های واقعی

در حال حاضر API های زیر سالم هستند.

Instrument/GetInstrumentInfo/{InsCode}

ClosingPrice/GetClosingPriceInfo/{InsCode}

BestLimits/{InsCode}

Trade/GetTrade/{InsCode}

ClosingPrice/GetClosingPriceDailyList/{InsCode}/0

---

# API هایی که خراب هستند

InstrumentSearch

GetInstrumentAll

GetInstrumentByName

GetInstrument

این Endpoint ها دیگر استفاده نمی‌شوند.

---

# روش کشف صندوق‌ها

به جای API جدید از Endpoint قدیمی استفاده می‌شود.

https://old.tsetmc.com/tsev2/data/search.aspx?skey=...

نمونه:

skey=صندوق

skey=طلا

skey=ثابت

skey=اهرم

...

---

# Discovery

FundDiscovery نوشته شده است.

با جستجوی چند کلیدواژه:

194 نماد پیدا شده است.

هر رکورد شامل:

symbol

name

ins_code

---

# Registry

هدف:

ساخت فایل

data/fund_registry.json

که فقط صندوق‌های واقعی داخل آن باشند.

---

# Classifier

تشخیص نوع صندوق با استفاده از:

InstrumentInfo

sector

faraDesc

cgrValCotTitle

نوع‌ها:

سهامی

درآمد ثابت

طلا

اهرمی

مختلط

کالایی

UNKNOWN

---

# Scanner

Scanner اکنون از API واقعی استفاده می‌کند.

دریافت می‌کند:

OrderBook

ClosingPrice

History

InstrumentInfo

---

# Ranking

RankingEngine آماده است.

BPIScorer آماده است.

در حال حاضر امتیازها هنوز ساده هستند.

در نسخه بعد:

NAV Score

Bubble Score

Liquidity Score

Volume Score

Smart Money Score

Trend Score

Risk Score

به آن اضافه خواهد شد.

---

# مشکلات فعلی

1-

data/funds.json

هنوز شامل برخی داده‌های قدیمی است.

مثلاً:

عیار

اشتباه به InsCode پتروشیمی نوری وصل شده است.

دلیل:

نسخه اولیه پروژه.

---

2-

تمام InsCode ها باید مجدداً از Discovery ساخته شوند.

هیچ داده دستی نباید باقی بماند.

---

3-

Registry هنوز کامل نشده است.

---

# هدف مرحله بعد

ساخت Registry واقعی

↓

اعتبارسنجی تمام 194 نماد

↓

تشخیص نوع واقعی

↓

حذف سهام

↓

باقی ماندن فقط ETF ها

↓

ذخیره در fund_registry.json

---

# برنامه نسخه بعد

بعد از Registry:

تحلیل NAV

↓

تحلیل حباب

↓

قدرت خریدار

↓

قدرت فروشنده

↓

جریان پول

↓

روند

↓

امتیاز BPI واقعی

↓

رتبه‌بندی

↓

پیشنهاد خرید

↓

گزارش روزانه

---

# اصول پروژه

هیچ داده Mock

هیچ داده دستی

هیچ حدس

فقط داده واقعی بازار

هر تحلیل باید قابل اثبات باشد.

---

# وضعیت فعلی

Discovery

✔

Classifier

✔

Scanner

✔

API

✔

Registry

در حال توسعه

NAV Engine

شروع نشده

Bubble Engine

شروع نشده

Liquidity Engine

شروع نشده

Money Flow Engine

شروع نشده

Recommendation Engine

شروع نشده

Telegram

شروع نشده

Dashboard

شروع نشده



---

# Documentation System

Project documentation created:

PROJECT_STATE.md

ROADMAP.md

ARCHITECTURE.md

CHANGELOG.md


From now on every major development step updates these files.

