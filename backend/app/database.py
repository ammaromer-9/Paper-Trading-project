import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

# Falls back to a local SQLite file if DATABASE_URL isn't set. Swapping this
# env variable to a PostgreSQL URL later requires no code changes.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./paper_trading.db")

# SQLite needs this flag because it only allows one thread to use a
# connection by default, which doesn't work with FastAPI's request handling.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency that provides a DB session and closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
