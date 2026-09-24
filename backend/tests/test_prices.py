from decimal import Decimal
from unittest.mock import patch

import pytest
import requests
from fastapi import HTTPException

from app.services import prices


def _mock_response(status_code=200, json_data=None):
    class _Response:
        def __init__(self):
            self.status_code = status_code

        def json(self):
            return json_data or {}

    return _Response()


def test_valid_price_is_fetched_and_returned():
    with patch("app.services.prices.requests.get", return_value=_mock_response(json_data={"c": 225.50})) as mock_get:
        price = prices.get_price("aapl")

    assert price == Decimal("225.50")
    mock_get.assert_called_once()
    # Ticker is uppercased before it's sent to Finnhub.
    assert mock_get.call_args.kwargs["params"]["symbol"] == "AAPL"
    # The key goes in a header, never in the URL/params.
    assert mock_get.call_args.kwargs["headers"]["X-Finnhub-Token"] == prices.FINNHUB_API_KEY


def test_unknown_ticker_returns_404():
    with patch("app.services.prices.requests.get", return_value=_mock_response(json_data={"c": 0})):
        with pytest.raises(HTTPException) as exc_info:
            prices.get_price("ZZZZ")

    assert exc_info.value.status_code == 404


def test_timeout_returns_503():
    with patch("app.services.prices.requests.get", side_effect=requests.exceptions.Timeout):
        with pytest.raises(HTTPException) as exc_info:
            prices.get_price("AAPL")

    assert exc_info.value.status_code == 503
    assert "unavailable" in exc_info.value.detail


def test_rate_limit_returns_503():
    with patch("app.services.prices.requests.get", return_value=_mock_response(status_code=429)):
        with pytest.raises(HTTPException) as exc_info:
            prices.get_price("AAPL")

    assert exc_info.value.status_code == 503
    assert "busy" in exc_info.value.detail


@pytest.mark.parametrize("bad_ticker", ["", "AA PL", "AAP$L"])
def test_malformed_ticker_returns_400_without_calling_finnhub(bad_ticker):
    with patch("app.services.prices.requests.get") as mock_get:
        with pytest.raises(HTTPException) as exc_info:
            prices.get_price(bad_ticker)

    assert exc_info.value.status_code == 400
    mock_get.assert_not_called()


def test_cache_hit_within_60_seconds_skips_second_call():
    with patch("app.services.prices.requests.get", return_value=_mock_response(json_data={"c": 225.50})) as mock_get:
        first = prices.get_price("AAPL")
        second = prices.get_price("AAPL")

    assert first == second == Decimal("225.50")
    mock_get.assert_called_once()


def test_cache_refetches_after_60_seconds():
    with patch("app.services.prices.requests.get", return_value=_mock_response(json_data={"c": 225.50})) as mock_get:
        with patch("app.services.prices.time.time", return_value=1_000.0):
            prices.get_price("AAPL")
        with patch("app.services.prices.time.time", return_value=1_000.0 + prices.CACHE_TTL_SECONDS + 1):
            prices.get_price("AAPL")

    assert mock_get.call_count == 2
