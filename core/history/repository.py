"""دسترسی داده به جداول history / funds / nav / scores."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Iterable, Optional

from core.database.connection import Database
from core.scoring.models import FundAssessment
from services.providers.models import NavData, SymbolQuote


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _trade_date_from_quote(q: SymbolQuote) -> str:
    if q.date:
        # ممکن است 1403/xx یا 2026-07-23 باشد — همان را نگه می‌داریم
        return str(q.date).strip()[:32]
    return datetime.now().astimezone().date().isoformat()


class HistoryRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    # ------------------------------------------------------------------ funds
    def upsert_fund(
        self,
        *,
        symbol: str,
        name: str = "",
        ins_code: str = "",
        isin: Optional[str] = None,
        fund_type: str = "",
        sector: Optional[str] = None,
        sector_id: Optional[int] = None,
        board: Optional[str] = None,
    ) -> int:
        now = _now_iso()
        with self.db.transaction() as conn:
            row = conn.execute(
                "SELECT id, first_seen_at FROM funds WHERE symbol = ?",
                (symbol,),
            ).fetchone()
            if row:
                conn.execute(
                    """
                    UPDATE funds SET
                        name = COALESCE(NULLIF(?, ''), name),
                        ins_code = COALESCE(NULLIF(?, ''), ins_code),
                        isin = COALESCE(?, isin),
                        fund_type = COALESCE(NULLIF(?, ''), fund_type),
                        sector = COALESCE(?, sector),
                        sector_id = COALESCE(?, sector_id),
                        board = COALESCE(?, board),
                        is_active = 1,
                        last_seen_at = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        name,
                        ins_code,
                        isin,
                        fund_type,
                        sector,
                        sector_id,
                        board,
                        now,
                        now,
                        row["id"],
                    ),
                )
                return int(row["id"])

            cur = conn.execute(
                """
                INSERT INTO funds(
                    symbol, name, ins_code, isin, fund_type, sector, sector_id,
                    board, is_active, first_seen_at, last_seen_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
                """,
                (
                    symbol,
                    name,
                    ins_code,
                    isin,
                    fund_type,
                    sector,
                    sector_id,
                    board,
                    now,
                    now,
                    now,
                ),
            )
            return int(cur.lastrowid)

    def get_fund_id(self, symbol: str) -> Optional[int]:
        row = self.db.fetchone("SELECT id FROM funds WHERE symbol = ?", (symbol,))
        return int(row["id"]) if row else None

    def list_funds(self, active_only: bool = True) -> list[dict[str, Any]]:
        sql = "SELECT * FROM funds"
        if active_only:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY symbol"
        return [dict(r) for r in self.db.fetchall(sql)]

    # ---------------------------------------------------------------- history
    def upsert_history_from_quote(
        self,
        quote: SymbolQuote,
        *,
        fund_type: str = "",
        source: str = "brs",
    ) -> tuple[int, bool]:
        """
        ذخیره/به‌روزرسانی یک ردیف روزانه.
        Returns: (fund_id, inserted_new)
        """
        fund_id = self.upsert_fund(
            symbol=quote.symbol,
            name=quote.name or "",
            ins_code=quote.ins_code or "",
            isin=quote.isin,
            fund_type=fund_type,
            sector=quote.sector,
            sector_id=quote.sector_id,
            board=quote.board,
        )
        trade_date = _trade_date_from_quote(quote)
        now = _now_iso()
        bid_qty = quote.orderbook.total_bid_quantity if quote.orderbook else None
        ask_qty = quote.orderbook.total_ask_quantity if quote.orderbook else None
        mf = quote.money_flow

        with self.db.transaction() as conn:
            existing = conn.execute(
                "SELECT id FROM history WHERE fund_id = ? AND trade_date = ?",
                (fund_id, trade_date),
            ).fetchone()
            params = (
                quote.open_price,
                quote.high,
                quote.low,
                quote.close_price,
                quote.last_price,
                quote.yesterday_price,
                quote.volume,
                quote.value,
                quote.trade_count,
                quote.change_close_pct if quote.change_close_pct is not None else quote.change_last_pct,
                bid_qty,
                ask_qty,
                mf.buy_real_volume if mf else None,
                mf.sell_real_volume if mf else None,
                mf.buy_legal_volume if mf else None,
                mf.sell_legal_volume if mf else None,
                source,
            )
            if existing:
                conn.execute(
                    """
                    UPDATE history SET
                        open_price=?, high_price=?, low_price=?, close_price=?,
                        last_price=?, yesterday_price=?, volume=?, value=?,
                        trade_count=?, change_pct=?, bid_qty=?, ask_qty=?,
                        buy_real_volume=?, sell_real_volume=?,
                        buy_legal_volume=?, sell_legal_volume=?, source=?
                    WHERE id=?
                    """,
                    params + (int(existing["id"]),),
                )
                return fund_id, False

            conn.execute(
                """
                INSERT INTO history(
                    fund_id, trade_date, open_price, high_price, low_price,
                    close_price, last_price, yesterday_price, volume, value,
                    trade_count, change_pct, bid_qty, ask_qty,
                    buy_real_volume, sell_real_volume, buy_legal_volume,
                    sell_legal_volume, source, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (fund_id, trade_date) + params + (now,),
            )
            return fund_id, True

    def get_history(
        self,
        symbol: str,
        *,
        limit: int = 200,
        since: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        fund_id = self.get_fund_id(symbol)
        if fund_id is None:
            return []
        if since:
            rows = self.db.fetchall(
                """
                SELECT h.*, f.symbol FROM history h
                JOIN funds f ON f.id = h.fund_id
                WHERE h.fund_id = ? AND h.trade_date >= ?
                ORDER BY h.trade_date ASC
                LIMIT ?
                """,
                (fund_id, since, limit),
            )
        else:
            rows = self.db.fetchall(
                """
                SELECT * FROM (
                    SELECT h.*, f.symbol FROM history h
                    JOIN funds f ON f.id = h.fund_id
                    WHERE h.fund_id = ?
                    ORDER BY h.trade_date DESC
                    LIMIT ?
                ) t ORDER BY trade_date ASC
                """,
                (fund_id, limit),
            )
        return [dict(r) for r in rows]

    def latest_trade_date(self, symbol: Optional[str] = None) -> Optional[str]:
        if symbol:
            fund_id = self.get_fund_id(symbol)
            if fund_id is None:
                return None
            row = self.db.fetchone(
                "SELECT MAX(trade_date) AS d FROM history WHERE fund_id = ?",
                (fund_id,),
            )
        else:
            row = self.db.fetchone("SELECT MAX(trade_date) AS d FROM history")
        return row["d"] if row and row["d"] else None

    def history_count(self, symbol: Optional[str] = None) -> int:
        if symbol:
            fund_id = self.get_fund_id(symbol)
            if fund_id is None:
                return 0
            row = self.db.fetchone(
                "SELECT COUNT(*) AS c FROM history WHERE fund_id = ?",
                (fund_id,),
            )
        else:
            row = self.db.fetchone("SELECT COUNT(*) AS c FROM history")
        return int(row["c"]) if row else 0

    # ------------------------------------------------------------------- nav
    def upsert_nav(
        self,
        symbol: str,
        nav: NavData,
        *,
        market_price: Optional[float] = None,
        premium_pct: Optional[float] = None,
        source: str = "brs",
    ) -> bool:
        fund_id = self.get_fund_id(symbol)
        if fund_id is None:
            fund_id = self.upsert_fund(symbol=symbol, name=symbol)
        nav_date = (nav.date or datetime.now().astimezone().date().isoformat())[:32]
        now = _now_iso()
        if premium_pct is None and market_price and nav.redeem_nav:
            try:
                premium_pct = (float(market_price) - float(nav.redeem_nav)) / float(nav.redeem_nav) * 100.0
            except Exception:
                premium_pct = None

        with self.db.transaction() as conn:
            existing = conn.execute(
                "SELECT id FROM nav_history WHERE fund_id = ? AND nav_date = ?",
                (fund_id, nav_date),
            ).fetchone()
            if existing:
                conn.execute(
                    """
                    UPDATE nav_history SET
                        issue_nav=?, redeem_nav=?, premium_pct=?, market_price=?, source=?
                    WHERE id=?
                    """,
                    (
                        nav.issue_nav,
                        nav.redeem_nav,
                        premium_pct,
                        market_price,
                        source,
                        int(existing["id"]),
                    ),
                )
                return False
            conn.execute(
                """
                INSERT INTO nav_history(
                    fund_id, nav_date, issue_nav, redeem_nav, premium_pct,
                    market_price, source, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fund_id,
                    nav_date,
                    nav.issue_nav,
                    nav.redeem_nav,
                    premium_pct,
                    market_price,
                    source,
                    now,
                ),
            )
            return True

    # ----------------------------------------------------------- daily scores
    def upsert_daily_score(self, assessment: FundAssessment, score_date: str) -> None:
        fund_id = self.get_fund_id(assessment.symbol)
        if fund_id is None:
            fund_id = self.upsert_fund(
                symbol=assessment.symbol,
                name=assessment.name,
                ins_code=assessment.ins_code,
                fund_type=assessment.fund_type,
                sector=assessment.sector,
            )
        factor_map = {f.key: f.score for f in assessment.factors}
        now = _now_iso()
        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO daily_scores(
                    fund_id, score_date, final_score, rank, recommendation,
                    recommendation_label, trend_score, liquidity_score, risk_score,
                    money_flow_score, nav_score, volume_score, technical_score,
                    historical_return_score, ai_confidence, factors_json,
                    reasons_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(fund_id, score_date) DO UPDATE SET
                    final_score=excluded.final_score,
                    rank=excluded.rank,
                    recommendation=excluded.recommendation,
                    recommendation_label=excluded.recommendation_label,
                    trend_score=excluded.trend_score,
                    liquidity_score=excluded.liquidity_score,
                    risk_score=excluded.risk_score,
                    money_flow_score=excluded.money_flow_score,
                    nav_score=excluded.nav_score,
                    volume_score=excluded.volume_score,
                    technical_score=excluded.technical_score,
                    historical_return_score=excluded.historical_return_score,
                    ai_confidence=excluded.ai_confidence,
                    factors_json=excluded.factors_json,
                    reasons_json=excluded.reasons_json
                """,
                (
                    fund_id,
                    score_date,
                    float(assessment.final_score),
                    assessment.rank,
                    assessment.recommendation,
                    assessment.recommendation_label,
                    factor_map.get("momentum"),
                    factor_map.get("liquidity"),
                    None,
                    factor_map.get("money_flow"),
                    factor_map.get("nav_premium"),
                    factor_map.get("volume_value"),
                    None,
                    None,
                    None,
                    json.dumps([f.to_dict() for f in assessment.factors], ensure_ascii=False),
                    json.dumps(list(assessment.summary_reasons), ensure_ascii=False),
                    now,
                ),
            )

    def save_market_snapshot(
        self,
        *,
        trade_date: str,
        funds_count: int,
        market_status: str = "",
        market_power: Optional[float] = None,
        best_group: str = "",
        worst_group: str = "",
        total_value: Optional[float] = None,
        total_volume: Optional[float] = None,
        avg_change_pct: Optional[float] = None,
        payload: Optional[dict[str, Any]] = None,
    ) -> int:
        now = _now_iso()
        with self.db.transaction() as conn:
            cur = conn.execute(
                """
                INSERT INTO market_snapshot(
                    snapshot_at, trade_date, funds_count, market_status,
                    market_power, best_group, worst_group, total_value,
                    total_volume, avg_change_pct, payload_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    now,
                    trade_date,
                    funds_count,
                    market_status,
                    market_power,
                    best_group,
                    worst_group,
                    total_value,
                    total_volume,
                    avg_change_pct,
                    json.dumps(payload or {}, ensure_ascii=False),
                    now,
                ),
            )
            return int(cur.lastrowid)

    # ---------------------------------------------------------- request cache
    def cache_get(self, key: str) -> Optional[str]:
        now = _now_iso()
        row = self.db.fetchone(
            """
            SELECT response_json FROM request_cache
            WHERE cache_key = ? AND expires_at > ?
            """,
            (key, now),
        )
        return row["response_json"] if row else None

    def cache_set(
        self,
        key: str,
        *,
        endpoint: str,
        params_json: str,
        response_json: str,
        expires_at: str,
    ) -> None:
        now = _now_iso()
        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO request_cache(cache_key, endpoint, params_json, response_json, expires_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    response_json=excluded.response_json,
                    expires_at=excluded.expires_at,
                    params_json=excluded.params_json,
                    endpoint=excluded.endpoint
                """,
                (key, endpoint, params_json, response_json, expires_at, now),
            )

    def cache_purge_expired(self) -> int:
        now = _now_iso()
        with self.db.transaction() as conn:
            cur = conn.execute(
                "DELETE FROM request_cache WHERE expires_at <= ?",
                (now,),
            )
            return int(cur.rowcount or 0)

    def bulk_upsert_quotes(
        self,
        quotes: Iterable[SymbolQuote],
        fund_types: Optional[dict[str, str]] = None,
        source: str = "brs",
    ) -> dict[str, int]:
        fund_types = fund_types or {}
        inserted = updated = 0
        for q in quotes:
            if not q.symbol:
                continue
            _, is_new = self.upsert_history_from_quote(
                q,
                fund_type=fund_types.get(q.symbol, ""),
                source=source,
            )
            if is_new:
                inserted += 1
            else:
                updated += 1
        return {"inserted": inserted, "updated": updated, "total": inserted + updated}
