# Telegram UX Redesign — صندوقچی

بنیاد بر سند هویت برند: **User = Hero, Sandoghchi = Guide** | **AI = Decision Assistant** | **DATA → ANALYSIS → INSIGHT** | **Iran Market First** | **Trust First** | **Explainability First** | **No Hype**

---

## ۱. معماری زمانی بازار ایران (Market Hours Engine)

```python
# core/market/hours.py
MARKET_SESSIONS = {
    "pre_open":   {"start": "08:45", "end": "09:00",   "days": [5,6,0,1,2]},  # شنبه-چهارشنبه
    "morning":    {"start": "09:00", "end": "12:00",   "days": [5,6,0,1,2]},  # بازارهای اول
    "midday":     {"start": "11:00", "end": "15:00",   "days": [5,6,0,1,2]},  # بازارهای دوم (تداخل)
    "afternoon":  {"start": "15:00", "end": "17:00",   "days": [5,6,0,1,2]},  # بازارهای سوم
    "gold_24h":   {"start": "00:00", "end": "23:59",   "days": [5,6,0,1,2,3,4]},  # طلا/کالایی ۲۴ساعته
}

FUND_SESSION_MAP = {
    "طلا": "gold_24h",
    "کالایی": "gold_24h",
    "اهرم": "morning",      # سهام/اهرم با بازار اصلی
    "سهامی": "morning",
    "مختلط": "morning",
    "درآمد ثابت": "midday",  # صندوق‌های درآمد ثابت معمولاً بازه میانی
}
```

**زمان‌بندی گزارش‌های خودکار:**
| ساعت | گزارش | توضیح |
|------|-------|-------|
| 08:50 | **صبحانه بازار** | پیش‌بازار + کل صندوق‌های بورسی + پتانسیل‌ها |
| 10:00 | **نبرد صبح** | آپدیت لحظه‌ای صندوق‌های فعال |
| 12:30 | **استراحت بازار** | جمع‌بندی نیمی‌روز |
| 15:15 | **ساعت آخر** | روند پایانی + سیگنال‌های روز بعد |
| 17:10 | **بازار بسته** | جمع‌بندی کامل + آماده‌سازی فردا |
| هر ۱۵ دقیقه در ساعات بازار | **میکرو‌آپدیت** | فقط تغییرات معنادار (فیلتر شده) |

---

## ۲. دسته‌بندی صندوق‌ها (Fund Taxonomy)

```python
FUND_CATEGORIES = {
    "gold": {
        "label": "🥇 طلا و کالایی",
        "session": "gold_24h",
        "examples": ["عیار", "مثقال", "طلا", "کالای کهربا", "کالای پارسیان"],
        "analysis_mode": "nav_premium_tracking",  # ردیابی NAV/پرمیوم
        "exclude_from_general_top5": True,
    },
    "fixed_income": {
        "label": "💵 درآمد ثابت",
        "session": "midday",
        "examples": ["کارین", "صبا", "ایمن", "پایدار", "آینده"],
        "analysis_mode": "yield_duration",  # بازده/مدت/ریسک اعتبار
        "exclude_from_general_top5": True,
        "separate_reporting": True,
    },
    "equity": {
        "label": "📈 سهامی",
        "session": "morning",
        "examples": ["هما", "بذر", "خورشید", "سرو", "آگاس", "رشد"],
        "analysis_mode": "momentum_quality",
    },
    "leverage": {
        "label": "⚡ اهرمی",
        "session": "morning",
        "examples": ["اهرم", "موج", "توان", "لبخند", "افران"],
        "analysis_mode": "leverage_risk_adjusted",
    },
    "mixed": {
        "label": "🔀 مختلط",
        "session": "morning",
        "examples": ["الماس"],
        "analysis_mode": "balanced_allocation",
    },
}
```

---

## ۳. سرویس‌های اصلی (Core Services)

### ۳.۱ گزارش صبحانه بازار (Daily Market Brief) — ۰۸:۵۰
```
📊 صندوقچی — صبحانه بازار ۱۴۰۳/۰۵/۱۸
━━━━━━━━━━━━━━━━━━━━━━━━

🌅 پیش‌بازار (۰۸:۴۵-۰۹:۰۰)
• نمادهای فعال: ۱۲ صندوق | حجم پیش‌فروش: ۴۵ میلیارد
• گرادیان مثبت: ۸ | منفی: ۳ | خالی: ۱

📈 وضعیت کلی بازار (۳۰ صندوق تحلیل‌شده)
• قدرت بازار: ۵۸/۱۰۰ (میانگین با تمایل به خرید)
• بهترین گروه: طلا (+۱.۲٪) | ضعیف‌ترین: درآمد ثابت (-۰.۳٪)
• بازار سهامی: روند صعودی ضعیف | اهرمی: نوسان بالا

🏆 صندوق‌های با پتانسیل بالا (امروز)
1. عیار (طلا) — ۷۵.۷ | خرید | پرمیوم ۲.۱٪ | NAV رشد ۰.۸٪
2. مهتاب (سهامی) — ۷۲.۳ | خرید | مومنتوم قوی | حجم ۳ برابر
3. بذر (سهامی) — ۷۰.۱ | خرید | کاش قوی | P/E جذاب

⚠️ صندوق‌های با پتانسیل ضعیف (مراقبت)
1. پایدار (درآمد ثابت) — ۳۲.۱ | فروش | ریسک اعتبار بالا
2. موج (اهرمی) — ۳۵.۴ | کاهش | بتا ۲.۴ | انحراف بالا

📁 پرتفوی شما (اگر ثبت شده)
• ارزش فعلی: ۱۲۵ میلیون | سود/زیان: +۳.۲٪
• تحلیل: ۲ صندوق در زون ریسک | پیشنهاد: کم کردن اهرمی‌ها

[دکمه‌ها: 🏆 برترین‌ها | ⚠️ ضعیف‌ها | 🌐 بازار | 📁 پرتفویم | 🤖 بپرس]
```

### ۳.۲ تحلیل گروه‌بندی (Category Reports)
```
/gold → 🥇 طلا و کالایی (n=۶)
━━━━━━━━━━━━━━━━━━━━━
🏆 برترین: عیار (۷۵.۷) — پرمیوم پایین، NAV صعودی
🥈 دوم: مثقال (۷۱.۲) — حجم بالا،Spread کم
...
⚠️ ضعیف: کهربا (۴۲.۳) — پرمیوم منفی، حجم خفیف

/fixed → 💵 درآمد ثابت (n=۸) — گزارش جداگانه
━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ نکته: صندوق‌های درآمد ثابت در_TOP5_ کلی نمایش داده نمی‌شوند
🏆 برترین: کارین (۷۱.۲) — بازده ۲۳٪، مدت ۰.۸ سال، اعتبار AA
🥈 دوم: صبا (۶۵.۴) — بازده ۲۱٪، تنوع خوب
...
⚠️ ضعیف: پایدار (۳۲.۱) — ریسک عدم پرداخت، بازده واقعی منفی

/equity → 📈 سهامی (n=۱۰)
/leverage → ⚡ اهرمی (n=۶)
/mixed → 🔀 مختلط (n=۱)
```

### ۳.۳ تحلیل تک صندوق (Fund Deep Dive) — `/fund عیار` یا دکمه جستجو
```
🔍 تحلیل عمیق: عیار (صندوق طلای عیار مفید)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 امتیاز کلی: ۷۵.۷/۱۰۰ | 🟢 خرید
📈 روند: صعودی پایدار (۳ هفته) | مومنتوم: قوی

💰 قیمت و NAV
• قیمت: ۴۷۰,۴۲۰ | NAV: ۴۶۰,۵۰۰ | پرمیوم: +۲.۱٪
• تغییر روز: +۰.۸٪ | هفته: +۳.۲٪ | ماه: +۱۲.۵٪

📈 اندیکاتورها (۳۰ روز)
• RSI: ۶۲ (خنثی-مثبت) | MACD: صعودی | EMA۲۰ > EMA۵۰
• شارپ: ۱.۸ | سورتینو: ۲.۳ | ماکس DD: -۴.۲٪
• الفا (فاما-فرنچ ۳ فاکتور): +۳.۱٪ سالانه

🔬 تحلیل پیشرفته (Advanced Ratios)
• ترینور: ۱.۵ | جنسن آلفا: +۲.۸٪ | اطلاعات: ۰.۹
• کالمار: ۳.۲ | اومگا: ۲.۱ | استرلینگ: ۲.۷
• CVaR ۹۵٪: -۳.۱٪ | Tail Ratio: ۱.۶

📊 مقایسه دسته (طلا، n=۶)
• رتبه: ۱/۶ | درصدیل: ۹۵
• نسبت به میانگین دسته: +۱۸.۳ امتیاز

🧠 توضیح ساده (Explainability)
> «عیار در ۳ هفته اخیر روند صعودی پایدار داشته. پرمیوم ۲٪ نشان‌دهنده تقاضا است اما حبابی نیست. شارپ ۱.۸ و سورتینو ۲.۳ بیانگر بازده تنظیم‌شده بر ریسک عالی. ریسک اصلی: نوسان قیمت طلا جهانی.»

⏱ آخرین بروزرسانی: ۱۴۰۳/۰۵/۱۸ ۰۹:۱۵ (داده ۵ دقیقه قبل)

[دکمه‌ها: 🔄 بروزرسانی | ⭐ واچ‌لیست | ➕ به سبد | ⚖️ مقایسه | 🏠 منو]
```

### ۳.۴ پرتفوی هوشمند (Smart Portfolio) — `/portfolio`
```
📁 پرتفوی شما — ۱۴۰۳/۰۵/۱۸ ۰۹:۲۰
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 خلاصه
• سرمایه: ۵۰۰ میلیون | ارزش فعلی: ۵۱۶ میلیون (+۳.۲٪)
• نقد: ۱۲ میلیون (۲.۳٪) | تنوع: ۷ صندوق / ۴ دسته

📊 تحلیل ریسک
• ریسک پورتفوی: متوسط | بتا پورتفوی: ۱.۱۵
• VaR ۹۵٪ (روزانه): -۱.۸٪ | ماکس DD تاریخ: -۸.۳٪
• تمرکز: ۳۵٪ در طلا (รีسک تمرکز متوسط)

🎯 صندوق‌های پرتفوی
1. عیار (طلا) — ۳۰٪ | +۵.۲٪ | 🟢 نگه‌داری
2. بذر (سهامی) — ۲۵٪ | +۲.۱٪ | 🟢 نگه‌داری
3. کارین (درآمد ثابت) — ۲۰٪ | +۰.۸٪ | 🟡 بررسی پرمیوم
4. موج (اهرمی) — ۱۵٪ | -۳.۴٪ | 🔴 ریسک بالا / پیشنهاد کاهش
5. الماس (مختلط) — ۱۰٪ | +۱.۲٪ | 🟢 نگه‌داری

💡 پیشنهادات AI (Decision Assistant)
• موج: بتا ۲.۴ در بازار نوسانی خطرناک. کاهش به ۵٪ یا خروج.
• کارین: بازده خوب اما پرمیوم NAV بالا. صبر برای اصلاح.
• تنوع: اضافه کردن صندوق سهامی کم‌ریسک (مثل رشد) برای توازن.

[دکمه‌ها: 🔄 بروزرسانی | ➕ افزودن | ➖ حذف | ⚖️ بازتعادل | 🏠 منو]
```

### ۳.۵ مشاور هوشمند (AI Advisor) — چت آزاد یا `/ask`
```
کاربر: «۵۰ میلیون ریسک کم یک‌ساله، چی بخرم؟»

🤖 مشاور صندوقچی
━━━━━━━━━━━━━━━━━━━━━

📋 پروفایل شما: ریسک کم | افق ۱۲ ماه | ۵۰ میلیون

🎯 پیشنهاد تخصیص (بر اساس داده امروز):
• ۴۰٪ درآمد ثابت (کارین، صبا) — پایداری، بازده ۲۱-۲۳٪
• ۳۰٪ طلا (عیار، مثقال) — هم‌پوشانی با تورم، پرمیوم کنترل‌شده
• ۲۰٪ سهامی کم‌ریسک (رشد، بذر) — رشد با نوسان کم
• ۱۰٪ نقد/مختلط (الماس) — انعطاف

⚠️ نکات مهم:
• صندوق‌های اهرمی (موج، توان) برای ریسک کم مناسب نیستند
• درآمد ثابت: فقط صندوق‌های اعتبار AA+ و مدت <۱ سال
• طلا: پرمیوم >۳٪ یعنی ریسک اصلاح — صبر کنید

📝 این 제안 **تصمیم‌گیرنده** نیست. شما تصمیم می‌گیرید.
من فقط داده، تحلیل و سناریوها را می‌گذارم پیش‌رو.

[دکمه‌ها: 📊 تحلیل کامل | 📁 بساز پرتفوی | ❓ سوال دیگر | 🏠 منو]
```

### ۳.۶ بک‌تست و بهبود استراتژی (Backtest Engine)
```python
# core/backtest/engine.py
class BacktestEngine:
    """
    بک‌تست استراتژی‌های تحلیلی برای بهبود مدل امتیازدهی.
    اجرا: روزانه در cron (بعد از بسته شدن بازار)
    """
    STRATEGIES = {
        "momentum_30d": {"lookback": 30, "factor": "price_momentum"},
        "mean_reversion": {"lookback": 60, "factor": "nav_premium_zscore"},
        "factor_ff3": {"factors": ["market", "size", "value"]},
        "factor_c4": {"factors": ["market", "size", "value", "momentum"]},
        "advanced_ratios": {"metrics": ["sharpe", "sortino", "calmar", "omega"]},
    }
    
    def run_daily_backtest(self):
        # برای هر استراتژی: محاسبه سیگنال D-30 → عملکرد D+1 تا D+30
        # مقایسه با buy-and-hold و benchmark بازار
        # ذخیره نتایج در ai_lessons برای یادگیری روزانه
        pass
```

---

## ۴. کیبورد و منوهای ری‌دیزاین شده

### ۴.۱ منوی اصلی (Main Menu) — محوری و пои�ی
```python
def main_menu_keyboard() -> dict:
    return {
        "inline_keyboard": [
            # ردیف ۱: گزارش‌های اصلی روزانه
            [{"text": "📊 صبحانه بازار (۰۸:۵۰)", "callback_data": "cmd:today"},
             {"text": "🌐 وضعیت لحظه‌ای", "callback_data": "cmd:market"}],
            
            # ردیف ۲: برترین/ضعیف + گروه‌ها
            [{"text": "🏆 برترین امروز", "callback_data": "cmd:top"},
             {"text": "⚠️ ضعیف‌ترین‌ها", "callback_data": "cmd:worst"}],
            [{"text": "🥇 طلا", "callback_data": "cmd:gold"},
             {"text": "💵 درآمد ثابت", "callback_data": "cmd:fixed"},
             {"text": "📈 سهامی", "callback_data": "cmd:stock"}],
            [{"text": "⚡ اهرمی", "callback_data": "cmd:leverage"},
             {"text": "🔀 مختلط", "callback_data": "cmd:mixed"}],
            
            # ردیف ۳: شخصی‌سازی
            [{"text": "📁 پرتفوی من", "callback_data": "cmd:portfolio"},
             {"text": "⭐ واچ‌لیست", "callback_data": "cmd:watchlist"}],
            [{"text": "🔍 جستجوی صندوق", "callback_data": "cmd:search_prompt"},
             {"text": "🤖 مشاور هوشمند", "callback_data": "cmd:ask"}],
            
            # ردیف ۴: تنظیمات و راهنما
            [{"text": "⚙️ پروفایل/تنظیمات", "callback_data": "cmd:profile"},
             {"text": "ℹ️ راهنما", "callback_data": "cmd:help"}],
        ]
    }
```

### ۴.۲ کیبورد گزارش صندوق (Fund Card Actions)
```python
def fund_actions_keyboard(symbol: str, fund_type: str) -> dict:
    buttons = [
        [{"text": "🔄 بروزرسانی", "callback_data": f"fund:{symbol}"},
         {"text": "⭐ واچ‌لیست", "callback_data": f"watch:{symbol}"}],
        [{"text": "➕ به سبد", "callback_data": f"pfadd:{symbol}"},
         {"text": "⚖️ مقایسه با هم‌گروه", "callback_data": f"compare:{symbol}"}],
    ]
    # دکمه‌های اختصاصی بر اساس نوع صندوق
    if fund_type == "gold":
        buttons.append([{"text": "🥇 نمودار پرمیوم/NAV", "callback_data": f"chart:{symbol}:premium"}])
    elif fund_type == "fixed_income":
        buttons.append([{"text": "💵 تحلیل بازده/مدت", "callback_data": f"chart:{symbol}:yield"}])
    elif fund_type == "leverage":
        buttons.append([{"text": "⚡ تحلیل ریسک/بازار", "callback_data": f"chart:{symbol}:beta"}])
    buttons.append([{"text": "🏠 منوی اصلی", "callback_data": "cmd:menu"}])
    return {"inline_keyboard": buttons}
```

---

## ۵. مدل داده تاریخچه تحلیلی (Analytical History)

```sql
-- migrations/010_analytical_history.sql
CREATE TABLE fund_analytical_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_id INTEGER NOT NULL,
    trade_date TEXT NOT NULL,  -- YYYY-MM-DD
    
    -- امتیازدهی روزانه
    final_score REAL,
    recommendation TEXT,  -- buy/hold/reduce/sell
    rank_position INTEGER,
    percentile REAL,
    
    -- فاکتورهای امتیازدهی (۶ فاکتور پایه)
    factor_liquidity REAL,
    factor_momentum REAL,
    factor_orderbook REAL,
    factor_moneyflow REAL,
    factor_volume_value REAL,
    factor_volatility REAL,
    
    -- متریک‌های پیشرفته (Advanced Ratios)
    sharpe REAL,
    sortino REAL,
    calmar REAL,
    omega REAL,
    information_ratio REAL,
    treynor REAL,
    jensen_alpha REAL,
    max_drawdown REAL,
    var_95 REAL,
    cvar_95 REAL,
    tail_ratio REAL,
    upside_capture REAL,
    downside_capture REAL,
    
    -- فاکتور مدل‌ها
    ff3_alpha REAL,
    ff3_beta_market REAL,
    ff3_beta_size REAL,
    ff3_beta_value REAL,
    c4_alpha REAL,
    c4_beta_momentum REAL,
    
    -- داده‌های خام برای بک‌تست
    close_price REAL,
    nav_price REAL,
    premium_discount REAL,
    volume REAL,
    value REAL,
    change_1d REAL,
    change_1w REAL,
    change_1m REAL,
    
    -- متا
    created_at TEXT DEFAULT (datetime('now')),
    
    FOREIGN KEY (fund_id) REFERENCES funds(id),
    UNIQUE(fund_id, trade_date)
);

CREATE INDEX idx_fah_fund_date ON fund_analytical_history(fund_id, trade_date DESC);
CREATE INDEX idx_fah_date_score ON fund_analytical_history(trade_date DESC, final_score DESC);
```

---

## ۶. Pipeline روزانه کامل (Daily Pipeline)

```python
# core/pipeline/daily_orchestrator.py
class DailyOrchestrator:
    """
    ارکستراسیون کامل روزانه — اجرا در cronها و رویدادهای بازار
    """
    
    SCHEDULE = {
        "08:50": "generate_market_brief",      # صبحانه بازار
        "10:00": "generate_micro_update",      # نبرد صبح
        "12:30": "generate_midday_summary",    # استراحت بازار
        "15:15": "generate_final_hour",        # ساعت آخر
        "17:10": "generate_market_close",      # بازار بسته
        "18:00": "run_backtest_and_learn",     # بک‌تست + یادگیری AI
        "00:30": "prepare_next_day",           # آماده‌سازی فردا (seedها)
    }
    
    def generate_market_brief(self):
        """۰۸:۵۰ — گزارش کامل صبحانه"""
        # 1. بارگذاری رنکینگ تازه (LocalDB → Provider)
        # 2. تفکیک به دسته‌ها (طلا، درآمد ثابت، سهامی، اهرمی، مختلط)
        # 3. محاسبه قدرت بازار، بهترین/ضعیف‌ترین گروه
        # 4. شناسایی Top 5 کلی (بدون طلا/درآمد ثابت) + Top 5 هر دسته
        # 5. اگر کاربر پرتفوی دارد → تحلیل پرتفوی
        # 6. ساخت پیام‌های چندبخشی (Layer 1/2/3) با لحن برند
        # 7. ارسال به کاربران subscribed (broadcast یا انبوه)
        
    def run_backtest_and_learn(self):
        """۱۸:۰۰ — بک‌تست استراتژی‌ها و آپدیت ai_lessons"""
        engine = BacktestEngine()
        results = engine.run_daily_backtest()
        # ذخیره در ai_lessons برای AIAdvisor یادگیری روزانه
        # آپدیت وزن‌های فاکتورها در weights.py اگر معنادار باشد
```

---

## ۷. پیام‌رسانی برند-سازگار (Brand-Compliant Messaging)

### اصول نگارش (از سند هویت برند):
| اصل | اعمال در کد |
|------|-------------|
| **User = Hero** | «شما تصمیم می‌گیرید»، «پیشنهاد من: ...»، «انتخاب با شماست» |
| **AI = Assistant** | هیچ‌گاه «بخرید»/«فروشید» — همیشه «تحلیل نشان می‌دهد...» |
| **DATA → ANALYSIS → INSIGHT** | سه لایه: ۱. نتیجه (امتیاز) ۲. دلیل (فاکتورها) ۳. جزئیات/محدودیت |
| **Trust First** | منبع داده صریح: «داده: BRS Gateway، ۰۹:۱۵» — عدم قطعیت: «پرمیوم >۳٪ = ریسک اصلاح» |
| **Iran Market First** | تقویم شمسی، ساعات بازار ایران، دسته‌بندی طلا/درآمد ثابت/اهرمی |
| **Tone** | آرام، ساده، حرفه‌ای، بدون هیجان، بدون EMOJI اضافه |
| **No Hype** | هیچ «بهترین»، «سود تضمینی»، «فرصت طلایی»، FOMO |
| **Progressive Disclosure** | Layer 1: کارت خلاصه → Layer 2: دلیل/فاکتور → Layer 3: جداول/نمودار/بک‌تست |

### قالب پیام (Message Template):
```python
def format_brand_message(title: str, layer1: str, layer2: str = "", layer3: str = "", 
                         source_note: str = "", disclaimer: str = "") -> str:
    parts = [f"📊 صندوقچی — {title}", "━" * 20]
    if source_note:
        parts.append(f"📡 {source_note}")
    parts.append("")  # خط خالی
    parts.append(layer1)  # Layer 1: نتیجه
    if layer2:
        parts.append("") 
        parts.append("🔍 دلیل و تحلیل:")
        parts.append(layer2)  # Layer 2: تحلیل
    if layer3:
        parts.append("")
        parts.append("📋 جزئیات و محدودیت‌ها:")
        parts.append(layer3)  # Layer 3: جزئیات
    if disclaimer:
        parts.append("")
        parts.append(f"⚠️ {disclaimer}")
    parts.append("")
    parts.append("شما تصمیم می‌گیرید. من فقط آگاهی می‌دهم.")
    return "\n".join(parts)
```

---

## ۸. تغییرات فایل‌های موجود (Implementation Plan)

### فایل‌های جدید:
1. `core/market/hours.py` — موتور ساعات بازار
2. `core/market/taxonomy.py` — طبقه‌بندی صندوق‌ها
3. `core/backtest/engine.py` — موتور بک‌تست
4. `core/pipeline/daily_orchestrator.py` — ارکستراسیون روزانه
5. `services/telegram/brand_messaging.py` — پیام‌سازی برند
6. `services/telegram/category_reports.py` — گزارش‌های دسته‌ای
7. `services/telegram/fund_deepdive.py` — تحلیل عمیق صندوق
8. `services/telegram/portfolio_analyzer.py` — تحلیل پرتفوی
9. `migrations/010_analytical_history.sql` — تاریخچه تحلیلی

### فایل‌های تغییر داده شده:
1. `services/telegram/keyboards.py` — منوهای جدید
2. `services/telegram_bot.py` — هندلرهای جدید، سرویس‌های جدید
3. `services/telegram/rank_loader.py` — تفکیک دسته‌ای
4. `core/pipeline/daily_analysis.py` — ذخیره در analytical_history
5. `core/scoring/score_engine.py` — محاسبه و بازگرداندن همه متریک‌ها
6. `tools/cron_*.sh` — زمان‌بندی جدید (۰۸:۵۰، ۱۰:۰۰، ۱۲:۳۰، ۱۵:۱۵، ۱۷:۱۰، ۱۸:۰۰)

---

## ۹. مثال کامل: جریان کاربر

```
[۰۸:۴۵] کاربر ربات را باز می‌کند
    ↓
[منوی اصلی] دکمه «📊 صبحانه بازار (۰۸:۵۰)»
    ↓
[Layer 1] خلاصه بازار + ۳ برترین + ۳ ضعیف + پرتفوی (اگر יש)
[Layer 2] دلیل هر کدام (یک خط)
[Layer 3] دکمه «🔍 جزئیات عیار» → تحلیل عمیق ۱۵ متریک
    ↓
[دکمه] «➕ به سبد» → ورودی تعداد/قیمت → ثبت در پرتفوی
    ↓
[دکمه] «🤖 مشاور» → چت آزاد: «این سبد برای ۱ ساله ریسک کم خوبه؟»
    ↓
[AI] تحلیل پرتفوی + پیشنهاد تخصیص + توضیح ریسک‌ها
    ↓
کاربر تصمیم می‌گیرد → اجرا در بروکر → صندوقچی فقط یادآوری/پایش می‌کند
```

---

## ۱۰. اولویت پیاده‌سازی (Phased)

| فاز | تحویل | شرح |
|-----|-------|-----|
| **Phase 1** (این هفته) | کیبورد جدید، دسته‌بندی صندوق‌ها، گزارش صبحانه ۰۸:۵۰، تحلیل گروه‌ها، fund_deepdive با advanced ratios |
| **Phase 2** (هفته بعد) | پرتفوی هوشمند (ریسک/بازار)، مشاور AI با پروفایل، بک‌تست روزانه، analytical_history table |
| **Phase 3** (هفته بعد) | Broadcast زمان‌بندی شده، میکرو‌آپدیت ۱۵ دقیقه‌ای، یادگیری AI از ai_lessons، بهینه‌سازی وزن‌ها |

---

*این سند یک مرجع حیاتی است — هر تغییر در UX باید با این اصول همسو باشد.*