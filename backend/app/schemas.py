from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    cash_balance: Decimal


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


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
