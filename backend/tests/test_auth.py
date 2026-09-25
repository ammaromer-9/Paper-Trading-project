from datetime import datetime, timedelta, timezone

import jwt

from app.auth import JWT_ALGORITHM, JWT_SECRET


def _expired_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


# --- signup ---------------------------------------------------------------


def test_signup_creates_user_with_starting_cash(client):
    response = client.post(
        "/signup", json={"email": "new@example.com", "password": "password123"}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "new@example.com"
    assert body["cash_balance"] == "10000.00"
    assert "password" not in body
    assert "password_hash" not in body


def test_signup_duplicate_email_returns_409(client):
    client.post("/signup", json={"email": "dup@example.com", "password": "password123"})
    response = client.post(
        "/signup", json={"email": "dup@example.com", "password": "password123"}
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Email already registered"


def test_signup_rejects_invalid_email(client):
    response = client.post(
        "/signup", json={"email": "not-an-email", "password": "password123"}
    )
    assert response.status_code == 422


def test_signup_rejects_short_password(client):
    response = client.post("/signup", json={"email": "short@example.com", "password": "abc"})
    assert response.status_code == 422


def test_signup_lowercases_email(client):
    client.post("/signup", json={"email": "Mixed@Example.com", "password": "password123"})
    response = client.post("/login", data={"username": "mixed@example.com", "password": "password123"})
    assert response.status_code == 200


# --- login ------------------------------------------------------------------


def test_login_with_correct_credentials_returns_token(client):
    client.post("/signup", json={"email": "login@example.com", "password": "password123"})
    response = client.post(
        "/login", data={"username": "login@example.com", "password": "password123"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_wrong_password_returns_401(client):
    client.post("/signup", json={"email": "login2@example.com", "password": "password123"})
    response = client.post(
        "/login", data={"username": "login2@example.com", "password": "wrongpassword"}
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_login_unknown_email_returns_same_401(client):
    response = client.post(
        "/login", data={"username": "nobody@example.com", "password": "password123"}
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


# --- protecting endpoints ----------------------------------------------------


def test_protected_endpoint_rejects_missing_token(client):
    response = client.get("/portfolio")
    assert response.status_code == 401


def test_protected_endpoint_rejects_bad_token(client):
    response = client.get("/portfolio", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401


def test_protected_endpoint_rejects_expired_token(client):
    signup = client.post(
        "/signup", json={"email": "expired@example.com", "password": "password123"}
    )
    user_id = signup.json()["id"]
    token = _expired_token(user_id)

    response = client.get("/portfolio", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_protected_endpoint_rejects_token_for_a_deleted_user(client, auth_headers):
    headers = auth_headers()
    token = headers["Authorization"].removeprefix("Bearer ")
    user_id = int(jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])["sub"])

    from app.database import SessionLocal
    from app import models

    db = SessionLocal()
    try:
        db.query(models.User).filter(models.User.id == user_id).delete()
        db.commit()
    finally:
        db.close()

    response = client.get("/portfolio", headers=headers)
    assert response.status_code == 401


def test_quote_stays_public(client, mock_prices):
    mock_prices({"AAPL": "225.50"})
    response = client.get("/quote/aapl")
    assert response.status_code == 200


def test_root_endpoint_reports_ok(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# --- user isolation -----------------------------------------------------------


def test_users_cannot_see_each_others_data(client, auth_headers, mock_prices):
    headers_a = auth_headers("a@example.com", "passwordA1")
    headers_b = auth_headers("b@example.com", "passwordB1")

    mock_prices({"AAPL": "100.00"})
    client.post("/buy", json={"ticker": "AAPL", "shares": 5}, headers=headers_a)

    portfolio_b = client.get("/portfolio", headers=headers_b).json()
    assert portfolio_b["holdings"] == []
    assert portfolio_b["cash_balance"] == "10000.00"

    trades_b = client.get("/trades", headers=headers_b).json()
    assert trades_b == []

    trades_a = client.get("/trades", headers=headers_a).json()
    assert len(trades_a) == 1
