"""
Holdings management API routes.
"""
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from app.core.database import get_db
from app.schemas import HoldingInDB, HoldingCreate, HoldingUpdate
from app.schemas.holding_extended import HoldingUpdateRequest, AssetSellRequest
from app.crud import (
    get_user_portfolio,
    get_portfolio_holdings,
    get_holding,
    create_holding,
    update_holding,
    delete_holding
)
from app.crud.transaction import create_transaction
from app.schemas.transaction import TransactionCreate
from app.utils.dependencies import get_current_active_user
from app.models import User
from app.models.holding import Holding as HoldingModel

router = APIRouter()


@router.get("/", response_model=List[HoldingInDB])
async def get_holdings(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get all holdings in current user's portfolio.
    """
    portfolio = await get_user_portfolio(db, current_user.id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )

    holdings = await get_portfolio_holdings(db, portfolio.id)

    # CRITICAL FIX: Always calculate cost_basis and market_value from database fields before returning
    for holding in holdings:
        holding.cost_basis = holding.quantity * holding.average_cost
        holding.market_value = holding.quantity * (holding.current_price or holding.average_cost)
        if holding.cost_basis > 0:
            holding.unrealized_gain_loss = holding.market_value - holding.cost_basis
            holding.unrealized_gain_loss_percentage = (holding.unrealized_gain_loss / holding.cost_basis) * 100

    return holdings


@router.post("/", response_model=HoldingInDB)
async def create_user_holding(
    holding_create: HoldingCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Create a new holding in current user's portfolio.
    """
    portfolio = await get_user_portfolio(db, current_user.id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )
    
    holding = await create_holding(db, portfolio.id, holding_create)
    return holding


@router.get("/{holding_id}", response_model=HoldingInDB)
async def get_holding_detail(
    holding_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get specific holding by ID.
    """
    holding = await get_holding(db, holding_id)
    if not holding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Holding not found"
        )

    # Verify holding belongs to current user
    portfolio = await get_user_portfolio(db, current_user.id)
    if not portfolio or holding.portfolio_id != portfolio.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this holding"
        )

    # CRITICAL FIX: Always calculate cost_basis and market_value from database fields before returning
    holding.cost_basis = holding.quantity * holding.average_cost
    holding.market_value = holding.quantity * (holding.current_price or holding.average_cost)
    if holding.cost_basis > 0:
        holding.unrealized_gain_loss = holding.market_value - holding.cost_basis
        holding.unrealized_gain_loss_percentage = (holding.unrealized_gain_loss / holding.cost_basis) * 100

    return holding


@router.put("/{holding_id}", response_model=HoldingInDB)
async def update_user_holding(
    holding_id: int,
    holding_update: HoldingUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Update a specific holding.
    """
    holding = await get_holding(db, holding_id)
    if not holding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Holding not found"
        )
    
    # Verify holding belongs to current user
    portfolio = await get_user_portfolio(db, current_user.id)
    if not portfolio or holding.portfolio_id != portfolio.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this holding"
        )
    
    updated_holding = await update_holding(db, holding_id, holding_update)
    if not updated_holding:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update holding"
        )
    
    return updated_holding


@router.delete("/{holding_id}")
async def delete_user_holding(
    holding_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Delete a specific holding.
    """
    holding = await get_holding(db, holding_id)
    if not holding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Holding not found"
        )
    
    # Verify holding belongs to current user
    portfolio = await get_user_portfolio(db, current_user.id)
    if not portfolio or holding.portfolio_id != portfolio.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this holding"
        )
    
    success = await delete_holding(db, holding_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete holding"
        )
    
    return {"message": "Holding deleted successfully"}


@router.put("/{holding_id}/edit", response_model=HoldingInDB)
async def edit_holding_details(
    holding_id: int,
    holding_in: HoldingUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Update a holding's quantity and average cost (for corrections).
    """
    holding: HoldingModel = await get_holding(db, holding_id)
    if not holding:
        raise HTTPException(status_code=404, detail="Holding not found")

    portfolio = await get_user_portfolio(db, current_user.id)
    if not portfolio or holding.portfolio_id != portfolio.id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this holding")

    # Update the holding with new values
    holding.quantity = holding_in.quantity
    holding.average_cost = holding_in.average_cost
    holding.cost_basis = holding.quantity * holding.average_cost
    holding.market_value = holding.quantity * (holding.current_price or holding.average_cost)
    
    await db.commit()
    await db.refresh(holding)
    return holding


@router.post("/sell", response_model=dict)
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
    result = await db.execute(
        select(HoldingModel).where(
            HoldingModel.portfolio_id == portfolio.id,
            HoldingModel.ticker == sell_request.ticker.upper().strip()
        )
    )
    holding = result.scalar_one_or_none()

    if not holding or holding.quantity < sell_request.quantity:
        raise HTTPException(status_code=400, detail="Not enough quantity to sell")

    # Update holding quantity
    holding.quantity -= sell_request.quantity
    holding.market_value = holding.quantity * (holding.current_price or sell_request.price)
    holding.cost_basis = holding.quantity * holding.average_cost

    # If quantity becomes 0, we could optionally delete the holding
    if holding.quantity == 0:
        await db.delete(holding)
    
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
