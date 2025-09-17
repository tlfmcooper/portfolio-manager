"""
CRUD operations for asset management.
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, or_
from datetime import datetime

from app.models import Asset
from app.schemas import AssetCreate, AssetUpdate


async def get_asset(db: AsyncSession, asset_id: int) -> Optional[Asset]:
    """Get asset by ID."""
    stmt = select(Asset).where(Asset.id == asset_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_asset_by_ticker(db: AsyncSession, ticker: str) -> Optional[Asset]:
    """Get asset by ticker symbol."""
    stmt = select(Asset).where(Asset.ticker == ticker.upper())
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_assets(db: AsyncSession, skip: int = 0, limit: int = 100, search: str = None) -> List[Asset]:
    """Get multiple assets with optional search."""
    stmt = select(Asset).where(Asset.is_active == True)
    
    if search:
        search_term = f"%{search.upper()}%"
        stmt = stmt.where(
            or_(
                Asset.ticker.like(search_term),
                Asset.name.like(search_term),
                Asset.sector.like(search_term)
            )
        )
    
    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


async def create_asset(db: AsyncSession, asset_create: AssetCreate) -> Asset:
    """Create a new asset."""
    db_asset = Asset(
        ticker=asset_create.ticker.upper(),
        name=asset_create.name,
        asset_type=asset_create.asset_type,
        sector=asset_create.sector,
        industry=asset_create.industry,
        currency=asset_create.currency,
        exchange=asset_create.exchange,
    )
    
    db.add(db_asset)
    await db.commit()
    await db.refresh(db_asset)
    
    return db_asset


async def get_or_create_asset(db: AsyncSession, ticker: str, asset_data: Optional[AssetCreate] = None) -> Asset:
    """Get existing asset or create new one."""
    asset = await get_asset_by_ticker(db, ticker)
    
    if asset:
        return asset
    
    # Create new asset
    if not asset_data:
        asset_data = AssetCreate(ticker=ticker)
    
    return await create_asset(db, asset_data)


async def update_asset(db: AsyncSession, asset_id: int, asset_update: AssetUpdate) -> Optional[Asset]:
    """Update asset information."""
    db_asset = await get_asset(db, asset_id)
    if not db_asset:
        return None
    
    update_data = asset_update.dict(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(db_asset, field, value)
    
    db_asset.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(db_asset)
    
    return db_asset
