"""سرویس پروفایل کاربر، پرتفو و واچ‌لیست."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional

from core.database.connection import Database, get_database


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


class PortfolioService:
    def __init__(self, db: Optional[Database] = None) -> None:
        self.db = db or get_database()

    def ensure_user(
        self,
        telegram_id: str | int,
        *,
        username: str = "",
        first_name: str = "",
        last_name: str = "",
    ) -> dict[str, Any]:
        tid = str(telegram_id)
        now = _now()
        row = self.db.fetchone("SELECT * FROM users WHERE telegram_id = ?", (tid,))
        if row:
            with self.db.transaction() as conn:
                conn.execute(
                    """
                    UPDATE users SET username=COALESCE(NULLIF(?,''), username),
                        first_name=COALESCE(NULLIF(?,''), first_name),
                        last_name=COALESCE(NULLIF(?,''), last_name),
                        last_seen_at=?, updated_at=?
                    WHERE telegram_id=?
                    """,
                    (username, first_name, last_name, now, now, tid),
                )
            user = dict(self.db.fetchone("SELECT * FROM users WHERE telegram_id = ?", (tid,)))
        else:
            with self.db.transaction() as conn:
                cur = conn.execute(
                    """
                    INSERT INTO users(telegram_id, username, first_name, last_name, created_at, updated_at, last_seen_at)
                    VALUES (?,?,?,?,?,?,?)
                    """,
                    (tid, username, first_name, last_name, now, now, now),
                )
                uid = int(cur.lastrowid)
                conn.execute(
                    """
                    INSERT INTO portfolios(user_id, name, created_at, updated_at)
                    VALUES (?, 'اصلی', ?, ?)
                    """,
                    (uid, now, now),
                )
            user = dict(self.db.fetchone("SELECT * FROM users WHERE telegram_id = ?", (tid,)))
        return user

    def get_user(self, telegram_id: str | int) -> Optional[dict[str, Any]]:
        row = self.db.fetchone("SELECT * FROM users WHERE telegram_id = ?", (str(telegram_id),))
        return dict(row) if row else None

    def update_profile(
        self,
        telegram_id: str | int,
        *,
        risk_profile: Optional[str] = None,
        horizon_months: Optional[int] = None,
        capital: Optional[float] = None,
        preferred_groups: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        user = self.ensure_user(telegram_id)
        now = _now()
        with self.db.transaction() as conn:
            conn.execute(
                """
                UPDATE users SET
                    risk_profile=COALESCE(?, risk_profile),
                    horizon_months=COALESCE(?, horizon_months),
                    capital=COALESCE(?, capital),
                    preferred_groups=COALESCE(?, preferred_groups),
                    updated_at=?
                WHERE id=?
                """,
                (
                    risk_profile,
                    horizon_months,
                    capital,
                    json.dumps(preferred_groups, ensure_ascii=False) if preferred_groups is not None else None,
                    now,
                    user["id"],
                ),
            )
        return dict(self.db.fetchone("SELECT * FROM users WHERE id = ?", (user["id"],)))

    def get_portfolio(self, telegram_id: str | int, name: str = "اصلی") -> dict[str, Any]:
        user = self.ensure_user(telegram_id)
        row = self.db.fetchone(
            "SELECT * FROM portfolios WHERE user_id = ? AND name = ?",
            (user["id"], name),
        )
        if not row:
            now = _now()
            with self.db.transaction() as conn:
                conn.execute(
                    "INSERT INTO portfolios(user_id, name, created_at, updated_at) VALUES (?,?,?,?)",
                    (user["id"], name, now, now),
                )
            row = self.db.fetchone(
                "SELECT * FROM portfolios WHERE user_id = ? AND name = ?",
                (user["id"], name),
            )
        items = self.db.fetchall(
            "SELECT * FROM portfolio_items WHERE portfolio_id = ? ORDER BY symbol",
            (row["id"],),
        )
        return {"portfolio": dict(row), "items": [dict(i) for i in items], "user": user}

    def upsert_holding(
        self,
        telegram_id: str | int,
        symbol: str,
        *,
        quantity: float,
        avg_cost: Optional[float] = None,
        notes: str = "",
    ) -> dict[str, Any]:
        pf = self.get_portfolio(telegram_id)
        pid = pf["portfolio"]["id"]
        now = _now()
        symbol = symbol.strip()
        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO portfolio_items(portfolio_id, symbol, quantity, avg_cost, notes, created_at, updated_at)
                VALUES (?,?,?,?,?,?,?)
                ON CONFLICT(portfolio_id, symbol) DO UPDATE SET
                    quantity=excluded.quantity,
                    avg_cost=COALESCE(excluded.avg_cost, portfolio_items.avg_cost),
                    notes=COALESCE(NULLIF(excluded.notes,''), portfolio_items.notes),
                    updated_at=excluded.updated_at
                """,
                (pid, symbol, float(quantity), avg_cost, notes, now, now),
            )
        return self.get_portfolio(telegram_id)

    def remove_holding(self, telegram_id: str | int, symbol: str) -> dict[str, Any]:
        pf = self.get_portfolio(telegram_id)
        with self.db.transaction() as conn:
            conn.execute(
                "DELETE FROM portfolio_items WHERE portfolio_id = ? AND symbol = ?",
                (pf["portfolio"]["id"], symbol.strip()),
            )
        return self.get_portfolio(telegram_id)

    def add_watch(self, telegram_id: str | int, symbol: str) -> None:
        user = self.ensure_user(telegram_id)
        now = _now()
        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO watchlist(user_id, symbol, created_at)
                VALUES (?,?,?)
                """,
                (user["id"], symbol.strip(), now),
            )

    def list_watch(self, telegram_id: str | int) -> list[str]:
        user = self.ensure_user(telegram_id)
        rows = self.db.fetchall(
            "SELECT symbol FROM watchlist WHERE user_id = ? ORDER BY created_at DESC",
            (user["id"],),
        )
        return [r["symbol"] for r in rows]

    def portfolio_summary_text(self, telegram_id: str | int, prices: Optional[dict[str, float]] = None) -> str:
        data = self.get_portfolio(telegram_id)
        user = data["user"]
        items = data["items"]
        lines = [
            "📁 پرتفوی شما",
            f"ریسک: {user.get('risk_profile') or 'medium'} | افق: {user.get('horizon_months') or 12} ماه",
        ]
        if user.get("capital"):
            lines.append(f"سرمایه ثبت‌شده: {float(user['capital']):,.0f}")
        if not items:
            lines.append("هنوز سهم/صندوقی ثبت نشده. مثال: /pf_add عیار 100")
            return "\n".join(lines)
        total_cost = 0.0
        total_val = 0.0
        lines.append("")
        for it in items:
            qty = float(it.get("quantity") or 0)
            cost = float(it.get("avg_cost") or 0)
            px = (prices or {}).get(it["symbol"]) or cost
            val = qty * float(px or 0)
            cval = qty * cost
            total_cost += cval
            total_val += val
            pnl = val - cval
            pnl_pct = (pnl / cval * 100.0) if cval else 0.0
            lines.append(
                f"• {it['symbol']}: {qty:g} | بهای تمام‌شده {cost:,.0f} | ارزش {val:,.0f} | PnL {pnl_pct:+.1f}%"
            )
        if total_cost:
            lines.append("")
            lines.append(f"جمع بهای تمام‌شده: {total_cost:,.0f}")
            lines.append(f"ارزش روز: {total_val:,.0f}")
            lines.append(f"بازده پرتفو: {(total_val/total_cost-1)*100:+.2f}%")
        return "\n".join(lines)
