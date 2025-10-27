"""
CRUD operations for holding management.
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload
from datetime import datetime

from app.models import Holding, Portfolio, Asset
from app.schemas import HoldingCreate, HoldingUpdate


async def get_holding(db: AsyncSession, holding_id: int) -> Optional[Holding]:
    """Get holding by ID with asset information."""
    stmt = (
        select(Holding)
        .options(selectinload(Holding.asset))
        .where(Holding.id == holding_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_portfolio_holdings(db: AsyncSession, portfolio_id: int) -> List[Holding]:
    """Get all holdings for a portfolio."""
    stmt = (
        select(Holding)
        .options(selectinload(Holding.asset))
        .where(Holding.portfolio_id == portfolio_id)
        .where(Holding.is_active == True)
        .where(Holding.quantity > 0)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_holding_by_asset(db: AsyncSession, portfolio_id: int, asset_id: int) -> Optional[Holding]:
    """Get existing holding for specific asset in portfolio."""
    stmt = (
        select(Holding)
        .where(Holding.portfolio_id == portfolio_id)
        .where(Holding.asset_id == asset_id)
        .where(Holding.is_active == True)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
