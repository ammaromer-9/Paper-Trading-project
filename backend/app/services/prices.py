from decimal import Decimal

# Phase 1: hard-coded prices so we can build and test the trading logic
# before wiring up the real Finnhub API in Phase 2.
FAKE_PRICES = {
    "AAPL": Decimal("225.50"),
    "GOOGL": Decimal("175.25"),
    "MSFT": Decimal("430.10"),
    "TSLA": Decimal("245.80"),
    "AMZN": Decimal("188.40"),
}


def get_price(ticker: str) -> Decimal:
    """Return the current price for a ticker, or 0 if it's unknown.

    A price of 0 is treated as "invalid ticker" by the callers, matching
    how the real Finnhub API behaves for unknown symbols.
    """
    return FAKE_PRICES.get(ticker.upper(), Decimal("0"))
