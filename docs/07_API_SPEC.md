# صندوقچی API Specification


Base:

/api/v1


## Public


GET /health

GET /market/summary

GET /ranking/today

GET /ranking/top

GET /ranking/worst

GET /funds/{symbol}

GET /funds/{symbol}/history

GET /funds/{symbol}/indicators


## User


GET /me

PATCH /me

GET /me/portfolio

POST /me/portfolio/items

DELETE /me/portfolio/items/{symbol}

POST /me/ask


## Admin


POST /admin/auth/login

GET /admin/overview

POST /admin/pipeline/run

GET /admin/ranking/preview

POST /admin/telegram/publish

GET /admin/config/scoring

PUT /admin/config/scoring


## Rules

- JSON UTF8
- Validation
- Audit
- بدون Business Logic داخل API


هر پاسخ تحلیلی:

source

as_of

confidence

explain

