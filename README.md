# Paper Trading Project

A paper (simulated) stock trading API. Buy and sell fake shares with real
market prices and track a virtual portfolio.

## Setup

1. Create a virtual environment and install dependencies:

   ```bash
   cd backend
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Copy the example env file and fill in your own values:

   ```bash
   cp .env.example .env
   ```

   You'll need a `JWT_SECRET` (used to sign login tokens) — generate one with:

   ```bash
   python3 -c "import secrets; print(secrets.token_hex(32))"
   ```

   Paste the output into `backend/.env` as `JWT_SECRET=...`.

3. Run the server:

   ```bash
   uvicorn app.main:app --reload
   ```

   The API docs are then available at `http://localhost:8000/docs`.

### Getting a Finnhub API key

Live prices come from [Finnhub](https://finnhub.io). To get a free key:

1. Sign up at https://finnhub.io/register.
2. Copy the API key from your Finnhub dashboard.
3. Paste it into `backend/.env` as `FINNHUB_API_KEY=your-key-here`.
4. Restart the server so it picks up the new value — `.env` is only read on
   startup.

The free tier is plenty for development; the app also caches each price for
60 seconds to stay well within the rate limit.

## Authentication

Every endpoint except `GET /quote/{ticker}` requires a logged-in user.

1. **Sign up** — `POST /signup` with a JSON body of `email` and `password`
   (password must be at least 8 characters). New accounts start with
   $10,000.00 in cash.
2. **Log in** — `POST /login` with the email and password (as form fields,
   not JSON) to get back a JWT access token that expires after 60 minutes.
3. **Use the token** — send it as `Authorization: Bearer <token>` on every
   other request.

### Using the Authorize button in `/docs`

1. Go to `http://localhost:8000/docs`.
2. Open `POST /signup` and create an account (or use one you already made).
3. Click the **Authorize** button near the top of the page.
4. In the dialog, enter your email in the **username** field and your
   password in the **password** field, then click **Authorize**.
5. Close the dialog. Every request you send from `/docs` now includes your
   token automatically, so `/buy`, `/sell`, `/portfolio`, and `/trades` will
   work.
6. To "log out", click **Authorize** again and then **Logout**.

## Tests

```bash
cd backend
pytest
```

Tests never call the real Finnhub API — all HTTP calls are mocked.
