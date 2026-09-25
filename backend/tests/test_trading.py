from decimal import Decimal
from unittest.mock import patch

from fastapi import HTTPException

from app import models


def _user(db_session_factory):
    db = db_session_factory()
    try:
        return db.query(models.User).first()
    finally:
        db.close()


def _holding(db_session_factory, ticker="AAPL"):
    db = db_session_factory()
    try:
        return (
            db.query(models.Holding)
            .filter(models.Holding.ticker == ticker)
            .first()
        )
    finally:
        db.close()


# --- quote --------------------------------------------------------------


def test_quote_endpoint_returns_price(client, mock_prices):
    mock_prices({"AAPL": "225.50"})
    response = client.get("/quote/aapl")

    assert response.status_code == 200
    assert response.json() == {"ticker": "AAPL", "price": "225.50"}


# --- buy ------------------------------------------------------------------


def test_buy_updates_cash_and_creates_holding(client, auth_headers, mock_prices):
    headers = auth_headers()
    mock_prices({"AAPL": "225.50"})

    response = client.post("/buy", json={"ticker": "AAPL", "shares": 2}, headers=headers)

    assert response.status_code == 200
    trade = response.json()
    assert trade["ticker"] == "AAPL"
    assert trade["side"] == "buy"
    assert trade["shares"] == 2
    # Per-share prices come from Numeric(12,4) columns, so they round-trip
    # with 4 decimal places even though dollar totals use 2.
    assert trade["price"] == "225.5000"

    portfolio = client.get("/portfolio", headers=headers).json()
    assert portfolio["cash_balance"] == "9549.00"
    assert portfolio["holdings"][0]["shares"] == 2
    assert portfolio["holdings"][0]["avg_cost"] == "225.5000"


def test_buying_same_stock_twice_gives_weighted_average_cost(client, auth_headers, mock_prices):
    headers = auth_headers()
    price_table = mock_prices({"AAPL": "100.00"})

    client.post("/buy", json={"ticker": "AAPL", "shares": 2}, headers=headers)  # 2 @ 100
    price_table["AAPL"] = Decimal("130.00")
    client.post("/buy", json={"ticker": "AAPL", "shares": 3}, headers=headers)  # 3 @ 130

    portfolio = client.get("/portfolio", headers=headers).json()
    holding = portfolio["holdings"][0]
    assert holding["shares"] == 5
    # (2*100 + 3*130) / 5 = 118.00
    assert holding["avg_cost"] == "118.0000"


def test_buy_with_exactly_enough_cash_leaves_zero_balance(client, auth_headers, mock_prices):
    headers = auth_headers()
    mock_prices({"AAPL": "10000.00"})

    response = client.post("/buy", json={"ticker": "AAPL", "shares": 1}, headers=headers)
    assert response.status_code == 200

    portfolio = client.get("/portfolio", headers=headers).json()
    assert portfolio["cash_balance"] == "0.00"


def test_buy_fails_when_cash_is_insufficient(client, auth_headers, mock_prices, db_session_factory):
    headers = auth_headers()
    mock_prices({"AAPL": "10000.01"})

    response = client.post("/buy", json={"ticker": "AAPL", "shares": 1}, headers=headers)

    assert response.status_code == 400
    assert response.json()["detail"] == "Not enough cash for this trade"

    user = _user(db_session_factory)
    assert user.cash_balance == Decimal("10000.00")
    assert _holding(db_session_factory) is None
    assert client.get("/trades", headers=headers).json() == []


def test_buy_fails_cleanly_when_price_lookup_fails(client, auth_headers, db_session_factory):
    headers = auth_headers()
    with patch(
        "app.services.prices.get_price",
        side_effect=HTTPException(status_code=503, detail="Price service unavailable"),
    ):
        response = client.post("/buy", json={"ticker": "AAPL", "shares": 2}, headers=headers)

    assert response.status_code == 503

    user = _user(db_session_factory)
    assert user.cash_balance == Decimal("10000.00")
    assert _holding(db_session_factory) is None


def test_buy_normalizes_ticker_case_and_whitespace(client, auth_headers, mock_prices):
    headers = auth_headers()
    mock_prices({"AAPL": "100.00"})

    response = client.post("/buy", json={"ticker": " aapl ", "shares": 1}, headers=headers)

    assert response.status_code == 200
    assert response.json()["ticker"] == "AAPL"


def test_buy_rejects_zero_shares(client, auth_headers, mock_prices):
    headers = auth_headers()
    mock_prices({"AAPL": "100.00"})

    response = client.post("/buy", json={"ticker": "AAPL", "shares": 0}, headers=headers)
    assert response.status_code == 400


def test_buy_rejects_negative_shares(client, auth_headers, mock_prices):
    headers = auth_headers()
    mock_prices({"AAPL": "100.00"})

    response = client.post("/buy", json={"ticker": "AAPL", "shares": -1}, headers=headers)
    assert response.status_code == 400


def test_buy_rejects_non_integer_shares(client, auth_headers, mock_prices):
    headers = auth_headers()
    mock_prices({"AAPL": "100.00"})

    response = client.post("/buy", json={"ticker": "AAPL", "shares": 1.5}, headers=headers)
    assert response.status_code == 422


def test_every_successful_buy_creates_one_trade_record(client, auth_headers, mock_prices):
    headers = auth_headers()
    mock_prices({"AAPL": "100.00"})

    client.post("/buy", json={"ticker": "AAPL", "shares": 2}, headers=headers)

    trades = client.get("/trades", headers=headers).json()
    assert len(trades) == 1
    assert trades[0]["side"] == "buy"
    assert trades[0]["shares"] == 2
    assert trades[0]["price"] == "100.0000"


# --- sell -------------------------------------------------------------------


def test_partial_sell_reduces_shares_but_keeps_avg_cost(client, auth_headers, mock_prices):
    headers = auth_headers()
    mock_prices({"AAPL": "100.00"})
    client.post("/buy", json={"ticker": "AAPL", "shares": 4}, headers=headers)

    response = client.post("/sell", json={"ticker": "AAPL", "shares": 1}, headers=headers)

    assert response.status_code == 200
    portfolio = client.get("/portfolio", headers=headers).json()
    holding = portfolio["holdings"][0]
    assert holding["shares"] == 3
    assert holding["avg_cost"] == "100.0000"


def test_selling_all_shares_removes_the_holding(client, auth_headers, mock_prices):
    headers = auth_headers()
    mock_prices({"AAPL": "100.00"})
    client.post("/buy", json={"ticker": "AAPL", "shares": 2}, headers=headers)

    response = client.post("/sell", json={"ticker": "AAPL", "shares": 2}, headers=headers)

    assert response.status_code == 200
    portfolio = client.get("/portfolio", headers=headers).json()
    assert portfolio["holdings"] == []


def test_sell_updates_cash_balance(client, auth_headers, mock_prices):
    headers = auth_headers()
    price_table = mock_prices({"AAPL": "100.00"})
    client.post("/buy", json={"ticker": "AAPL", "shares": 2}, headers=headers)  # cash: 9800.00

    price_table["AAPL"] = Decimal("150.00")
    response = client.post("/sell", json={"ticker": "AAPL", "shares": 1}, headers=headers)

    assert response.status_code == 200
    portfolio = client.get("/portfolio", headers=headers).json()
    assert portfolio["cash_balance"] == "9950.00"  # 9800 + 150


def test_sell_fails_for_a_stock_you_dont_own(client, auth_headers, mock_prices, db_session_factory):
    headers = auth_headers()
    mock_prices({"AAPL": "100.00"})

    response = client.post("/sell", json={"ticker": "AAPL", "shares": 1}, headers=headers)

    assert response.status_code == 400
    assert response.json()["detail"] == "Not enough shares to sell"
    assert _user(db_session_factory).cash_balance == Decimal("10000.00")


def test_sell_fails_when_selling_more_shares_than_owned(client, auth_headers, mock_prices):
    headers = auth_headers()
    mock_prices({"AAPL": "100.00"})
    client.post("/buy", json={"ticker": "AAPL", "shares": 1}, headers=headers)

    response = client.post("/sell", json={"ticker": "AAPL", "shares": 2}, headers=headers)

    assert response.status_code == 400
    holding = _holding_response(client, headers)
    assert holding["shares"] == 1


def _holding_response(client, headers):
    return client.get("/portfolio", headers=headers).json()["holdings"][0]


def test_sell_rejects_zero_and_negative_shares(client, auth_headers, mock_prices):
    headers = auth_headers()
    mock_prices({"AAPL": "100.00"})
    client.post("/buy", json={"ticker": "AAPL", "shares": 1}, headers=headers)

    assert client.post("/sell", json={"ticker": "AAPL", "shares": 0}, headers=headers).status_code == 400
    assert client.post("/sell", json={"ticker": "AAPL", "shares": -1}, headers=headers).status_code == 400


def test_failed_sell_leaves_cash_holdings_and_trades_unchanged(client, auth_headers, mock_prices, db_session_factory):
    headers = auth_headers()
    mock_prices({"AAPL": "100.00"})
    client.post("/buy", json={"ticker": "AAPL", "shares": 1}, headers=headers)

    response = client.post("/sell", json={"ticker": "AAPL", "shares": 5}, headers=headers)

    assert response.status_code == 400
    assert _user(db_session_factory).cash_balance == Decimal("9900.00")
    assert _holding(db_session_factory).shares == 1
    assert len(client.get("/trades", headers=headers).json()) == 1


def test_every_successful_sell_creates_one_trade_record(client, auth_headers, mock_prices):
    headers = auth_headers()
    mock_prices({"AAPL": "100.00"})
    client.post("/buy", json={"ticker": "AAPL", "shares": 2}, headers=headers)

    client.post("/sell", json={"ticker": "AAPL", "shares": 1}, headers=headers)

    trades = client.get("/trades", headers=headers).json()
    sell_trades = [t for t in trades if t["side"] == "sell"]
    assert len(sell_trades) == 1
    assert sell_trades[0]["shares"] == 1
    assert sell_trades[0]["price"] == "100.0000"


# --- money precision ----------------------------------------------------


def test_money_math_uses_decimal_not_float(client, auth_headers, mock_prices):
    """3 shares at $0.10 would show a rounding error with plain floats
    (0.1 * 3 == 0.30000000000000004 in binary floating point). Using
    Decimal throughout keeps this exact.
    """
    headers = auth_headers()
    mock_prices({"PENNY": "0.10"})

    response = client.post("/buy", json={"ticker": "PENNY", "shares": 3}, headers=headers)

    assert response.status_code == 200
    assert response.json()["price"] == "0.1000"

    portfolio = client.get("/portfolio", headers=headers).json()
    assert portfolio["cash_balance"] == "9999.70"
