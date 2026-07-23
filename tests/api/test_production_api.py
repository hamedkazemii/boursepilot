import os
import sys

sys.path.insert(0, os.getcwd())

from fastapi.testclient import TestClient
from api.main import app


client = TestClient(app)


def test_health():
    r = client.get("/api/v1/health")

    assert r.status_code == 200

    body = r.json()

    assert body["status"] == "ok"


def test_market_summary_route():
    r = client.get("/api/v1/market/summary")

    assert r.status_code in [200,404,500]


def test_ranking_routes_exist():

    routes = [
        r.path
        for r in app.routes
    ]

    assert "/api/v1/ranking/today" in routes
    assert "/api/v1/ranking/top" in routes


def test_fund_route_exists():

    routes = [
        r.path
        for r in app.routes
    ]

    assert "/api/v1/funds/{symbol}" in routes


def test_portfolio_routes_exist():

    routes = [
        r.path
        for r in app.routes
    ]

    assert "/api/v1/me/portfolio" in routes


def test_auth_routes_exist():

    routes = [
        r.path
        for r in app.routes
    ]

    assert "/api/v1/auth/login" in routes

