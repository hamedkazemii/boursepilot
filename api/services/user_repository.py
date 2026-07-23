import sqlite3
import os
from pathlib import Path


BASE = Path(__file__).resolve().parents[2]


def get_db():

    db = os.getenv(
        "DATABASE_PATH",
        "data/database.db"
    )

    path = BASE / db

    path.parent.mkdir(
        exist_ok=True
    )

    conn = sqlite3.connect(
        path
    )

    conn.row_factory = sqlite3.Row

    return conn



def init_user_tables():

    conn = get_db()

    conn.execute("""
    CREATE TABLE IF NOT EXISTS web_users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id TEXT UNIQUE,
        username TEXT,
        risk_profile TEXT DEFAULT 'medium',
        capital REAL DEFAULT 0
    )
    """)


    conn.execute("""
    CREATE TABLE IF NOT EXISTS portfolio_items(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        symbol TEXT,
        units REAL,
        avg_price REAL
    )
    """)


    conn.commit()
    conn.close()



def ensure_user(
    telegram_id="demo",
    username="demo"
):

    init_user_tables()

    conn = get_db()


    row = conn.execute(
        """
        SELECT *
        FROM web_users
        WHERE telegram_id=?
        """,
        (telegram_id,)
    ).fetchone()


    if row:

        conn.close()

        return dict(row)


    cur = conn.execute(
        """
        INSERT INTO web_users
        (
        telegram_id,
        username
        )
        VALUES (?,?)
        """,
        (
            telegram_id,
            username
        )
    )


    conn.commit()


    user_id = cur.lastrowid


    row = conn.execute(
        """
        SELECT *
        FROM web_users
        WHERE id=?
        """,
        (user_id,)
    ).fetchone()


    conn.close()


    return dict(row)



def get_portfolio(user_id):

    conn=get_db()


    rows=conn.execute(
        """
        SELECT *
        FROM portfolio_items
        WHERE user_id=?
        """,
        (user_id,)
    ).fetchall()


    conn.close()


    return [
        dict(x)
        for x in rows
    ]



def add_item(
    user_id,
    symbol,
    units,
    avg_price
):

    conn=get_db()


    conn.execute(
        """
        INSERT INTO portfolio_items
        (
        user_id,
        symbol,
        units,
        avg_price
        )
        VALUES (?,?,?,?)
        """,
        (
            user_id,
            symbol,
            units,
            avg_price
        )
    )


    conn.commit()
    conn.close()



def delete_item(
    user_id,
    symbol
):

    conn=get_db()


    conn.execute(
        """
        DELETE FROM portfolio_items
        WHERE user_id=?
        AND symbol=?
        """,
        (
            user_id,
            symbol
        )
    )


    conn.commit()
    conn.close()

