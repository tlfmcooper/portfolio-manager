"""
Portfolio management API routes.
"""
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas import PortfolioInDB, PortfolioUpdate, PortfolioSummary
from app.crud import (
    get_user_portfolio,
    update_portfolio,
    calculate_portfolio_metrics,
    update_portfolio_metrics
)
from app.utils.dependencies import get_current_active_user
from app.models import User
from app.services.portfolio_analysis import AdvancedPortfolioAnalytics

router = APIRouter()


@router.get("/", response_model=PortfolioInDB)
async def get_portfolio(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get current user's portfolio.
    """
    portfolio = await get_user_portfolio(db, current_user.id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )
    return portfolio


@router.put("/", response_model=PortfolioInDB)
async def update_user_portfolio(
    portfolio_update: PortfolioUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Update current user's portfolio.
    """
    portfolio = await get_user_portfolio(db, current_user.id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )
    
    updated_portfolio = await update_portfolio(db, portfolio.id, portfolio_update)
    if not updated_portfolio:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update portfolio"
        )
    
    return updated_portfolio


@router.get("/summary", response_model=PortfolioSummary)
async def get_portfolio_summary(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get portfolio summary with key metrics.
    """
    portfolio = await get_user_portfolio(db, current_user.id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )
    
    # Update portfolio metrics before returning summary
    await update_portfolio_metrics(db, portfolio.id)
    
    # Refresh portfolio data
    updated_portfolio = await get_user_portfolio(db, current_user.id)
    
    return {
        "id": updated_portfolio.id,
        "name": updated_portfolio.name,
        "total_value": updated_portfolio.total_value,
        "total_return": updated_portfolio.total_return,
        "total_return_percentage": updated_portfolio.total_return_percentage,
        "total_holdings_count": updated_portfolio.total_holdings_count,
        "diversification_score": updated_portfolio.diversification_score,
        "currency": updated_portfolio.currency,
        "last_updated": updated_portfolio.updated_at,
    }


@router.get("/metrics", response_model=Dict)
async def get_portfolio_metrics(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get detailed portfolio metrics and analysis.
    """
    portfolio = await get_user_portfolio(db, current_user.id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )
    
    metrics = await calculate_portfolio_metrics(db, portfolio.id)
    return metrics


@router.post("/refresh-metrics")
async def refresh_portfolio_metrics(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Refresh portfolio metrics (recalculate all values).
    """
    portfolio = await get_user_portfolio(db, current_user.id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )
    
    success = await update_portfolio_metrics(db, portfolio.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh portfolio metrics"
        )
    
    return {"message": "Portfolio metrics refreshed successfully"}


@router.get("/analysis", response_model=Dict)
async def get_portfolio_analysis(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get comprehensive portfolio analysis with advanced metrics.
    """
    portfolio = await get_user_portfolio(db, current_user.id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )
    
    analysis = AdvancedPortfolioAnalytics(portfolio.id, db)
    metrics = await analysis.calculate_portfolio_metrics()
    return metrics
