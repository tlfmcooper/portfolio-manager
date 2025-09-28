from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.schemas.holding import Holding
from app.models.holding import Holding as HoldingModel
from app.schemas.holding_extended import HoldingUpdateRequest, AssetSellRequest
from app.utils.dependencies import get_current_active_user
from app.models import User
from app.crud import get_user_portfolio
from app.crud.holding import get_holding, update_holding
from app.crud.transaction import create_transaction
from app.schemas.transaction import TransactionCreate
from datetime import datetime

router = APIRouter()

@router.put("/holdings/{holding_id}", response_model=Holding)
async def edit_holding(
    holding_id: int,
    holding_in: HoldingUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Update a holding's quantity and average cost.
    """
    holding: HoldingModel = await get_holding(db, holding_id)
    if not holding:
        raise HTTPException(status_code=404, detail="Holding not found")

    portfolio = await get_user_portfolio(db, current_user.id)
    if not portfolio or holding.portfolio_id != portfolio.id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this holding")

    holding = await update_holding(db, db_obj=holding, obj_in=holding_in)
    return holding

@router.post("/holdings/sell", response_model=dict)
async def sell_asset(
    sell_request: AssetSellRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Sell an asset from a portfolio.
    """
    portfolio = await get_user_portfolio(db, current_user.id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    # Find the holding to sell from
    holding = await db.execute(
        select(HoldingModel).where(
            HoldingModel.portfolio_id == portfolio.id,
            HoldingModel.ticker == sell_request.ticker.upper().strip()
        )
    ).scalar_one_or_none()

    if not holding or holding.quantity < sell_request.quantity:
        raise HTTPException(status_code=400, detail="Not enough quantity to sell")

    # Update holding quantity
    holding.quantity -= sell_request.quantity
    holding.market_value = holding.quantity * (holding.current_price or sell_request.price)
    holding.cost_basis = holding.quantity * holding.average_cost

    # Create a sell transaction
    transaction_in = TransactionCreate(
        asset_id=holding.asset_id,
        transaction_type="SELL",
        quantity=sell_request.quantity,
        price=sell_request.price,
        transaction_date=datetime.utcnow(),
    )
    await create_transaction(db, portfolio_id=portfolio.id, obj_in=transaction_in)

    await db.commit()

    return {"message": "Asset sold successfully"}