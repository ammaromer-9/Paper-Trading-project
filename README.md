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

## Tests

```bash
cd backend
pytest
```

Tests never call the real Finnhub API — all HTTP calls are mocked.
