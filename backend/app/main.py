import os

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.routers import auth, portfolio, trading

load_dotenv()

# Creates any tables that don't already exist on startup - works against
# both SQLite and PostgreSQL. See the README for when this stops being
# enough and a migration tool (e.g. Alembic) becomes worth adding.
Base.metadata.create_all(bind=engine)

# Everything lives under /api so CloudFront can route "/api/*" to this
# backend and everything else to the S3-hosted frontend, both behind one
# domain. This also covers the docs and OpenAPI schema, so /api/docs works
# through CloudFront the same way it does when hitting the backend directly.
API_PREFIX = "/api"

app = FastAPI(
    title="Paper Trading API",
    docs_url=f"{API_PREFIX}/docs",
    redoc_url=f"{API_PREFIX}/redoc",
    openapi_url=f"{API_PREFIX}/openapi.json",
)

# Only needed for local development, where the frontend (localhost:5173)
# and backend (localhost:8000) are different origins. In production,
# CloudFront serves both the frontend and /api/* from the same domain, so
# the browser sees it as one origin and never sends a CORS preflight -
# CORS_ORIGINS then has nothing to do.
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=API_PREFIX, tags=["auth"])
app.include_router(trading.router, prefix=API_PREFIX, tags=["trading"])
app.include_router(portfolio.router, prefix=API_PREFIX, tags=["portfolio"])


@app.get(API_PREFIX)
def root():
    return {"status": "ok"}


@app.get(f"{API_PREFIX}/health")
def health(db: Session = Depends(get_db)):
    """Used by AWS (or any host) to check the app is up and can reach its database."""
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(status_code=503, detail="Database unavailable")
    return {"status": "ok"}
