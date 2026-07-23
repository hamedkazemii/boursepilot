"""
نگاشت پاسخ خام BRS به DTOهای استاندارد صندوقچی.
"""

from __future__ import annotations

from typing import Any, Optional

from services.providers.models import (MoneyFlowSnapshot, NavData,
                                       OrderBookLevel, OrderBookSnapshot,
                                       ShareholderRow, SymbolQuote)
from services.providers.textnorm import normalize_fa, normalize_symbol


def _num(value: Any, default: Optional[float] = None) -> Optional[float]:
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "")
    if not text or text.lower() in {"none", "null", "-"}:
        return default
    try:
        return float(text)
    except ValueError:
        return default


def _int(value: Any, default: int = 0) -> int:
    number = _num(value, default=float(default))
    if number is None:
        return default
    return int(number)


def is_fund_like(payload: dict[str, Any]) -> bool:
    """تشخیص صندوق‌مانند از روی sector/name/board."""
    blob = " ".join(
        str(payload.get(k, "") or "")
        for k in ("cs", "l30", "l18", "m_board", "cs_sub", "sector")
    )
    blob = normalize_fa(blob)
    keywords = (
        "صندوق",
        "ETF",
        "etf",
        "قابل معامله",
    )
    return any(k.lower() in blob.lower() if k.isascii() else k in blob for k in keywords)


def map_orderbook(payload: dict[str, Any]) -> OrderBookSnapshot:
    """ساخت عمق ۵ سطحی از فیلدهای pd/qd/zd و po/qo/zo."""
    bids: list[OrderBookLevel] = []
    asks: list[OrderBookLevel] = []

    for level in range(1, 6):
        bid_price = _num(payload.get(f"pd{level}"), 0.0) or 0.0
        bid_qty = _num(payload.get(f"qd{level}"), 0.0) or 0.0
        bid_cnt = _int(payload.get(f"zd{level}"), 0)
        ask_price = _num(payload.get(f"po{level}"), 0.0) or 0.0
        ask_qty = _num(payload.get(f"qo{level}"), 0.0) or 0.0
        ask_cnt = _int(payload.get(f"zo{level}"), 0)

        # سطح خالی را نگه می‌داریم فقط اگر قیمت/حجم داشته باشد
        if bid_price or bid_qty or bid_cnt:
            bids.append(
                OrderBookLevel(
                    side="bid",
                    level=level,
                    price=bid_price,
                    quantity=bid_qty,
                    order_count=bid_cnt,
                )
            )
        if ask_price or ask_qty or ask_cnt:
            asks.append(
                OrderBookLevel(
                    side="ask",
                    level=level,
                    price=ask_price,
                    quantity=ask_qty,
                    order_count=ask_cnt,
                )
            )

    return OrderBookSnapshot(bids=tuple(bids), asks=tuple(asks))


def map_money_flow(payload: dict[str, Any]) -> MoneyFlowSnapshot:
    return MoneyFlowSnapshot(
        buy_real_count=_int(payload.get("Buy_CountI"), 0),
        buy_legal_count=_int(payload.get("Buy_CountN"), 0),
        sell_real_count=_int(payload.get("Sell_CountI"), 0),
        sell_legal_count=_int(payload.get("Sell_CountN"), 0),
        buy_real_volume=_num(payload.get("Buy_I_Volume"), 0.0) or 0.0,
        buy_legal_volume=_num(payload.get("Buy_N_Volume"), 0.0) or 0.0,
        sell_real_volume=_num(payload.get("Sell_I_Volume"), 0.0) or 0.0,
        sell_legal_volume=_num(payload.get("Sell_N_Volume"), 0.0) or 0.0,
    )


def map_symbol_quote(payload: dict[str, Any]) -> SymbolQuote:
    """AllSymbols / Symbol.php → SymbolQuote."""
    if not isinstance(payload, dict):
        raise TypeError("payload must be dict")

    symbol = normalize_symbol(str(payload.get("l18") or payload.get("symbol") or ""))
    name = normalize_fa(str(payload.get("l30") or payload.get("name") or symbol))
    ins = payload.get("id")
    ins_code = "" if ins is None else str(ins)

    return SymbolQuote(
        symbol=symbol,
        name=name,
        ins_code=ins_code,
        isin=(str(payload["isin"]) if payload.get("isin") not in (None, "") else None),
        sector=normalize_fa(str(payload.get("cs") or "")) or None,
        sector_id=_int(payload.get("cs_id"), 0) or None,
        board=normalize_fa(str(payload.get("m_board") or payload.get("m") or "")) or None,
        state=normalize_fa(str(payload.get("state") or "")) or None,
        last_price=_num(payload.get("pl")),
        close_price=_num(payload.get("pc")),
        yesterday_price=_num(payload.get("py")),
        open_price=_num(payload.get("pf")),
        change_last=_num(payload.get("plc")),
        change_last_pct=_num(payload.get("plp")),
        change_close=_num(payload.get("pcc")),
        change_close_pct=_num(payload.get("pcp")),
        volume=_num(payload.get("tvol")),
        value=_num(payload.get("tval")),
        trade_count=_int(payload.get("tno"), 0) if payload.get("tno") is not None else None,
        avg_volume_1m=_num(payload.get("tvol_avg_1m")),
        low=_num(payload.get("pmin")),
        high=_num(payload.get("pmax")),
        threshold_min=_num(payload.get("tmin")),
        threshold_max=_num(payload.get("tmax")),
        market_value=_num(payload.get("mv")),
        shares=_num(payload.get("z")),
        time=str(payload.get("time") or "") or None,
        date=str(payload.get("date") or payload.get("date_update") or "") or None,
        orderbook=map_orderbook(payload),
        money_flow=map_money_flow(payload),
        is_fund_like=is_fund_like(payload),
        raw=dict(payload),
    )


def map_nav(symbol: str, payload: dict[str, Any]) -> NavData:
    if not isinstance(payload, dict):
        raise TypeError("NAV payload must be dict")
    return NavData(
        symbol=normalize_symbol(symbol),
        issue_nav=_num(payload.get("psubtran")),
        redeem_nav=_num(payload.get("predtran")),
        date=str(payload.get("date") or "") or None,
        time=str(payload.get("time") or "") or None,
        raw=dict(payload),
    )


def map_shareholders(payload: Any) -> list[ShareholderRow]:
    if payload is None:
        return []
    if isinstance(payload, dict):
        # بعضی پاسخ‌ها ممکن است wrapper داشته باشند
        if "data" in payload and isinstance(payload["data"], list):
            rows = payload["data"]
        else:
            rows = [payload]
    elif isinstance(payload, list):
        rows = payload
    else:
        return []

    result: list[ShareholderRow] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        result.append(
            ShareholderRow(
                name=normalize_fa(str(row.get("name") or "")),
                volume=_num(row.get("volume"), 0.0) or 0.0,
                percent=_num(row.get("percent"), 0.0) or 0.0,
                change=_num(row.get("change"), 0.0) or 0.0,
                shareholder_id=_int(row.get("id"), 0) or None,
            )
        )
    return result
