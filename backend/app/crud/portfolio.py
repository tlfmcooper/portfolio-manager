"""
CRUD operations for portfolio management.
"""
from typing import Optional, List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from sqlalchemy.orm import selectinload
from datetime import datetime

from app.models import Portfolio, Holding, Asset
from app.schemas import PortfolioCreate, PortfolioUpdate


async def get_portfolio(db: AsyncSession, portfolio_id: int) -> Optional[Portfolio]:
    """Get portfolio by ID with holdings."""
    stmt = (
        select(Portfolio)
        .options(selectinload(Portfolio.holdings).selectinload(Holding.asset))
        .where(Portfolio.id == portfolio_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_portfolio(db: AsyncSession, user_id: int) -> Optional[Portfolio]:
    """Get user's portfolio with holdings."""
    stmt = (
        select(Portfolio)
        .options(selectinload(Portfolio.holdings).selectinload(Holding.asset))
        .where(Portfolio.user_id == user_id)
        .where(Portfolio.is_active == True)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_portfolio(db: AsyncSession, user_id: int, portfolio_create: PortfolioCreate) -> Portfolio:
    """Create a new portfolio for user."""
    db_portfolio = Portfolio(
        user_id=user_id,
        name=portfolio_create.name,
        description=portfolio_create.description,
        initial_value=portfolio_create.initial_value,
        currency=portfolio_create.currency,
        risk_tolerance=portfolio_create.risk_tolerance,
        investment_objective=portfolio_create.investment_objective,
        time_horizon=portfolio_create.time_horizon,
    )
    
    db.add(db_portfolio)
    await db.commit()
    await db.refresh(db_portfolio)
    
    return db_portfolio
