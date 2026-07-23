from pathlib import Path
import json
import sqlite3
import os


BASE = Path(__file__).resolve().parents[2]


def load_report():

    candidates = [
        BASE / "reports/daily_ranking.json",
        BASE / "data/daily_ranking.json"
    ]

    for file in candidates:
        if file.exists():
            try:
                return json.loads(file.read_text())
            except Exception:
                pass

    return {
        "top": [],
        "worst": [],
        "funds": []
    }



def db_status():

    db_path = os.getenv(
        "DATABASE_PATH",
        "data/database.db"
    )

    path = BASE / db_path

    if not path.exists():
        return {
            "exists": False
        }

    try:
        conn = sqlite3.connect(path)

        tables = conn.execute(
            "select name from sqlite_master where type='table'"
        ).fetchall()

        conn.close()

        return {
            "exists": True,
            "tables": [
                x[0] for x in tables
            ]
        }

    except Exception as e:

        return {
            "exists": False,
            "error": str(e)
        }



def market_summary():

    report = load_report()

    top = report.get("top", [])
    worst = report.get("worst", [])

    return {

        "top_count": len(top),
        "worst_count": len(worst),

        "source": report.get(
            "source",
            "unknown"
        ),

        "as_of": report.get(
            "as_of"
        ),

        "sane": report.get(
            "sane",
            False
        )

    }

