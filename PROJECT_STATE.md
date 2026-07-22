# صندوقچی (BoursePilot)
## Project State
Last Update: 2026-07-22
Version: 0.3.0

---

# هدف محصول

ساخت **صندوقچی**: دستیار هوشمند صندوق‌های قابل‌معامله ایران که بتواند:

- کل صندوق‌های قابل معامله (~۴۰۰) را روزانه کشف کند
- داده زنده از BrsApi بگیرد
- رنکینگ فارسی با توضیح بدهد
- پیش‌سفارش ۸:۴۵–۹ را پایش کند
- روی دارایی کاربر مشاوره بدهد
- دقت سیگنال‌های خودش را بسنجد و بهبود دهد
- V1: ربات تلگرام + وب‌اپ ساده + لندینگ

---

# وضعیت فعلی

| بخش | وضعیت |
|-----|--------|
| BRS API Layer | ✅ v0.3.0 |
| Provider Protocol + DTO | ✅ |
| BrsClient / BrsProvider / Mapper | ✅ |
| کشف fund-like از AllSymbols | ✅ (متد آماده) |
| Unit tests (بدون شبکه) | ✅ |
| Smoke test tool | ✅ |
| NAV واقعی از API | ✅ (لایه API) |
| Scanner مبتنی بر BRS | ❌ هنوز TSETMC قدیمی |
| Score / Ranking فارسی کامل | ❌ |
| پیش‌سفارش ۸:۴۵–۹ | ❌ |
| ربات تلگرام | ❌ (سرویس خام موجود) |
| وب‌اپ / لندینگ | ❌ |
| پرتفوی کاربر / مشاوره | ❌ |
| خودارزیابی سیگنال | ❌ |

---

# منبع داده

- **اصلی:** BrsApi.ir (`AllSymbols`, `Symbol`, `Nav`, `Shareholder`)
- کلید: env `BRS_API_KEY`
- User-Agent مرورگر الزامی است

---

# فاز بعدی

1. اسنپ‌شات روزانه ~۴۰۰ صندوق
2. موتور امتیاز و رنکینگ فارسی
3. جاب پیش‌سفارش
4. تلگرام V1
5. وب‌اپ + لندینگ
6. مشاوره پرتفوی
7. feedback loop

---

# Documentation

- README.md
- docs/BRS_API.md
- ROADMAP.md
- ARCHITECTURE.md
- CHANGELOG.md
- VERSION
