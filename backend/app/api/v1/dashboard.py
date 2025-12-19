"""
Dashboard API routes - Batched endpoints for efficient data fetching.
"""
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.utils.dependencies import get_current_active_user
from app.models import User
from app.crud import get_user_portfolio
from app.crud.portfolio_extended import get_portfolio_cash_balance
from app.crud.transaction import (
    get_total_realized_gains,
    get_realized_gains_by_asset
)
from app.core.redis_client import get_redis_client
import json

router = APIRouter()


@router.get("/overview")
async def get_dashboard_overview(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    currency: Optional[str] = Query(None, description="Display currency (USD or CAD)")
) -> Any:
    """
    Get comprehensive dashboard overview data in a single request.

    Returns cash balance, realized gains summary, and detailed realized gains.
    This endpoint combines three separate calls into one for better performance.

    Args:
        currency: Optional currency to display values in (USD or CAD)

    Returns:
        {
            "cash_balance": {...},
            "realized_gains": {...},
            "realized_gains_detailed": {...}
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

    # Check Redis cache first
    cache_key = f"dashboard:overview:{portfolio.id}:{display_currency}"
    redis_client = await get_redis_client()

    try:
        cached_data = await redis_client.get(cache_key)
        if cached_data:
            return json.loads(cached_data)
    except Exception:
        pass  # Continue without cache if Redis fails

    # Fetch all data in parallel would be ideal, but for simplicity we'll fetch sequentially
    # In a production environment, you could use asyncio.gather for parallel fetching

    # 1. Get cash balance
    cash_balance_data = await get_portfolio_cash_balance(
        db=db,
        portfolio_id=portfolio.id,
        display_currency=display_currency
    )

    # 2. Get realized gains summary
    total_realized = await get_total_realized_gains(db, portfolio.id)
    realized_gains_data = {
        "portfolio_id": portfolio.id,
        "total_realized_gains": total_realized,
        "currency": portfolio.currency
    }

    # 3. Get detailed realized gains
    realized_gains_list = await get_realized_gains_by_asset(db, portfolio.id)
    realized_gains_detailed_data = {
        "portfolio_id": portfolio.id,
        "currency": portfolio.currency,
        "realized_gains": realized_gains_list,
        "total": sum(item["realized_gain_loss"] for item in realized_gains_list)
    }

    # Combine all data into a single response
    response = {
        "cash_balance": cash_balance_data,
        "realized_gains": realized_gains_data,
        "realized_gains_detailed": realized_gains_detailed_data
    }

    # Cache the result for 5 minutes (300 seconds)
    try:
        await redis_client.set(cache_key, json.dumps(response), ttl=300)
    except Exception:
        pass  # Continue without caching if Redis fails

    return response
