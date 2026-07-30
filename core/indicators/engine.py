"""Indicator Engine — محاسبه سری‌زمانی از history."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any, Optional, Sequence


@dataclass
class IndicatorSnapshot:
    as_of_date: str = ""
    ret_1d: Optional[float] = None
    ret_5d: Optional[float] = None
    ret_20d: Optional[float] = None
    ret_60d: Optional[float] = None
    ret_90d: Optional[float] = None
    ema20: Optional[float] = None
    ema50: Optional[float] = None
    ema200: Optional[float] = None
    rsi14: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    atr14: Optional[float] = None
    bb_upper: Optional[float] = None
    bb_mid: Optional[float] = None
    bb_lower: Optional[float] = None
    volatility_20: Optional[float] = None
    sharpe_60: Optional[float] = None
    sortino_60: Optional[float] = None
    max_drawdown_90: Optional[float] = None
    avg_volume_20: Optional[float] = None
    volume_ratio: Optional[float] = None
    bars: int = 0
    extras: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


class IndicatorEngine:
    """محاسبه اندیکاتور از لیست ردیف‌های history (مرتب از قدیم→جدید)."""

    def compute(self, rows: Sequence[dict[str, Any]]) -> IndicatorSnapshot:
        if not rows:
            return IndicatorSnapshot()
        closes = [_f(r.get("close_price") if r.get("close_price") is not None else r.get("last_price")) for r in rows]
        highs = [_f(r.get("high_price")) for r in rows]
        lows = [_f(r.get("low_price")) for r in rows]
        vols = [_f(r.get("volume")) for r in rows]
        dates = [str(r.get("trade_date") or "") for r in rows]

        # drop leading Nones in close
        pairs = [(c, h, l, v, d) for c, h, l, v, d in zip(closes, highs, lows, vols, dates) if c is not None]
        if not pairs:
            return IndicatorSnapshot(bars=0)
        closes = [p[0] for p in pairs]
        highs = [p[1] if p[1] is not None else p[0] for p in pairs]
        lows = [p[2] if p[2] is not None else p[0] for p in pairs]
        vols = [p[3] for p in pairs]
        dates = [p[4] for p in pairs]
        n = len(closes)
        last = closes[-1]
        snap = IndicatorSnapshot(as_of_date=dates[-1], bars=n)

        snap.ret_1d = _ret(closes, 1)
        snap.ret_5d = _ret(closes, 5)
        snap.ret_20d = _ret(closes, 20)
        snap.ret_60d = _ret(closes, 60)
        snap.ret_90d = _ret(closes, 90)

        snap.ema20 = _ema(closes, 20)
        snap.ema50 = _ema(closes, 50)
        snap.ema200 = _ema(closes, 200)
        snap.rsi14 = _rsi(closes, 14)
        macd, signal = _macd(closes)
        snap.macd = macd
        snap.macd_signal = signal
        snap.atr14 = _atr(highs, lows, closes, 14)
        mid, up, low = _bollinger(closes, 20, 2.0)
        snap.bb_mid, snap.bb_upper, snap.bb_lower = mid, up, low
        snap.volatility_20 = _volatility(closes, 20)
        snap.sharpe_60 = _sharpe(closes, 60)
        snap.sortino_60 = _sortino(closes, 60)
        snap.max_drawdown_90 = _max_drawdown(closes[-90:] if n >= 2 else closes)

        vol_valid = [v for v in vols[-20:] if v is not None and v > 0]
        if vol_valid:
            snap.avg_volume_20 = sum(vol_valid) / len(vol_valid)
            last_v = vols[-1]
            if last_v is not None and snap.avg_volume_20:
                snap.volume_ratio = last_v / snap.avg_volume_20

        # trend regime extras
        snap.extras = {
            "price": last,
            "above_ema20": (snap.ema20 is not None and last > snap.ema20),
            "above_ema50": (snap.ema50 is not None and last > snap.ema50),
            "above_ema200": (snap.ema200 is not None and last > snap.ema200),
            "macd_hist": (macd - signal) if macd is not None and signal is not None else None,
        }
        return snap


def _f(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        x = float(v)
        if math.isnan(x) or math.isinf(x):
            return None
        return x
    except Exception:
        return None


def _ret(closes: list[float], days: int) -> Optional[float]:
    if len(closes) <= days or closes[-1 - days] == 0:
        return None
    return (closes[-1] / closes[-1 - days] - 1.0) * 100.0


def _ema(values: list[float], period: int) -> Optional[float]:
    if len(values) < period:
        return None
    k = 2 / (period + 1)
    ema = sum(values[:period]) / period
    for x in values[period:]:
        ema = x * k + ema * (1 - k)
    return ema


def _sma(values: list[float], period: int) -> Optional[float]:
    if len(values) < period:
        return None
    window = values[-period:]
    return sum(window) / period


def _rsi(closes: list[float], period: int = 14) -> Optional[float]:
    if len(closes) <= period:
        return None
    gains = []
    losses = []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i - 1]
        gains.append(max(d, 0.0))
        losses.append(max(-d, 0.0))
    # Wilder
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _macd(closes: list[float]) -> tuple[Optional[float], Optional[float]]:
    if len(closes) < 35:
        return None, None
    # compute EMA series
    def ema_series(period: int) -> list[float]:
        k = 2 / (period + 1)
        out = []
        ema = sum(closes[:period]) / period
        out.extend([None] * (period - 1))  # type: ignore
        out.append(ema)
        for x in closes[period:]:
            ema = x * k + ema * (1 - k)
            out.append(ema)
        return out  # type: ignore

    e12 = ema_series(12)
    e26 = ema_series(26)
    macd_line = []
    for a, b in zip(e12, e26):
        if a is None or b is None:
            macd_line.append(None)
        else:
            macd_line.append(a - b)
    # signal = ema9 of macd
    vals = [x for x in macd_line if x is not None]
    if len(vals) < 9:
        return macd_line[-1], None
    k = 2 / 10
    sig = sum(vals[:9]) / 9
    for x in vals[9:]:
        sig = x * k + sig * (1 - k)
    return vals[-1], sig


def _atr(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> Optional[float]:
    if len(closes) <= period:
        return None
    trs = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        trs.append(tr)
    if len(trs) < period:
        return None
    atr = sum(trs[:period]) / period
    for x in trs[period:]:
        atr = (atr * (period - 1) + x) / period
    return atr


def _bollinger(closes: list[float], period: int = 20, nstd: float = 2.0) -> tuple[Optional[float], Optional[float], Optional[float]]:
    if len(closes) < period:
        return None, None, None
    window = closes[-period:]
    mid = sum(window) / period
    var = sum((x - mid) ** 2 for x in window) / period
    sd = math.sqrt(var)
    return mid, mid + nstd * sd, mid - nstd * sd


def _daily_returns(closes: list[float]) -> list[float]:
    out = []
    for i in range(1, len(closes)):
        if closes[i - 1]:
            out.append(closes[i] / closes[i - 1] - 1.0)
    return out


def _volatility(closes: list[float], period: int = 20) -> Optional[float]:
    rets = _daily_returns(closes[-(period + 1) :])
    if len(rets) < max(5, period // 2):
        return None
    m = sum(rets) / len(rets)
    var = sum((r - m) ** 2 for r in rets) / len(rets)
    return math.sqrt(var) * math.sqrt(252) * 100.0  # annualized %


def _sharpe(closes: list[float], period: int = 60) -> Optional[float]:
    rets = _daily_returns(closes[-(period + 1) :])
    if len(rets) < 10:
        return None
    m = sum(rets) / len(rets)
    var = sum((r - m) ** 2 for r in rets) / len(rets)
    sd = math.sqrt(var)
    if sd == 0:
        return None
    return (m * 252) / (sd * math.sqrt(252))


def _sortino(closes: list[float], period: int = 60) -> Optional[float]:
    rets = _daily_returns(closes[-(period + 1) :])
    if len(rets) < 10:
        return None
    m = sum(rets) / len(rets)
    downside = [r for r in rets if r < 0]
    if not downside:
        return 3.0 if m > 0 else 0.0
    dvar = sum(r * r for r in downside) / len(downside)
    dsd = math.sqrt(dvar)
    if dsd == 0:
        return None
    return (m * 252) / (dsd * math.sqrt(252))


def _max_drawdown(closes: list[float]) -> Optional[float]:
    if len(closes) < 2:
        return None
    peak = closes[0]
    max_dd = 0.0
    for c in closes:
        peak = max(peak, c)
        if peak > 0:
            dd = c / peak - 1.0
            max_dd = min(max_dd, dd)
    return max_dd * 100.0
