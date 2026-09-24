from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class QuoteResponse(BaseModel):
    ticker: str
    price: Decimal


class TradeRequest(BaseModel):
    ticker: str
    shares: int


class TradeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticker: str
    side: str
    shares: int
    price: Decimal
    timestamp: datetime


class HoldingResponse(BaseModel):
    ticker: str
    shares: int
    avg_cost: Decimal
    current_price: Decimal
    market_value: Decimal
    gain_loss: Decimal
    gain_loss_percent: Decimal


class PortfolioResponse(BaseModel):
    cash_balance: Decimal
    holdings: list[HoldingResponse]
    total_value: Decimal
