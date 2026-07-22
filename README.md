# صندوقچی (BoursePilot)

دستیار هوشمند صندوق‌های قابل‌معامله ایران.

**نسخه:** 0.3.0  
**داده بازار:** [BrsApi.ir](https://brsapi.ir)  
**وضعیت فاز:** لایه API آماده — رنکینگ/تلگرام/وب‌اپ در فازهای بعد

---

## قابلیت‌های هدف محصول
- کشف روزانه ~۴۰۰ صندوق قابل معامله
- رنکینگ فارسی با توضیح
- پایش پیش‌سفارش ۸:۴۵ تا ۹:۰۰
- مشاوره روی پرتفوی کاربر
- ربات تلگرام + وب‌اپ + لندینگ
- خودارزیابی سیگنال‌ها

---

## شروع سریع — لایه API

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# BRS_API_KEY را در .env بگذارید

# تست واحد (بدون شبکه)
python -m unittest tests.test_textnorm tests.test_brs_mapper tests.test_brs_provider -v

# اسموک زنده
python tools/brs_smoke_test.py
```

### استفاده در کد
```python
from services.providers import get_market_data_provider

provider = get_market_data_provider()
funds = provider.get_fund_symbols()
quote = provider.get_symbol("عیار")
nav = provider.get_nav("عیار")
```

مستند API: [`docs/BRS_API.md`](docs/BRS_API.md)

---

## Version 0.2.0 (legacy notes)
- Live market architecture scaffold
- Multi factor BPI engine (early)
- Persian morning report scaffold
- ETF registry preparation
