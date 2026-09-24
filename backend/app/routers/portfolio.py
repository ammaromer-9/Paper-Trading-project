from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import get_current_user
from app.database import get_db
from app.services import prices

router = APIRouter()


@router.get("/portfolio", response_model=schemas.PortfolioResponse)
def get_portfolio(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    holdings_out = []
    holdings_value = Decimal("0")

    for holding in user.holdings:
        current_price = prices.get_price(holding.ticker)
        market_value = current_price * holding.shares
        cost_basis = holding.avg_cost * holding.shares
        gain_loss = market_value - cost_basis
        gain_loss_percent = (gain_loss / cost_basis * 100) if cost_basis else Decimal("0")

        holdings_out.append(
            schemas.HoldingResponse(
                ticker=holding.ticker,
                shares=holding.shares,
                avg_cost=holding.avg_cost,
                current_price=current_price,
                market_value=market_value,
                gain_loss=gain_loss,
                gain_loss_percent=gain_loss_percent,
            )
        )
        holdings_value += market_value

    return schemas.PortfolioResponse(
        cash_balance=user.cash_balance,
        holdings=holdings_out,
        total_value=user.cash_balance + holdings_value,
    )


@router.get("/trades", response_model=list[schemas.TradeResponse])
def get_trades(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    return (
        db.query(models.Trade)
        .filter(models.Trade.user_id == user.id)
        .order_by(models.Trade.timestamp.desc())
        .all()
    )
