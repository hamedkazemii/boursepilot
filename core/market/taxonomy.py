"""طبقه‌بندی صندوق‌ها (Fund Taxonomy) — بر اساس واقعیت بازار ایران."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class FundCategory(str, Enum):
    GOLD = "gold"               # طلا و کالایی
    FIXED_INCOME = "fixed_income"  # درآمد ثابت
    EQUITY = "equity"           # سهامی
    LEVERAGE = "leverage"       # اهرمی
    MIXED = "mixed"             # مختلط


@dataclass(frozen=True)
class CategoryConfig:
    key: FundCategory
    label: str
    emoji: str
    session_key: str  # pre_open, morning, midday, afternoon, gold_24h
    analysis_mode: str
    exclude_from_general_top5: bool = False
    separate_reporting: bool = False
    typical_metrics: list[str] = field(default_factory=list)
    risk_profile: str = "medium"  # low, medium, high
    examples: list[str] = field(default_factory=list)


CATEGORY_CONFIGS: dict[FundCategory, CategoryConfig] = {
    FundCategory.GOLD: CategoryConfig(
        key=FundCategory.GOLD,
        label="طلا و کالایی",
        emoji="🥇",
        session_key="gold_24h",
        analysis_mode="nav_premium_tracking",
        exclude_from_general_top5=True,
        separate_reporting=True,
        typical_metrics=["premium_discount", "nav_change", "volume", "spread", "gold_correlation"],
        risk_profile="medium",
        examples=["عیار", "مثقال", "طلا", "کالای کهربا", "کالای پارسیان", "گهر", "طلای سبز"],
    ),
    FundCategory.FIXED_INCOME: CategoryConfig(
        key=FundCategory.FIXED_INCOME,
        label="درآمد ثابت",
        emoji="💵",
        session_key="midday",
        analysis_mode="yield_duration_credit",
        exclude_from_general_top5=True,
        separate_reporting=True,
        typical_metrics=["yield_to_maturity", "duration", "credit_quality", "nav_stability", "distribution_yield"],
        risk_profile="low",
        examples=["کارین", "صبا", "ایمن", "پایدار", "آینده", "آروین", "مهر", "ثبات"],
    ),
    FundCategory.EQUITY: CategoryConfig(
        key=FundCategory.EQUITY,
        label="سهامی",
        emoji="📈",
        session_key="morning",
        analysis_mode="momentum_quality_value",
        exclude_from_general_top5=False,
        separate_reporting=False,
        typical_metrics=["momentum", "quality_score", "value_score", "volume_trend", "earnings_growth"],
        risk_profile="medium",
        examples=["هما", "بذر", "خورشید", "سرو", "آگاس", "رشد", "فناور", "پارس"],
    ),
    FundCategory.LEVERAGE: CategoryConfig(
        key=FundCategory.LEVERAGE,
        label="اهرمی",
        emoji="⚡",
        session_key="morning",
        analysis_mode="leverage_risk_adjusted",
        exclude_from_general_top5=False,
        separate_reporting=False,
        typical_metrics=["beta", "leverage_ratio", "volatility", "max_drawdown", "sortino"],
        risk_profile="high",
        examples=["اهرم", "موج", "توان", "لبخند", "افران", "برق", "طوفان"],
    ),
    FundCategory.MIXED: CategoryConfig(
        key=FundCategory.MIXED,
        label="مختلط",
        emoji="🔀",
        session_key="morning",
        analysis_mode="balanced_allocation",
        exclude_from_general_top5=False,
        separate_reporting=False,
        typical_metrics=["asset_allocation", "sharpe", "diversification", "correlation"],
        risk_profile="medium",
        examples=["الماس", "پارسیان مختلط", "ملی مختلط"],
    ),
}


# نگاشت کلمات کلیدی نام صندوق به دسته (برای Clasificación خودکار)
CATEGORY_KEYWORDS: dict[FundCategory, list[str]] = {
    FundCategory.GOLD: [
        "طلا", "عیار", "مثقال", "کالایی", "کهربا", "گهر", "سبز", "زرد", "طلای",
    ],
    FundCategory.FIXED_INCOME: [
        "درآمد", "ثابت", "پایدار", "آینده", "آروین", "مهر", "ثبات", "سود", "بازده",
        "کوتاه", "متوسط", "بلند", "اعتبار", "سرمایه", "ثبات",
    ],
    FundCategory.LEVERAGE: [
        "اهرم", "موج", "توان", "لبخند", "افران", "برق", "طوفان", "شتاب", "قدرت",
        "lever", "اهرمی",
    ],
    FundCategory.MIXED: [
        "مختلط", "متعادل", "تنوع", "balanced", "mixed",
    ],
}


def classify_fund_category(name: str, symbol: str = "") -> FundCategory:
    """
    دسته‌بندی خودکار صندوق بر اساس نام و نماد.
    اولویت: طلا > درآمد ثابت > اهرمی > مختلط > سهامی (پیش‌فرض)
    """
    text = f"{name} {symbol}".lower()
    
    # بررسی اولویت‌بندی شده
    for cat in [FundCategory.GOLD, FundCategory.FIXED_INCOME, FundCategory.LEVERAGE, FundCategory.MIXED]:
        for kw in CATEGORY_KEYWORDS[cat]:
            if kw in text:
                return cat
    
    return FundCategory.EQUITY  # پیش‌فرض


def get_category_config(category: FundCategory | str) -> CategoryConfig:
    if isinstance(category, str):
        category = FundCategory(category)
    return CATEGORY_CONFIGS[category]


def get_all_categories() -> list[CategoryConfig]:
    return list(CATEGORY_CONFIGS.values())


def get_reportable_categories(exclude_special: bool = False) -> list[CategoryConfig]:
    """دسته‌های قابل گزارش در رنکینگ کلی."""
    cats = list(CATEGORY_CONFIGS.values())
    if exclude_special:
        cats = [c for c in cats if not c.exclude_from_general_top5]
    return cats