from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import get_current_user
from app.database import get_db
from app.services import prices

router = APIRouter()


@router.get("/quote/{ticker}", response_model=schemas.QuoteResponse)
def get_quote(ticker: str):
    ticker = ticker.upper()
    price = prices.get_price(ticker)
    return schemas.QuoteResponse(ticker=ticker, price=price)


@router.post("/buy", response_model=schemas.TradeResponse)
def buy(
    trade: schemas.TradeRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    if trade.shares <= 0:
        raise HTTPException(status_code=400, detail="Shares must be a positive integer")

    ticker = trade.ticker.strip().upper()
    price = prices.get_price(ticker)
    cost = price * trade.shares

    if user.cash_balance < cost:
        raise HTTPException(status_code=400, detail="Not enough cash for this trade")

    # Everything below happens in one transaction: if anything fails, the
    # whole buy (cash, holding, trade record) rolls back together.
    user.cash_balance -= cost

    holding = (
        db.query(models.Holding)
        .filter(models.Holding.user_id == user.id, models.Holding.ticker == ticker)
        .first()
    )
    if holding is None:
        holding = models.Holding(
            user_id=user.id, ticker=ticker, shares=trade.shares, avg_cost=price
        )
        db.add(holding)
    else:
        # Weighted average cost: blend the existing cost basis with the new
        # purchase, weighted by how many shares each contributes.
        total_cost = (holding.avg_cost * holding.shares) + cost
        holding.shares += trade.shares
        holding.avg_cost = total_cost / holding.shares

    new_trade = models.Trade(
        user_id=user.id, ticker=ticker, side="buy", shares=trade.shares, price=price
    )
    db.add(new_trade)
    db.commit()
    db.refresh(new_trade)
    return new_trade


@router.post("/sell", response_model=schemas.TradeResponse)
def sell(
    trade: schemas.TradeRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    if trade.shares <= 0:
        raise HTTPException(status_code=400, detail="Shares must be a positive integer")

    ticker = trade.ticker.strip().upper()
    price = prices.get_price(ticker)

    holding = (
        db.query(models.Holding)
        .filter(models.Holding.user_id == user.id, models.Holding.ticker == ticker)
        .first()
    )
    if holding is None or holding.shares < trade.shares:
        raise HTTPException(status_code=400, detail="Not enough shares to sell")

    proceeds = price * trade.shares
    user.cash_balance += proceeds
    holding.shares -= trade.shares

    if holding.shares == 0:
        db.delete(holding)

    new_trade = models.Trade(
        user_id=user.id, ticker=ticker, side="sell", shares=trade.shares, price=price
    )
    db.add(new_trade)
    db.commit()
    db.refresh(new_trade)
    return new_trade
