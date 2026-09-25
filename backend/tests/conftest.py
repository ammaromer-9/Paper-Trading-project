import os
from decimal import Decimal

# Must happen before anything under app/ is imported, since app.database,
# app.auth, and app.services.prices all read these env vars at import time.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["JWT_SECRET"] = "test-secret-for-pytest-only"
os.environ.setdefault("FINNHUB_API_KEY", "test-key")

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.database as database
from app.database import Base
from app.main import app
from app.services import prices

# A plain in-memory SQLite DB is per-connection, so a normal connection pool
# would give every session its own empty database. StaticPool keeps everyone
# on the same connection for the life of the test process.
_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)

# Swap the app's engine/session for our in-memory ones so the get_db
# dependency (and anything else importing app.database) uses them too.
database.engine = _engine
database.SessionLocal = _TestSessionLocal


@pytest.fixture(autouse=True)
def _reset_state():
    """Fresh tables and an empty price cache before every test."""
    Base.metadata.create_all(bind=_engine)
    prices._price_cache.clear()
    yield
    Base.metadata.drop_all(bind=_engine)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db_session_factory():
    return _TestSessionLocal


@pytest.fixture
def auth_headers(client):
    """Signs up a fresh user and returns an Authorization header for them."""

    def _make(email="trader@example.com", password="password123"):
        client.post("/signup", json={"email": email, "password": password})
        response = client.post("/login", data={"username": email, "password": password})
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _make


@pytest.fixture
def mock_prices():
    """Patches the price service to serve fixed prices, e.g. mock_prices({"AAPL": "225.50"}).

    Both routers call through the same `prices` module, so patching
    `prices.get_price` here covers /quote, /buy, /sell, and /portfolio alike.
    """
    active_patchers = []

    def _set(prices_by_ticker):
        table = {ticker.upper(): Decimal(str(value)) for ticker, value in prices_by_ticker.items()}

        def fake_get_price(ticker):
            ticker = ticker.strip().upper()
            if ticker not in table:
                raise HTTPException(status_code=404, detail="Ticker not found")
            return table[ticker]

        from unittest.mock import patch

        patcher = patch("app.services.prices.get_price", side_effect=fake_get_price)
        patcher.start()
        active_patchers.append(patcher)
        return table

    yield _set

    for patcher in active_patchers:
        patcher.stop()
