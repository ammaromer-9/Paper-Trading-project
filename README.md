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

   The API docs are then available at `http://localhost:8000/api/docs`.

   Every route is served under `/api` (e.g. `/api/signup`, `/api/quote/{ticker}`)
   so that in production, one CloudFront distribution can route `/api/*` to
   this backend and everything else to the S3-hosted frontend, both under a
   single domain. See [Deployment](#deployment) below.

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

Every endpoint except `GET /api/quote/{ticker}` requires a logged-in user.

1. **Sign up** — `POST /api/signup` with a JSON body of `email` and
   `password` (password must be at least 8 characters). New accounts start
   with $10,000.00 in cash.
2. **Log in** — `POST /api/login` with the email and password (as form
   fields, not JSON) to get back a JWT access token that expires after 60
   minutes by default.
3. **Use the token** — send it as `Authorization: Bearer <token>` on every
   other request.

### Using the Authorize button in `/api/docs`

1. Go to `http://localhost:8000/api/docs`.
2. Open `POST /api/signup` and create an account (or use one you already made).
3. Click the **Authorize** button near the top of the page.
4. In the dialog, enter your email in the **username** field and your
   password in the **password** field, then click **Authorize**.
5. Close the dialog. Every request you send from `/api/docs` now includes
   your token automatically, so `/api/buy`, `/api/sell`, `/api/portfolio`,
   and `/api/trades` will work.
6. To "log out", click **Authorize** again and then **Logout**.

## Tests

```bash
cd backend
pytest
```

Tests never call the real Finnhub API — all HTTP calls are mocked.

## Frontend

A React (Vite) app in `frontend/` that talks to the backend above.

1. Install dependencies and copy the example env file:

   ```bash
   cd frontend
   npm install
   cp .env.example .env
   ```

   `VITE_API_URL` in `.env` defaults to `http://localhost:8000/api` for
   local development, matching the backend above. Vite reads this at
   **build time**, not runtime — it gets compiled directly into the
   JavaScript bundle. In production, the frontend and backend share one
   domain behind CloudFront (see [Deployment](#deployment)), so the
   production build instead uses a relative path:

   ```bash
   VITE_API_URL=/api npm run build
   ```

2. Run the dev server (with the backend already running in another
   terminal):

   ```bash
   npm run dev
   ```

   The app is then available at `http://localhost:5173`.

3. Build for production:

   ```bash
   npm run build
   ```

## Deployment

### Environment variables

The backend is entirely configured through environment variables (see
`backend/.env.example` for the full list with comments). Two are required —
the app refuses to start without them:

| Variable | Required? | Purpose |
|---|---|---|
| `DATABASE_URL` | No (defaults to local SQLite) | `sqlite:///./paper_trading.db` locally, or a `postgresql://user:password@host:5432/dbname` URL in production |
| `JWT_SECRET` | **Yes** | Signs login tokens |
| `FINNHUB_API_KEY` | **Yes** | Live stock prices |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No (defaults to 60) | How long a login token stays valid |
| `CORS_ORIGINS` | No (defaults to the local Vite dev server) | Comma-separated list of frontend origins allowed to call the API |

`CORS_ORIGINS` only matters for local development, where the frontend
(`localhost:5173`) and backend (`localhost:8000`) are different origins. In
production the frontend and `/api/*` are served from the same CloudFront
domain, so the browser treats every request as same-origin and never
triggers CORS in the first place.

### Database: SQLite vs. PostgreSQL

The same code works against either — SQLAlchemy picks the right driver from
the `DATABASE_URL` scheme (`sqlite://` vs. `postgresql://`), and the model
columns use `Numeric`, not `Float`, so money stays an exact decimal in both
SQLite and PostgreSQL (PostgreSQL's `NUMERIC` type is exact, unlike a
floating-point type).

There's no migration tool (like Alembic) in this project — on startup, the
app just creates any tables that don't already exist
(`Base.metadata.create_all`) and leaves existing ones alone. That's fine
while the schema is simple and you're the only one touching the database.
A migration tool becomes worth adding once you need to **change** an
existing table in production without losing data — e.g. adding a new
required column to a table that already has rows, renaming a column, or
coordinating a schema change across multiple running app instances. Alembic
generates versioned scripts for exactly that: each migration knows how to
apply a change and how to undo it, so you can upgrade (or roll back)
production safely instead of hand-editing the database.

### Health check

`GET /api/health` returns `{"status": "ok"}` if the app can reach its database,
or a 503 if it can't. Point your host's health check (e.g. an AWS load
balancer or ECS task definition) at this endpoint so it knows when the app
is actually ready to serve traffic, not just that the process started.

### Docker

```bash
cd backend
docker build -t paper-trading-backend .
docker run --env-file .env -p 8000:8000 paper-trading-backend
```

The `Dockerfile`:
- Starts from `python:3.13-slim` — a small image with just enough Debian and
  Python to run the app, not the full-size default image.
- Creates a non-root user (`appuser`) and switches to it before running the
  app, so a compromised container process doesn't run as root.
- Copies `requirements.txt` and installs dependencies *before* copying the
  app code, so Docker can reuse that (slow) layer from cache when only your
  code changes, not your dependencies.
- Copies the `app/` directory in, owned by `appuser`.
- Runs `uvicorn` bound to `0.0.0.0` (so it's reachable from outside the
  container) on port 8000, without `--reload` (that's a dev-only feature
  that watches files for changes — unnecessary overhead in production).

`.dockerignore` keeps `.env`, the local SQLite file, `.venv`, caches, and
`tests/` out of the image — none of that belongs in a production container.

**Don't have Docker installed?** Install [Docker Desktop](https://www.docker.com/products/docker-desktop/)
(Mac/Windows) or Docker Engine (Linux), then come back to test the image
locally before deploying.

### CloudFront routing

One CloudFront distribution sits in front of everything: the default
behavior serves the React build from an S3 bucket, and a `/api/*` behavior
routes to the EC2 instance running the backend container. Same domain for
both, which is also why `CORS_ORIGINS` isn't needed in production (see
above).

That setup needs one extra piece: React Router handles routes like
`/dashboard` entirely client-side, and there's no actual `/dashboard` file
in the S3 bucket. Refreshing the page on a route like that would normally
ask S3 for a file that doesn't exist and get a 404. `deploy/cloudfront-spa-rewrite.js`
is a CloudFront Function that rewrites any request for a path with no file
extension to `/index.html` instead, so the app's JavaScript loads and React
Router takes it from there.

Attach this function to the S3 (default) behavior only, as a **viewer
request** function - never to `/api/*`. A tempting alternative is
CloudFront's built-in "custom error responses" (e.g. turn a 403/404 into
`/index.html`), but that setting applies to the *whole distribution*, not
one behavior - it would also catch a real 404 from the API, like `/api/quote/ZZZZ`
returning "Ticker not found", and silently turn it into an HTML page instead
of the JSON error the frontend expects.

## Screenshots

_Add screenshots of the app here._
