import logging
import os
import re
import time
from decimal import Decimal

import requests
from dotenv import load_dotenv
from fastapi import HTTPException

load_dotenv()

logger = logging.getLogger(__name__)

FINNHUB_QUOTE_URL = "https://finnhub.io/api/v1/quote"
REQUEST_TIMEOUT_SECONDS = 5

# How long a cached price is trusted before we hit Finnhub again.
CACHE_TTL_SECONDS = 60

# Tickers are letters, dots, and dashes only (e.g. "BRK.B").
VALID_TICKER = re.compile(r"^[A-Z.\-]+$")

FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
if not FINNHUB_API_KEY:
    raise RuntimeError(
        "FINNHUB_API_KEY is not set. Add it to backend/.env (see .env.example)."
    )

# ticker -> (price, time fetched). Simple in-memory cache; resets on restart.
_price_cache: dict[str, tuple[Decimal, float]] = {}


def get_price(ticker: str) -> Decimal:
    """Return the current price for a ticker, using a 60-second cache.

    Raises HTTPException for an invalid ticker format, an unknown ticker,
    or any Finnhub failure, so routers can let it propagate as-is.
    """
    ticker = ticker.strip().upper()
    if not ticker or not VALID_TICKER.match(ticker):
        raise HTTPException(status_code=400, detail="Invalid ticker symbol")

    cached = _price_cache.get(ticker)
    if cached is not None:
        price, fetched_at = cached
        if time.time() - fetched_at < CACHE_TTL_SECONDS:
            logger.info("cache hit: %s", ticker)
            return price

    price = _fetch_from_finnhub(ticker)
    _price_cache[ticker] = (price, time.time())
    logger.info("fetched from Finnhub: %s", ticker)
    return price


def _fetch_from_finnhub(ticker: str) -> Decimal:
    try:
        response = requests.get(
            FINNHUB_QUOTE_URL,
            params={"symbol": ticker},
            headers={"X-Finnhub-Token": FINNHUB_API_KEY},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.exceptions.RequestException:
        raise HTTPException(status_code=503, detail="Price service unavailable")

    if response.status_code == 429:
        raise HTTPException(
            status_code=503, detail="Price service is busy, try again shortly"
        )
    if response.status_code != 200:
        raise HTTPException(status_code=503, detail="Price service unavailable")

    price = Decimal(str(response.json().get("c", 0)))
    if price == 0:
        raise HTTPException(status_code=404, detail="Ticker not found")

    return price
