# صندوقچی (BoursePilot)

دستیار هوشمند صندوق‌های قابل‌معامله ایران.

**نسخه:** 0.4.0  
**داده:** BrsApi.ir

---

## الان چه کار می‌کند؟
- اتصال زنده BRS
- کشف روزانه ~۴۰۰ صندوق‌مانند
- امتیاز چندعاملی + رنکینگ فارسی با توضیح
- اسکن پیش‌سفارش (عمق خرید/فروش)
- ذخیره اسنپ‌شات روزانه

## اجرا
```bash
pip install -r requirements.txt
cp .env.example .env   # BRS_API_KEY را بگذارید

python -m unittest tests.test_textnorm tests.test_brs_mapper tests.test_brs_provider tests.test_score_engine -v

python tools/run_snapshot.py
python tools/run_daily_rank.py --no-nav
python tools/run_preopen_scan.py
```

## مستندات
- `docs/BRS_API.md`
- `docs/DAILY_RANKING.md`
- `config/scoring.yaml`

## نقشه بعدی
تلگرام V1 → وب‌اپ → لندینگ → پرتفوی شخصی → ارزیابی دقت سیگنال
