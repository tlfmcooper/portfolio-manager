"""
Holding CRUD operations continued - Create, Update, Delete.
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from datetime import datetime

from app.models import Holding, Portfolio, Asset
from app.schemas import HoldingCreate, HoldingUpdate
from app.crud.asset import get_or_create_asset, AssetCreate


async def create_holding(db: AsyncSession, portfolio_id: int, holding_create: HoldingCreate) -> Holding:
    """Create a new holding in portfolio."""
    # Get or create the asset
    asset = await get_or_create_asset(
        db, 
        holding_create.asset_ticker,
        AssetCreate(ticker=holding_create.asset_ticker)
    )
    
    # Check if holding already exists
    existing_holding = await get_holding_by_asset(db, portfolio_id, asset.id)
    
    if existing_holding:
        # Update existing holding (add to position)
        new_total_cost = (existing_holding.quantity * existing_holding.average_cost) + \
                        (holding_create.quantity * holding_create.average_cost)
        new_total_quantity = existing_holding.quantity + holding_create.quantity
        new_average_cost = new_total_cost / new_total_quantity
        
        existing_holding.quantity = new_total_quantity
        existing_holding.average_cost = new_average_cost
        existing_holding.updated_at = datetime.utcnow()
        
        if holding_create.target_allocation is not None:
            existing_holding.target_allocation = holding_create.target_allocation
        if holding_create.notes:
            existing_holding.notes = holding_create.notes
        
        await db.commit()
        await db.refresh(existing_holding)
        return existing_holding
    
    # Create new holding
    db_holding = Holding(
        portfolio_id=portfolio_id,
        asset_id=asset.id,
        quantity=holding_create.quantity,
        average_cost=holding_create.average_cost,
        target_allocation=holding_create.target_allocation,
        notes=holding_create.notes,
        cost_basis=holding_create.quantity * holding_create.average_cost,
        market_value=holding_create.quantity * holding_create.average_cost,  # Initial value
    )
    
    db.add(db_holding)
    await db.commit()
    await db.refresh(db_holding)
    
    return db_holding


async def update_holding(db: AsyncSession, holding_id: int, holding_update: HoldingUpdate) -> Optional[Holding]:
    """Update holding information."""
    db_holding = await get_holding(db, holding_id)
    if not db_holding:
        return None
    
    update_data = holding_update.dict(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(db_holding, field, value)
    
    # Recalculate cost basis and market value
    if hasattr(db_holding, 'quantity') and hasattr(db_holding, 'average_cost'):
        db_holding.cost_basis = db_holding.quantity * db_holding.average_cost
        db_holding.market_value = db_holding.quantity * (db_holding.current_price or db_holding.average_cost)
    
    db_holding.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(db_holding)
    
    return db_holding


async def delete_holding(db: AsyncSession, holding_id: int) -> bool:
    """Delete (soft delete) a holding."""
    stmt = (
        update(Holding)
        .where(Holding.id == holding_id)
        .values(is_active=False, updated_at=datetime.utcnow())
    )
    
    result = await db.execute(stmt)
    await db.commit()
    
    return result.rowcount > 0


# Import to avoid circular imports
from app.crud.holding import get_holding_by_asset
