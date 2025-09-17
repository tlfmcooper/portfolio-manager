"""
Portfolio CRUD operations continued - Update, Delete, Analysis.
"""
from typing import Optional, List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from datetime import datetime

from app.models import Portfolio, Holding, Asset
from app.schemas import PortfolioUpdate


async def update_portfolio(db: AsyncSession, portfolio_id: int, portfolio_update: PortfolioUpdate) -> Optional[Portfolio]:
    """Update portfolio information."""
    db_portfolio = await get_portfolio(db, portfolio_id)
    if not db_portfolio:
        return None
    
    update_data = portfolio_update.dict(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(db_portfolio, field, value)
    
    db_portfolio.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(db_portfolio)
    
    return db_portfolio


async def calculate_portfolio_metrics(db: AsyncSession, portfolio_id: int) -> Dict:
    """Calculate portfolio performance metrics."""
    portfolio = await get_portfolio(db, portfolio_id)
    if not portfolio or not portfolio.holdings:
        return {
            "total_invested": 0.0,
            "total_value": 0.0,
            "total_return": 0.0,
            "total_return_percentage": 0.0,
            "asset_allocation": {},
            "holdings_count": 0,
        }
    
    total_cost = 0.0
    total_value = 0.0
    asset_allocation = {}
    
    for holding in portfolio.holdings:
        if not holding.is_active:
            continue
            
        cost = holding.quantity * holding.average_cost
        current_value = holding.quantity * (holding.current_price or holding.average_cost)
        
        total_cost += cost
        total_value += current_value
        
        # Calculate allocation percentage
        if holding.asset:
            asset_allocation[holding.asset.ticker] = current_value
    
    # Convert allocations to percentages
    if total_value > 0:
        asset_allocation = {
            ticker: (value / total_value) * 100 
            for ticker, value in asset_allocation.items()
        }
    
    total_return = total_value - total_cost
    total_return_percentage = (total_return / total_cost * 100) if total_cost > 0 else 0.0
    
    return {
        "total_invested": total_cost,
        "total_value": total_value,
        "total_return": total_return,
        "total_return_percentage": total_return_percentage,
        "asset_allocation": asset_allocation,
        "holdings_count": len([h for h in portfolio.holdings if h.is_active]),
    }


async def update_portfolio_metrics(db: AsyncSession, portfolio_id: int) -> bool:
    """Update cached portfolio metrics."""
    metrics = await calculate_portfolio_metrics(db, portfolio_id)
    
    stmt = (
        update(Portfolio)
        .where(Portfolio.id == portfolio_id)
        .values(
            total_invested=metrics["total_invested"],
            total_value=metrics["total_value"],
            total_return=metrics["total_return"],
            total_return_percentage=metrics["total_return_percentage"],
            updated_at=datetime.utcnow()
        )
    )
    
    result = await db.execute(stmt)
    await db.commit()
    
    return result.rowcount > 0


# Import to avoid circular imports
from app.crud.portfolio import get_portfolio
