import os


def test_required_data_files():

    files = [

        "data/funds.json",
        "data/fund_registry.json",
        "data/fund_ranking.json"

    ]

    for f in files:
        assert os.path.exists(f), f"Missing {f}"


def test_database_exists():

    assert os.path.exists(
        "data/database.db"
    )

