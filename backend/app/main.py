import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import portfolio, trading

load_dotenv()

# Creates the SQLite tables on startup if they don't already exist.
# (We'll move to proper migrations if/when we switch to PostgreSQL.)
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

app.include_router(trading.router, tags=["trading"])
app.include_router(portfolio.router, tags=["portfolio"])


@app.get("/")
def root():
    return {"status": "ok"}
