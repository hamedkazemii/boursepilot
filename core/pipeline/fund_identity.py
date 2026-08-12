"""
Fund Identity Manager — تعیین هویت و نوع صندوق.

FundType باید روی انتخاب methodology تأثیر بگذارد:
- هر metric قبل از اجرا باید is_applicable(metric, fund_type) را بگذراند.
- صندوق ناشناس فقط metrics جهانی می‌گیرد.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from core.history.repository import HistoryRepository
from services.providers.brs_provider import BrsProvider
from services.providers.models import SymbolQuote

logger = logging.getLogger(__name__)


class FundType(str, Enum):
    """نوع صندوق"""
    EQUITY = "equity"                # سهامی
    FIXED_INCOME = "fixed_income"    # درآمد ثابت
    GOLD = "gold"                    # طلا
    COMMODITY = "commodity"          # کالایی
    MIXED = "mixed"                  # مختلط
    INDEX = "index"                  # شاخصی
    LEVERAGED = "leveraged"          # اهرمی
    DERIVATIVE = "derivative"        # مشتقه
    OTHER = "other"                  # سایر
    UNKNOWN = "unknown"              # نامشخص


class HistoryAvailability(str, Enum):
    """در دسترس بودن تاریخچه"""
    FULL = "full"
    PARTIAL = "partial"
    INSUFFICIENT = "insufficient"
    NONE = "none"


class AssetClass(str, Enum):
    """کلاس دارایی"""
    EQUITY = "equity"
    FIXED_INCOME = "fixed_income"
    GOLD = "gold"
    COMMODITY = "commodity"
    MIXED = "mixed"
    INDEX = "index"
    LEVERAGED = "leveraged"
    DERIVATIVE = "derivative"
    OTHER = "other"
    UNKNOWN = "unknown"


@dataclass
class FundIdentity:
    """هویت کامل یک صندوق"""
    symbol: str
    name: str = ""
    fund_type: FundType = FundType.UNKNOWN
    strategy: str = ""
    asset_class: AssetClass = AssetClass.UNKNOWN
    is_leveraged: bool = False
    is_derivative: bool = False
    is_brand_like: bool = False
    is_active: bool = True
    history_availability: HistoryAvailability = HistoryAvailability.NONE
    applicable_metrics: list[str] = field(default_factory=list)
    methodology_restrictions: list[str] = field(default_factory=list)
    universe_version: str = ""
    identified_at: datetime = field(default_factory=datetime.now)
    source: str = "DB"

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "fund_type": self.fund_type.value,
            "strategy": self.strategy,
            "asset_class": self.asset_class.value,
            "is_leveraged": self.is_leveraged,
            "is_derivative": self.is_derivative,
            "is_brand_like": self.is_brand_like,
            "is_active": self.is_active,
            "history_availability": self.history_availability.value,
            "applicable_metrics": self.applicable_metrics,
            "methodology_restrictions": self.methodology_restrictions,
            "universe_version": self.universe_version,
            "identified_at": self.identified_at.isoformat(),
            "source": self.source,
        }


# ================================================================
# Metric Applicability Matrix
# ================================================================

# Metrics: کدام fund_type ها می‌توانند این metric را داشته باشند
METRIC_APPLICABILITY = {
    # Universal metrics (all fund types)
    "price": {FundType.EQUITY, FundType.FIXED_INCOME, FundType.GOLD, FundType.COMMODITY,
              FundType.MIXED, FundType.INDEX, FundType.LEVERAGED, FundType.DERIVATIVE,
              FundType.OTHER, FundType.UNKNOWN},
    "nav": {FundType.EQUITY, FundType.FIXED_INCOME, FundType.GOLD, FundType.COMMODITY,
            FundType.MIXED, FundType.INDEX, FundType.LEVERAGED, FundType.DERIVATIVE,
            FundType.OTHER, FundType.UNKNOWN},
    "premium_discount": {FundType.EQUITY, FundType.FIXED_INCOME, FundType.GOLD, FundType.COMMODITY,
                         FundType.MIXED, FundType.INDEX, FundType.LEVERAGED, FundType.DERIVATIVE,
                         FundType.OTHER, FundType.UNKNOWN},
    "volume": {FundType.EQUITY, FundType.FIXED_INCOME, FundType.GOLD, FundType.COMMODITY,
               FundType.MIXED, FundType.INDEX, FundType.LEVERAGED, FundType.DERIVATIVE,
               FundType.OTHER, FundType.UNKNOWN},
    "value": {FundType.EQUITY, FundType.FIXED_INCOME, FundType.GOLD, FundType.COMMODITY,
              FundType.MIXED, FundType.INDEX, FundType.LEVERAGED, FundType.DERIVATIVE,
              FundType.OTHER, FundType.UNKNOWN},
    "change_pct": {FundType.EQUITY, FundType.FIXED_INCOME, FundType.GOLD, FundType.COMMODITY,
                   FundType.MIXED, FundType.INDEX, FundType.LEVERAGED, FundType.DERIVATIVE,
                   FundType.OTHER, FundType.UNKNOWN},
    "liquidity": {FundType.EQUITY, FundType.FIXED_INCOME, FundType.GOLD, FundType.COMMODITY,
                  FundType.MIXED, FundType.INDEX, FundType.LEVERAGED, FundType.DERIVATIVE,
                  FundType.OTHER, FundType.UNKNOWN},
    "money_flow": {FundType.EQUITY, FundType.GOLD, FundType.COMMODITY,
                   FundType.MIXED, FundType.INDEX, FundType.LEVERAGED, FundType.DERIVATIVE},
    "orderbook": {FundType.EQUITY, FundType.GOLD, FundType.COMMODITY,
                  FundType.MIXED, FundType.INDEX, FundType.LEVERAGED, FundType.DERIVATIVE},

    # Technical metrics
    "rsi": {FundType.EQUITY, FundType.GOLD, FundType.COMMODITY, FundType.MIXED,
            FundType.INDEX, FundType.LEVERAGED, FundType.DERIVATIVE},
    "macd": {FundType.EQUITY, FundType.GOLD, FundType.COMMODITY, FundType.MIXED,
             FundType.INDEX, FundType.LEVERAGED, FundType.DERIVATIVE},
    "ema": {FundType.EQUITY, FundType.GOLD, FundType.COMMODITY, FundType.MIXED,
            FundType.INDEX, FundType.LEVERAGED, FundType.DERIVATIVE},
    "atr": {FundType.EQUITY, FundType.GOLD, FundType.COMMODITY, FundType.MIXED,
            FundType.INDEX, FundType.LEVERAGED, FundType.DERIVATIVE},
    "bollinger": {FundType.EQUITY, FundType.GOLD, FundType.COMMODITY, FundType.MIXED,
                  FundType.INDEX, FundType.LEVERAGED, FundType.DERIVATIVE},
    "volatility": {FundType.EQUITY, FundType.GOLD, FundType.COMMODITY, FundType.MIXED,
                   FundType.INDEX, FundType.LEVERAGED, FundType.DERIVATIVE},
    "momentum": {FundType.EQUITY, FundType.GOLD, FundType.COMMODITY, FundType.MIXED,
                 FundType.INDEX, FundType.LEVERAGED, FundType.DERIVATIVE},
    "returns": {FundType.EQUITY, FundType.GOLD, FundType.COMMODITY, FundType.MIXED,
                FundType.INDEX, FundType.LEVERAGED, FundType.DERIVATIVE},
    "drawdown": {FundType.EQUITY, FundType.GOLD, FundType.COMMODITY, FundType.MIXED,
                 FundType.INDEX, FundType.LEVERAGED, FundType.DERIVATIVE},
    "sharpe": {FundType.EQUITY, FundType.GOLD, FundType.COMMODITY, FundType.MIXED,
               FundType.INDEX, FundType.LEVERAGED, FundType.DERIVATIVE},
    "sortino": {FundType.EQUITY, FundType.GOLD, FundType.COMMODITY, FundType.MIXED,
                FundType.INDEX, FundType.LEVERAGED, FundType.DERIVATIVE},

    # Fundamental metrics
    "equity_exposure": {FundType.EQUITY, FundType.MIXED},
    "sector_concentration": {FundType.EQUITY, FundType.MIXED},
    "top_holdings": {FundType.EQUITY, FundType.MIXED},
    "yield": {FundType.FIXED_INCOME},
    "duration": {FundType.FIXED_INCOME},
    "maturity": {FundType.FIXED_INCOME},
    "credit_exposure": {FundType.FIXED_INCOME},
    "interest_sensitivity": {FundType.FIXED_INCOME},
    "gold_exposure": {FundType.GOLD},
    "fx_sensitivity": {FundType.GOLD},
    "commodity_exposure": {FundType.COMMODITY},
    "tracking_behavior": {FundType.INDEX, FundType.LEVERAGED, FundType.GOLD},
    "leverage_exposure": {FundType.LEVERAGED},
    "path_dependency": {FundType.LEVERAGED, FundType.DERIVATIVE},
    "index_exposure": {FundType.INDEX},

    # Risk metrics
    "market_risk": {FundType.EQUITY, FundType.GOLD, FundType.COMMODITY, FundType.MIXED,
                    FundType.INDEX, FundType.LEVERAGED, FundType.DERIVATIVE},
    "concentration_risk": {FundType.EQUITY, FundType.MIXED, FundType.FIXED_INCOME},
    "correlation_risk": {FundType.EQUITY, FundType.GOLD, FundType.COMMODITY, FundType.MIXED,
                         FundType.INDEX, FundType.LEVERAGED, FundType.DERIVATIVE},
    "nav_risk": {FundType.EQUITY, FundType.FIXED_INCOME, FundType.GOLD, FundType.COMMODITY,
                 FundType.MIXED, FundType.INDEX, FundType.LEVERAGED, FundType.DERIVATIVE},
    "liquidity_risk": {FundType.EQUITY, FundType.FIXED_INCOME, FundType.GOLD, FundType.COMMODITY,
                       FundType.MIXED, FundType.INDEX, FundType.LEVERAGED, FundType.DERIVATIVE},

    # KODAL
    "kodal": {FundType.EQUITY, FundType.FIXED_INCOME, FundType.GOLD, FundType.COMMODITY,
              FundType.MIXED, FundType.INDEX, FundType.LEVERAGED, FundType.DERIVATIVE,
              FundType.OTHER, FundType.UNKNOWN},
}

# Metric → دسته‌بندی
METRIC_CATEGORY = {
    "price": "market", "nav": "valuation", "premium_discount": "valuation",
    "volume": "market", "value": "market", "change_pct": "market",
    "liquidity": "market", "money_flow": "microstructure", "orderbook": "microstructure",
    "rsi": "technical", "macd": "technical", "ema": "technical", "atr": "technical",
    "bollinger": "technical", "volatility": "technical", "momentum": "technical",
    "returns": "technical", "drawdown": "technical", "sharpe": "technical", "sortino": "technical",
    "equity_exposure": "fundamental", "sector_concentration": "fundamental",
    "top_holdings": "fundamental", "yield": "fundamental", "duration": "fundamental",
    "maturity": "fundamental", "credit_exposure": "fundamental",
    "interest_sensitivity": "fundamental", "gold_exposure": "fundamental",
    "fx_sensitivity": "fundamental", "commodity_exposure": "fundamental",
    "tracking_behavior": "fundamental", "leverage_exposure": "fundamental",
    "path_dependency": "fundamental", "index_exposure": "fundamental",
    "market_risk": "risk", "concentration_risk": "risk", "correlation_risk": "risk",
    "nav_risk": "risk", "liquidity_risk": "risk",
    "kodal": "kodal",
}

# Fund type → methodology restrictions
FUND_TYPE_RESTRICTIONS = {
    FundType.FIXED_INCOME: [
        "RSI/technical momentum on fixed income has limited meaning; use yield/duration lens",
    ],
    FundType.GOLD: [
        "Analysis must include gold/FX context where available",
    ],
    FundType.COMMODITY: [
        "Analysis must include commodity price context",
    ],
    FundType.LEVERAGED: [
        "Risk interpretation must be leverage-aware",
    ],
    FundType.DERIVATIVE: [
        "Risk interpretation must be derivative-aware",
    ],
    FundType.INDEX: [
        "Analysis must consider index tracking behavior",
    ],
    FundType.UNKNOWN: [
        "Only universally valid metrics applied",
    ],
}


class FundIdentityManager:
    """
    تعیین هویت صندوق و کنترل applicability روش‌شناسی.

    - fund_type را از DB fund_universe یا BRS تشخیص می‌دهد
    - هر metric باید is_applicable() را بگذراند
    - صندوق ناشناس: فقط metrics جهانی
    """

    def __init__(
        self,
        provider: Optional[BrsProvider] = None,
        repository: Optional[HistoryRepository] = None,
        history_count_threshold_full: int = 180,
        history_count_threshold_partial: int = 45,
    ):
        self.provider = provider
        self.repository = repository
        self.history_count_threshold_full = history_count_threshold_full
        self.history_count_threshold_partial = history_count_threshold_partial
        self._request_id: Optional[str] = None

    def identify(
        self,
        symbol: str,
        *,
        request_id: Optional[str] = None,
        quote: Optional[SymbolQuote] = None,
    ) -> FundIdentity:
        """
        شناسایی هویت صندوق.

        Args:
            symbol: نماد صندوق
            request_id: شناسه درخواست برای Trace
            quote: نقل‌قول اختیاری (برای تشخیص از روی BRS)

        Returns:
            FundIdentity
        """
        self._request_id = request_id or f"fi_{symbol}_{datetime.now().timestamp()}"
        logger.info(f"[{self._request_id}] FundIdentity identify: {symbol}")

        identity = FundIdentity(symbol=symbol)

        # 1. تلاش از DB fund_universe
        if self.repository:
            try:
                identity = self._identify_from_db(symbol)
                identity.source = "DB"
            except Exception as e:
                logger.debug(f"[{self._request_id}] DB identify failed: {e}")

        # 2. اگر از DB پیدا نشد، از BRS
        if identity.fund_type == FundType.UNKNOWN and self.provider:
            try:
                identity = self._identify_from_brs(symbol, quote=quote)
                identity.source = "BRS"
            except Exception as e:
                logger.debug(f"[{self._request_id}] BRS identify failed: {e}")

        # 3. بررسی تاریخچه
        identity.history_availability = self._check_history_availability(symbol)

        # 4. محاسبه applicable_metrics
        identity.applicable_metrics = self._compute_applicable_metrics(identity.fund_type)

        # 5. اعمال restrictions
        identity.methodology_restrictions = list(FUND_TYPE_RESTRICTIONS.get(identity.fund_type, []))

        logger.info(
            f"[{self._request_id}] FundIdentity result: "
            f"type={identity.fund_type.value}, "
            f"history={identity.history_availability.value}, "
            f"metrics={len(identity.applicable_metrics)}"
        )
        return identity

    def is_applicable(self, metric: str, fund_type: FundType) -> bool:
        """
        بررسی applicability یک metric برای یک fund type.

        Args:
            metric: نام metric
            fund_type: نوع صندوق

        Returns:
            True اگر metric برای این نوع صندوق معتبر است
        """
        allowed = METRIC_APPLICABILITY.get(metric)
        if allowed is None:
            return False  # metric نامشخص
        return fund_type in allowed

    def _identify_from_db(self, symbol: str) -> FundIdentity:
        """شناسایی از DB fund_universe"""
        identity = FundIdentity(symbol=symbol)

        # از fund_universe (منبع حقیقت)
        try:
            with self.repository.db.transaction() as conn:
                row = conn.execute(
                    """SELECT symbol, name, cs, cs_id, cs_sub, board, is_active, ins_code
                       FROM fund_universe
                       WHERE symbol = ? AND is_active = 1
                       LIMIT 1""",
                    (symbol,),
                ).fetchone()
        except Exception:
            row = None

        # فول‌بک: از funds (در صورت عدم موجودی در fund_universe)
        if not row:
            try:
                fund_id = self.repository.get_fund_id(symbol)
                if fund_id is not None:
                    with self.repository.db.transaction() as conn:
                        row = conn.execute(
                            """SELECT symbol, name, fund_type, sector, board, is_active
                               FROM funds WHERE id = ?""",
                            (fund_id,),
                        ).fetchone()
            except Exception:
                row = None

        # همچنین از fund_universe می‌توانیم از history استفاده کنیم
        # but for now, if the symbol is not in the current fund_universe, mark as UNKNOWN

        if not row:
            # If still no row, check if the symbol exists in symbol table as a fund-like
            try:
                if self.provider:
                    q = self.provider.get_symbol(symbol)
                    if q and q.is_fund_like:
                        row = {
                            "symbol": q.symbol,
                            "name": q.name,
                            "cs": q.sector or "",
                            "cs_id": q.sector_id or 0,
                            "cs_sub": "",
                            "board": q.board or "",
                            "is_active": True,
                            "ins_code": q.ins_code or "",
                        }
            except Exception:
                pass

        if not row:
            return identity  # UNKNOWN

        identity.name = row["name"] or ""
        identity.is_active = bool(row["is_active"]) if "is_active" in row.keys() else True
        identity.universe_version = "fund_universe"

        # تشخیص fund_type
        text = " ".join(str(x or "") for x in (
            row["symbol"],
            row.get("name", ""),
            row.get("cs", "") if "cs" in row.keys() else row.get("sector", ""),
            row.get("board", ""),
        ))
        identity.fund_type = self._classify_from_text(text)

        # پرچم‌ها
        identity.is_leveraged = identity.fund_type == FundType.LEVERAGED
        identity.is_derivative = identity.fund_type == FundType.DERIVATIVE
        identity.is_brand_like = False

        # asset_class
        identity.asset_class = self._asset_class_for(identity.fund_type)

        # strategy
        identity.strategy = self._strategy_for(identity.fund_type)

        return identity

    def _identify_from_brs(self, symbol: str, quote: Optional[SymbolQuote] = None) -> FundIdentity:
        """شناسایی از BRS"""
        identity = FundIdentity(symbol=symbol)
        try:
            if quote is None:
                quote = self.provider.get_symbol(symbol)
            if quote:
                identity.name = quote.name or ""
                identity.fund_type = self._classify_from_text(
                    " ".join(str(x or "") for x in (symbol, quote.name, quote.sector, quote.board))
                )
                identity.is_brand_like = bool(quote.is_fund_like)
                identity.is_leveraged = identity.fund_type == FundType.LEVERAGED
                identity.is_derivative = identity.fund_type == FundType.DERIVATIVE
                identity.asset_class = self._asset_class_for(identity.fund_type)
                identity.strategy = self._strategy_for(identity.fund_type)
                identity.is_active = True
        except Exception as e:
            logger.debug(f"[{self._request_id}] BRS identify error: {e}")
        return identity

    def _classify_from_text(self, text: str) -> FundType:
        """طبقه‌بندی نوع صندوق از متن"""
        from services.providers.textnorm import normalize_fa
        t = normalize_fa(text)

        rules = [
            ("اهرم", FundType.LEVERAGED),
            ("اهرمی", FundType.LEVERAGED),
            ("طلا", FundType.GOLD),
            ("زر", FundType.GOLD),
            ("درآمد ثابت", FundType.FIXED_INCOME),
            ("درآمدثابت", FundType.FIXED_INCOME),
            ("ثابت", FundType.FIXED_INCOME),
            ("کالایی", FundType.COMMODITY),
            ("کالا", FundType.COMMODITY),
            ("زعفران", FundType.COMMODITY),
            ("نقره", FundType.COMMODITY),
            ("شاخصی", FundType.INDEX),
            ("شاخص", FundType.INDEX),
            ("مختلط", FundType.MIXED),
            ("سهامی", FundType.EQUITY),
            ("سهام", FundType.EQUITY),
            ("مشتقه", FundType.DERIVATIVE),
            ("اختیار", FundType.DERIVATIVE),
        ]
        for key, ftype in rules:
            if key in t:
                return ftype
        return FundType.UNKNOWN

    def _asset_class_for(self, fund_type: FundType) -> AssetClass:
        """نگاشت fund_type به asset_class"""
        mapping = {
            FundType.EQUITY: AssetClass.EQUITY,
            FundType.FIXED_INCOME: AssetClass.FIXED_INCOME,
            FundType.GOLD: AssetClass.GOLD,
            FundType.COMMODITY: AssetClass.COMMODITY,
            FundType.MIXED: AssetClass.MIXED,
            FundType.INDEX: AssetClass.INDEX,
            FundType.LEVERAGED: AssetClass.LEVERAGED,
            FundType.DERIVATIVE: AssetClass.DERIVATIVE,
            FundType.OTHER: AssetClass.OTHER,
            FundType.UNKNOWN: AssetClass.UNKNOWN,
        }
        return mapping.get(fund_type, AssetClass.UNKNOWN)

    def _strategy_for(self, fund_type: FundType) -> str:
        """توضیح استراتژی برای هر نوع صندوق"""
        strategies = {
            FundType.EQUITY: "سرمایه‌گذاری در سهام",
            FundType.FIXED_INCOME: "سرمایه‌گذاری در اوراق با درآمد ثابت",
            FundType.GOLD: "سرمایه‌گذاری در طلا",
            FundType.COMMODITY: "سرمایه‌گذاری در کالا",
            FundType.MIXED: "سرمایه‌گذاری ترکیبی (سهام + اوراق)",
            FundType.INDEX: "پیروی از شاخص",
            FundType.LEVERAGED: "اهرمی (بازده چند برابر بازار)",
            FundType.DERIVATIVE: "مشتقه",
            FundType.OTHER: "سایر",
            FundType.UNKNOWN: "نامشخص",
        }
        return strategies.get(fund_type, "")

    def _check_history_availability(self, symbol: str) -> HistoryAvailability:
        """بررسی در دسترس بودن تاریخچه"""
        if not self.repository:
            return HistoryAvailability.NONE

        try:
            fund_id = self.repository.get_fund_id(symbol)
            if fund_id is None:
                return HistoryAvailability.NONE

            with self.repository.db.transaction() as conn:
                row = conn.execute(
                    "SELECT COUNT(*) as cnt FROM history WHERE fund_id = ?",
                    (fund_id,),
                ).fetchone()

            count = int(row["cnt"]) if row else 0

            if count >= self.history_count_threshold_full:
                return HistoryAvailability.FULL
            elif count >= self.history_count_threshold_partial:
                return HistoryAvailability.PARTIAL
            elif count > 0:
                return HistoryAvailability.INSUFFICIENT
            return HistoryAvailability.NONE
        except Exception:
            return HistoryAvailability.NONE

    def _compute_applicable_metrics(self, fund_type: FundType) -> list[str]:
        """محاسبه لیست metrics قابل اجرا برای fund type"""
        metrics = []
        for metric, allowed_types in METRIC_APPLICABILITY.items():
            if fund_type in allowed_types:
                metrics.append(metric)
        return sorted(metrics)


# ================================================================
# Convenience Functions
# ================================================================

def create_fund_identity_manager(
    provider: Optional[BrsProvider] = None,
    repository: Optional[HistoryRepository] = None,
) -> FundIdentityManager:
    """ساخت FundIdentityManager با dependency injection"""
    return FundIdentityManager(provider=provider, repository=repository)