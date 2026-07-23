# صندوقچی Agent Start Guide

این اولین فایل ورودی هر Agent است.

## محصول

نام:
صندوقچی

نام انگلیسی:
BoursePilot


## هدف

ساخت دستیار هوشمند تحلیل صندوق‌های سرمایه‌گذاری ایران.


## قبل از هر تغییر

مطالعه الزامی:

1. PROJECT_CONTEXT.md
2. SANDOGHCHI_MASTER_CONTEXT.md
3. 01_PROJECT_STATE.md
4. 04_ARCHITECTURE.md


## قوانین اصلی

- SmartRanker تنها مرجع رتبه‌بندی است.
- UI موتور تحلیل ندارد.
- Secret داخل Git ممنوع است.
- Core بدون دلیل بازنویسی نشود.
- تست قبل از Merge اجرا شود.


## مسیر توسعه

Core

↓

API

↓

Web App

↓

Admin Panel

↓

AI Advisor

