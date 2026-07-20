# BoursePilot Architecture


## Data Flow


TSETMC

|

|

Discovery Layer

|

|

Registry

|

|

Market Data Layer

|

|

Analyzer Engine

|

|

Scoring Engine

|

|

Ranking Engine

|

|

Recommendation Engine

|

|

Report


---


# Layers


## Discovery Layer


مسئول:

کشف نمادها


فایل:

services/fund_discovery.py


منبع:

TSETMC Search


---


## Registry Layer


مسئول:

نگهداری صندوق‌های معتبر


فایل:

services/fund_registry.py


خروجی:

data/fund_registry.json


---


## Market Data Layer


مسئول:


دریافت:


- قیمت
- معاملات
- سفارشات
- تاریخچه


فایل:

services/tsetmc_client.py


---


## Analysis Layer


مسئول:


تبدیل داده خام به تحلیل


فایل‌ها:


core/market_engine.py

core/market_analyzer.py


---


## Scoring Layer


مسئول:


امتیازدهی


فایل:


core/scoring.py


---


## Ranking Layer


مسئول:


رتبه‌بندی


فایل:


core/ranking.py


---


## Reporting


مسئول:


تولید گزارش


reports/


