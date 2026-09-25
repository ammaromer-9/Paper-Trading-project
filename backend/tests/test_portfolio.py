from decimal import Decimal


def test_brand_new_user_has_starting_cash_and_nothing_else(client, auth_headers):
    headers = auth_headers()

    portfolio = client.get("/portfolio", headers=headers).json()
    assert portfolio["cash_balance"] == "10000.00"
    assert portfolio["holdings"] == []
    assert portfolio["total_value"] == "10000.00"

    assert client.get("/trades", headers=headers).json() == []


def test_portfolio_math_for_a_gain(client, auth_headers, mock_prices):
    headers = auth_headers()
    price_table = mock_prices({"AAPL": "100.00"})
    client.post("/buy", json={"ticker": "AAPL", "shares": 2}, headers=headers)  # cash: 9800.00

    price_table["AAPL"] = Decimal("150.00")
    portfolio = client.get("/portfolio", headers=headers).json()
    holding = portfolio["holdings"][0]

    assert holding["current_price"] == "150.00"
    assert holding["market_value"] == "300.00"
    assert holding["gain_loss"] == "100.00"
    assert holding["gain_loss_percent"] == "50.00"
    assert portfolio["total_value"] == "10100.00"  # 9800 cash + 300 market value


def test_portfolio_math_for_a_loss(client, auth_headers, mock_prices):
    headers = auth_headers()
    price_table = mock_prices({"AAPL": "100.00"})
    client.post("/buy", json={"ticker": "AAPL", "shares": 2}, headers=headers)  # cash: 9800.00

    price_table["AAPL"] = Decimal("75.00")
    portfolio = client.get("/portfolio", headers=headers).json()
    holding = portfolio["holdings"][0]

    assert holding["market_value"] == "150.00"
    assert holding["gain_loss"] == "-50.00"
    assert holding["gain_loss_percent"] == "-25.00"
    assert portfolio["total_value"] == "9950.00"  # 9800 cash + 150 market value


def test_portfolio_math_at_break_even(client, auth_headers, mock_prices):
    headers = auth_headers()
    mock_prices({"AAPL": "100.00"})
    client.post("/buy", json={"ticker": "AAPL", "shares": 2}, headers=headers)

    portfolio = client.get("/portfolio", headers=headers).json()
    holding = portfolio["holdings"][0]

    assert holding["gain_loss"] == "0.00"
    assert holding["gain_loss_percent"] == "0.00"


def test_total_value_equals_cash_plus_market_value_across_multiple_holdings(
    client, auth_headers, mock_prices
):
    headers = auth_headers()
    price_table = mock_prices({"AAPL": "100.00", "MSFT": "50.00"})
    client.post("/buy", json={"ticker": "AAPL", "shares": 2}, headers=headers)  # -200
    client.post("/buy", json={"ticker": "MSFT", "shares": 4}, headers=headers)  # -200

    price_table["AAPL"] = Decimal("120.00")
    price_table["MSFT"] = Decimal("60.00")
    portfolio = client.get("/portfolio", headers=headers).json()

    # cash: 10000 - 200 - 200 = 9600.00
    # market value: 2*120 + 4*60 = 480.00
    assert portfolio["cash_balance"] == "9600.00"
    assert portfolio["total_value"] == "10080.00"


def test_trade_history_is_returned_newest_first(client, auth_headers, mock_prices):
    headers = auth_headers()
    mock_prices({"AAPL": "100.00"})

    client.post("/buy", json={"ticker": "AAPL", "shares": 3}, headers=headers)
    client.post("/sell", json={"ticker": "AAPL", "shares": 1}, headers=headers)
    client.post("/buy", json={"ticker": "AAPL", "shares": 1}, headers=headers)

    trades = client.get("/trades", headers=headers).json()

    assert [t["side"] for t in trades] == ["buy", "sell", "buy"][::-1]
    assert trades[0]["shares"] == 1  # most recent trade: the second buy
    assert trades[-1]["shares"] == 3  # oldest trade: the first buy
