from pathlib import Path
import json


BASE = Path(__file__).resolve().parents[2]


def get_ranking_data():

    files = [
        BASE / "reports/daily_ranking.json",
        BASE / "reports/daily_ranking_latest.json",
        BASE / "data/daily_ranking.json"
    ]

    for f in files:

        if f.exists():

            try:
                return json.loads(
                    f.read_text()
                )

            except Exception:
                continue


    return {
        "ranking": [],
        "top": [],
        "worst": []
    }



def normalize_item(item):

    return {

        "symbol":
            item.get(
                "symbol",
                ""
            ),

        "name":
            item.get(
                "name",
                ""
            ),

        "score":
            item.get(
                "score",
                0
            ),

        "rank":
            item.get(
                "rank"
            ),

        "recommendation":
            item.get(
                "recommendation",
                "neutral"
            ),

        "reasons":
            item.get(
                "reasons",
                []
            )

    }



def get_all():

    data = get_ranking_data()

    items = (
        data.get("ranking")
        or data.get("funds")
        or []
    )

    return [
        normalize_item(x)
        for x in items
    ]



def get_top(limit=10):

    data = get_ranking_data()

    items = (
        data.get("top")
        or get_all()
    )

    return [
        normalize_item(x)
        for x in items[:limit]
    ]



def get_worst(limit=10):

    data = get_ranking_data()

    items = (
        data.get("worst")
        or []
    )

    return [
        normalize_item(x)
        for x in items[:limit]
    ]



def find_symbol(symbol):

    for item in get_all():

        if item["symbol"] == symbol:

            return item


    return None

