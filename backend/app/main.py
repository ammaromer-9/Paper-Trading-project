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

app = FastAPI(title="Paper Trading API")

cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, tags=["auth"])
app.include_router(trading.router, tags=["trading"])
app.include_router(portfolio.router, tags=["portfolio"])


@app.get("/")
def root():
    return {"status": "ok"}


@app.get("/health")
def health(db: Session = Depends(get_db)):
    """Used by AWS (or any host) to check the app is up and can reach its database."""
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(status_code=503, detail="Database unavailable")
    return {"status": "ok"}
