# صندوقچی Database Specification


## Database

Current:

SQLite


Future:

PostgreSQL برای Production


## Core Tables


## funds

اطلاعات صندوق:

- symbol
- name
- type
- active


## history

تاریخچه بازار:

- price
- volume
- value
- orderbook
- date


## nav_history

NAV و premium/discount


## daily_scores

خروجی SmartRanker


## users

کاربران:


- telegram_id
- username
- risk_profile
- capital


## portfolios

دارایی کاربران:


- symbol
- units
- avg_price


## ai_memory

حافظه AI


## Rules

Database فقط محل ذخیره است.

Business Logic در Core باقی می‌ماند.
