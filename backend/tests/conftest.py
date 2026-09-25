import os
import tempfile

# Must happen before anything under app/ is imported, since database.py and
# services/prices.py read these env vars at import time.
_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.close(_db_fd)
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"
os.environ.setdefault("FINNHUB_API_KEY", "test-key")

import pytest
from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, engine
from app.main import app
from app.services import prices


@pytest.fixture(autouse=True)
def _reset_state():
    """Fresh tables and an empty price cache before every test."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    prices._price_cache.clear()
    yield


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db_session_factory():
    return SessionLocal


@pytest.fixture
def auth_headers(client):
    """Signs up a fresh user and returns an Authorization header for them."""

    def _make(email="trader@example.com", password="password123"):
        client.post("/signup", json={"email": email, "password": password})
        response = client.post("/login", data={"username": email, "password": password})
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _make
