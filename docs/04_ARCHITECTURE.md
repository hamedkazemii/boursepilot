# صندوقچی Architecture Specification

## معماری کلان

صندوقچی یک سیستم تحلیل هوشمند صندوق‌های سرمایه‌گذاری ایران است.

Flow:

BRS API
→ Provider Layer
→ DTO
→ History Engine
→ SQLite
→ Indicators
→ SmartRanker
→ Analytics
→ API
→ Web / Admin / Telegram


## اصول

### Single Source Of Truth

SmartRanker تنها مرجع رتبه‌بندی است.

هیچ بخش دیگری Ranking مستقل تولید نمی‌کند.


### Domain First

منطق مالی و تحلیلی در Core باقی می‌ماند.


### No Duplicate Intelligence

UI فقط نمایش‌دهنده است.


## Core Modules


Provider:

services/providers


History:

core/history


Indicators:

core/indicators


Ranking:

core/ranking


Analytics:

core/analytics


## ممنوع

- بازنویسی موتور تحلیل بدون دلیل
- hardcode داده
- secret داخل کد
- منطق مالی در Frontend
