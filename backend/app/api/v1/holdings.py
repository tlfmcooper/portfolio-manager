"""
Holdings management API routes.
"""
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas import HoldingInDB, HoldingCreate, HoldingUpdate
from app.crud import (
    get_user_portfolio,
    get_portfolio_holdings,
    get_holding,
    create_holding,
    update_holding,
    delete_holding
)
from app.utils.dependencies import get_current_active_user
from app.models import User

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
