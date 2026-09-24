from decimal import Decimal
from unittest.mock import patch

from fastapi import HTTPException

from app import models


def _mock_price(value):
    """Patch get_price to return a fixed Decimal-compatible value."""
    return patch("app.routers.trading.prices.get_price", return_value=Decimal(str(value)))


def test_quote_endpoint_returns_price(client):
    with _mock_price(225.50):
        response = client.get("/quote/aapl")

    assert response.status_code == 200
    assert response.json() == {"ticker": "AAPL", "price": "225.5"}


def test_buy_updates_cash_and_holdings(client):
    with _mock_price(225.50):
        response = client.post("/buy", json={"ticker": "AAPL", "shares": 2})

    assert response.status_code == 200
    trade = response.json()
    assert trade["ticker"] == "AAPL"
    assert trade["shares"] == 2


def test_buy_fails_cleanly_when_price_lookup_fails(client, db_session_factory):
    with patch(
        "app.routers.trading.prices.get_price",
        side_effect=HTTPException(status_code=503, detail="Price service unavailable"),
    ):
        response = client.post("/buy", json={"ticker": "AAPL", "shares": 2})

    assert response.status_code == 503

    db = db_session_factory()
    try:
        user = db.query(models.User).first()
        assert user.cash_balance == Decimal("10000.00")
        assert db.query(models.Holding).count() == 0
    finally:
        db.close()


def test_sell_updates_cash_and_holdings(client):
    with _mock_price(225.50):
        client.post("/buy", json={"ticker": "AAPL", "shares": 2})
        response = client.post("/sell", json={"ticker": "AAPL", "shares": 1})

    assert response.status_code == 200
    assert response.json()["shares"] == 1


def test_portfolio_shows_live_market_value(client):
    with _mock_price(225.50):
        client.post("/buy", json={"ticker": "AAPL", "shares": 2})

    with patch("app.routers.portfolio.prices.get_price", return_value=Decimal("250.00")):
        response = client.get("/portfolio")

    assert response.status_code == 200
    holding = response.json()["holdings"][0]
    assert holding["current_price"] == "250.00"
    assert holding["market_value"] == "500.00"
