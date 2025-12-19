"""
Holdings management API routes.
"""
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from app.core.database import get_db
from app.schemas import HoldingInDB, HoldingCreate, HoldingUpdate
from app.schemas.holding_extended import HoldingUpdateRequest, AssetSellRequest
from app.crud import (
    get_user_portfolio,
    get_portfolio_holdings,
    get_portfolio_holdings_count,
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
from app.services.exchange_rate_service import get_exchange_rate_service
from app.core.redis_client import get_redis_client
import json

router = APIRouter()


@router.get("/")
async def get_holdings(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    currency: Optional[str] = Query(None, description="Display currency (USD or CAD)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: Optional[int] = Query(None, ge=1, le=500, description="Maximum number of records to return")
) -> Any:
    """
    Get holdings in current user's portfolio with pagination.

    Args:
        currency: Optional currency to display values in (USD or CAD)
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return (default: all)

    Returns:
        {
            "items": [...holdings...],
            "total": total_count,
            "skip": skip,
            "limit": limit
        }
    """
    portfolio = await get_user_portfolio(db, current_user.id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )

    # Use portfolio currency if not specified
    display_currency = currency.upper() if currency else portfolio.currency

    # Check Redis cache first (only for non-paginated requests)
    use_cache = skip == 0 and limit is None
    cache_key = f"portfolio:{portfolio.id}:holdings:{display_currency}"
    redis_client = await get_redis_client()

    if use_cache:
        try:
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
        except Exception:
            pass  # Continue without cache if Redis fails

    # Get total count and holdings
    total_count = await get_portfolio_holdings_count(db, portfolio.id)
    holdings = await get_portfolio_holdings(db, portfolio.id, skip=skip, limit=limit)
    exchange_service = get_exchange_rate_service()

    # Pre-fetch all needed exchange rates
    exchange_rates = {}
    currencies_needed = set()
    for holding in holdings:
        if holding.asset:
            currencies_needed.add(holding.asset.currency)

    # Fetch all needed exchange rates upfront
    for curr in currencies_needed:
        if curr != display_currency:
            rate = await exchange_service.get_exchange_rate(curr, display_currency)
            exchange_rates[curr] = rate

    # Calculate cost_basis and market_value with currency conversion
    for holding in holdings:
        # Get asset currency
        asset_currency = holding.asset.currency if holding.asset else "USD"

        # Calculate in original currency
        cost_basis = holding.quantity * holding.average_cost
        market_value = holding.quantity * (holding.current_price or holding.average_cost)

        # Convert to display currency if different using pre-fetched rate
        if asset_currency != display_currency and asset_currency in exchange_rates:
            rate = exchange_rates[asset_currency]
            cost_basis = cost_basis * rate
            market_value = market_value * rate

        holding.cost_basis = cost_basis
        holding.market_value = market_value

        if holding.cost_basis > 0:
            holding.unrealized_gain_loss = holding.market_value - holding.cost_basis
            holding.unrealized_gain_loss_percentage = (holding.unrealized_gain_loss / holding.cost_basis) * 100

    # Convert holdings to dict
    holdings_data = [HoldingInDB.from_orm(h).dict() for h in holdings]

    # Prepare response
    response = {
        "items": holdings_data,
        "total": total_count,
        "skip": skip,
        "limit": limit
    }

    # Cache the result for 5 minutes (only for non-paginated requests)
    if use_cache:
        try:
            await redis_client.set(cache_key, json.dumps(response), ttl=300)
        except Exception:
            pass  # Continue without caching if Redis fails

    return response


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

    This will:
    1. Calculate realized gain/loss using FIFO method
    2. Create a SELL transaction with realized gain/loss
    3. Update holding quantity
    4. Credit the sale proceeds to portfolio cash balance
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

    # Calculate realized gain/loss using FIFO
    from app.crud.transaction import calculate_realized_gain_loss_fifo
    realized_gain_loss = await calculate_realized_gain_loss_fifo(
        db=db,
        portfolio_id=portfolio.id,
        asset_id=holding.asset_id,
        sell_quantity=sell_request.quantity,
        sell_price=sell_request.price
    )

    # Calculate sale proceeds
    sale_proceeds = sell_request.quantity * sell_request.price

    # Update holding quantity
    holding.quantity -= sell_request.quantity
    holding.market_value = holding.quantity * (holding.current_price or sell_request.price)
    holding.cost_basis = holding.quantity * holding.average_cost

    # If quantity becomes 0, mark as inactive or delete
    if holding.quantity == 0:
        holding.is_active = False  # Soft delete

    # Create a sell transaction with realized gain/loss
    transaction_in = TransactionCreate(
        asset_id=holding.asset_id,
        transaction_type="SELL",
        quantity=sell_request.quantity,
        price=sell_request.price,
        transaction_date=datetime.utcnow(),
        realized_gain_loss=realized_gain_loss
    )
    await create_transaction(db, portfolio_id=portfolio.id, obj_in=transaction_in)

    # Credit cash balance with sale proceeds
    from app.crud.portfolio_extended import update_portfolio_cash_balance
    await update_portfolio_cash_balance(
        db=db,
        portfolio_id=portfolio.id,
        amount=sale_proceeds,
        operation="add"
    )

    await db.commit()

    return {
        "message": "Asset sold successfully",
        "quantity_sold": sell_request.quantity,
        "sale_price": sell_request.price,
        "sale_proceeds": sale_proceeds,
        "realized_gain_loss": realized_gain_loss,
        "new_cash_balance": portfolio.cash_balance + sale_proceeds
    }
