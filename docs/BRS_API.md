# لایه API بازار — BrsApi (صندوقچی)

## هدف
تأمین **داده زنده** برای کشف روزانه صندوق‌های قابل‌معامله، رنکینگ، پیش‌سفارش و مشاوره پرتفوی — فقط از API، بدون اسکرپ.

## تنظیمات
از `.env` یا secret محیطی:

| متغیر | توضیح |
|--------|--------|
| `BRS_API_KEY` | کلید ۳۲ کاراکتری (حتماً trim شود) |
| `BRS_BASE_URL` | پیش‌فرض `https://Api.BrsApi.ir/Tsetmc` |
| `BRS_USER_AGENT` | User-Agent مرورگر (الزامی) |
| `BRS_TIMEOUT_SECONDS` | تایم‌اوت |
| `BRS_ALL_SYMBOLS_TYPE` | پارامتر type برای AllSymbols (معمولاً 1) |
| `MARKET_DATA_PROVIDER` | فعلاً `brs` |

## Endpointها

| متد provider | Endpoint | کاربرد |
|--------------|----------|--------|
| `get_all_symbols` | `AllSymbols.php?key&type` | همه نمادها + عمق ۵ سطح |
| `get_fund_symbols` | همان + فیلتر صندوق | کشف روزانه ~۴۰۰ صندوق |
| `get_symbol` | `Symbol.php?key&l18` | جزئیات یک نماد |
| `get_nav` | `Nav.php?key&l18` | NAV صدور/ابطال |
| `get_shareholders` | `Shareholder.php?key&l18` | سهامداران عمده |

## ماژول‌ها
```
config.py
services/providers/
  base.py          # Protocol
  models.py        # DTO
  brs_client.py    # HTTP
  brs_mapper.py    # raw → DTO
  brs_provider.py  # پیاده‌سازی
  factory.py       # get_market_data_provider()
  textnorm.py      # ی/ک عربی→فارسی
  exceptions.py
```

## استفاده
```python
from services.providers import get_market_data_provider

provider = get_market_data_provider()  # brs
funds = provider.get_fund_symbols()
quote = provider.get_symbol("عیار")
nav = provider.get_nav("عیار")
```

## تست
```bash
# واحد (بدون شبکه)
python -m unittest tests.test_brs_mapper tests.test_brs_provider tests.test_textnorm -v

# زنده
export BRS_API_KEY=...
python tools/brs_smoke_test.py
```

## نکات امنیتی
- کلید را در git نگذارید.
- User-Agent پیش‌فرض Python استفاده نکنید (ریسک مسدودی IP).
- در این محیط ممکن است خروجی شبکه مستقیم sandbox محدود باشد؛ CI/لوکال با کلید واقعی smoke را بزنید.

## فاز بعد
- اسنپ‌شات روزانه صندوق‌ها
- موتور امتیاز/رنکینگ فارسی
- مانیتور پیش‌سفارش ۸:۴۵–۹
- ربات تلگرام + وب‌اپ + لندینگ صندوقچی
