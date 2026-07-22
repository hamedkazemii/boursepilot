# Changelog

## 2026-07-22 — v0.3.0 (صندوقچی / BRS API Layer)

### Product
- نام محصول کاربر-محور: **صندوقچی**
- مسیر داده اصلی: **BrsApi.ir** (نه اسکرپ TSETMC)

### Added
- `config.py` سالم با تنظیمات BRS از env
- لایه provider استاندارد:
  - `services/providers/base.py` (Protocol)
  - `services/providers/models.py` (DTO)
  - `services/providers/brs_client.py`
  - `services/providers/brs_mapper.py`
  - `services/providers/brs_provider.py`
  - `services/providers/factory.py`
  - `services/providers/textnorm.py`
  - `services/providers/exceptions.py`
- Fixture و تست واحد بدون شبکه:
  - `tests/test_brs_mapper.py`
  - `tests/test_brs_provider.py`
  - `tests/test_textnorm.py`
  - `tests/fixtures/brs/*`
- `tools/brs_smoke_test.py` برای تست زنده
- `docs/BRS_API.md`

### Notes
- `AllSymbols` پوشش قیمت، حجم، حقیقی/حقوقی و عمق ۵ سطح را دارد
- `Nav.php` NAV صدور/ابطال می‌دهد
- فازهای بعد: کشف روزانه ~۴۰۰ صندوق، رنکینگ، پیش‌سفارش ۸:۴۵–۹، تلگرام، وب‌اپ

---

## 2026-07-20

### Added
- Real TSETMC InstrumentInfo connection
- Real ClosingPrice connection
- Real OrderBook connection
- FundDiscovery module
- Search based discovery using old TSETMC endpoint

### Fixed
- Removed dependency on broken API endpoints

### Discovered
194 candidate funds found

### Next
Build Fund Registry
