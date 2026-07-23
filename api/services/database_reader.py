from pathlib import Path
import sqlite3


BASE_DIR = Path(__file__).resolve().parents[2]


def find_database():

    candidates = [
        BASE_DIR / "data" / "database.db",
        BASE_DIR / "data" / "sandoghchi.db",
    ]

    for db in candidates:
        if db.exists():
            return db

    return None


def get_connection():

    db = find_database()

    if not db:
        return None

    return sqlite3.connect(db)


def health_check():

    conn = get_connection()

    if not conn:
        return {
            "db": False
        }

    try:
        conn.execute("SELECT 1")
        return {
            "db": True
        }

    finally:
        conn.close()
