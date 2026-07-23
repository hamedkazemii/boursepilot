# صندوقچی Admin Panel Specification


## هدف

کنترل محصول توسط مدیر.


## صفحات


/admin

Overview:

- آخرین تحلیل
- سلامت داده
- کاربران
- وضعیت تلگرام


/admin/pipeline

اجرای:

- history sync
- analysis
- publish


/admin/ranking

QA رتبه‌بندی


/admin/telegram

انتشار گزارش


/admin/scoring

مدیریت وزن‌ها


/admin/users

مدیریت کاربران


## امنیت

- Login
- JWT
- Audit Log
- Secret Masking


## Publish

قبل از انتشار:

Preview

↓

Confirm

↓

Publish
