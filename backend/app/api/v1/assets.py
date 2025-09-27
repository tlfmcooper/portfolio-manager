"""
API endpoints for asset onboarding (ticker, quantity, unit cost).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.models.asset import Asset
from app.models.holding import Holding
from app.services.finance_service import FinanceService
from pydantic import BaseModel
from typing import List
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


class AssetOnboardingRequest(BaseModel):
    ticker: str
    quantity: float
    unit_cost: float


class AssetOnboardingResponse(BaseModel):
    ticker: str
    name: str
    quantity: float
    unit_cost: float
    current_price: float
    market_value: float
    asset_id: int
    holding_id: int


@router.post("/onboard", status_code=201, response_model=dict)
async def onboard_asset(
    data: List[AssetOnboardingRequest], db: AsyncSession = Depends(get_db)
):
    """
    Onboard multiple assets with their holdings.
    Fetches asset data from Yahoo Finance and creates holdings.
    """
    created_assets = []
    errors = []

    for item in data:
        try:
            ticker = item.ticker.upper().strip()

            # Check if asset already exists
            stmt = select(Asset).where(Asset.ticker == ticker)
            result = await db.execute(stmt)
            asset_obj = result.scalar_one_or_none()

            if not asset_obj:
                # Fetch asset data from Yahoo Finance
                logger.info(f"Fetching data for new ticker: {ticker}")
                asset_data = await FinanceService.get_asset_info(ticker)

                if not asset_data:
                    errors.append(f"Could not fetch data for ticker: {ticker}")
                    continue

                # Merge form data (quantity, unit_cost) into asset_data
                asset_obj = Asset(**asset_data)
                db.add(asset_obj)
                await db.flush()  # Get the ID
                logger.info(f"Created new asset: {ticker} with ID: {asset_obj.id}")
            else:
                # Update existing asset with fresh data if needed
                if not asset_obj.current_price:
                    current_price = await FinanceService.get_current_price(ticker)
                    if current_price:
                        asset_obj.current_price = current_price
            # Create holding
            holding = Holding(
                asset_id=asset_obj.id,
                quantity=item.quantity,
                average_cost=item.unit_cost,
                portfolio_id=1,  # TODO: Replace with actual portfolio/user logic
                cost_basis=item.quantity * item.unit_cost,
                market_value=item.quantity
                * (asset_obj.current_price or item.unit_cost),
                current_price=asset_obj.current_price,
            )
            db.add(holding)
            await db.flush()  # Get the holding ID
            created_assets.append(
                {
                    "ticker": ticker,
                    "name": asset_obj.name or ticker,
                    "quantity": item.quantity,
                    "unit_cost": item.unit_cost,
                    "current_price": asset_obj.current_price,
                    "market_value": holding.market_value,
                    "asset_id": asset_obj.id,
                    "holding_id": holding.id,
                }
            )
            logger.info(
                f"Successfully onboarded {ticker}: {item.quantity} shares at ${item.unit_cost}"
            )
        except Exception as e:
            logger.error(f"Error processing {item.ticker}: {str(e)}")
            errors.append(f"Error processing {item.ticker}: {str(e)}")
    if created_assets:
        await db.commit()
    return {"assets": created_assets, "errors": errors}


@router.get("/refresh/{ticker}")
async def refresh_asset_data(ticker: str, db: AsyncSession = Depends(get_db)):
    """Refresh asset data from Yahoo Finance."""
    try:
        # Find the asset
        stmt = select(Asset).where(Asset.ticker == ticker.upper())
        result = await db.execute(stmt)
        asset_obj = result.scalar_one_or_none()

        if not asset_obj:
            raise HTTPException(status_code=404, detail=f"Asset {ticker} not found")

        # Fetch fresh data
        asset_data = await FinanceService.get_asset_info(ticker)
        if not asset_data:
            raise HTTPException(
                status_code=400, detail=f"Could not fetch data for {ticker}"
            )

        # Update asset fields
        for key, value in asset_data.items():
            if key != "ticker" and hasattr(asset_obj, key):
                setattr(asset_obj, key, value)

        await db.commit()

        return {
            "success": True,
            "message": f"Successfully refreshed data for {ticker}",
            "asset": {
                "ticker": asset_obj.ticker,
                "name": asset_obj.name,
                "current_price": asset_obj.current_price,
                "market_cap": asset_obj.market_cap,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing asset {ticker}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Internal error refreshing {ticker}"
        )
