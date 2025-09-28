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
from app.models.transaction import Transaction
from app.services.finance_service import FinanceService
from pydantic import BaseModel
from typing import List
from datetime import datetime
import logging

from app.utils.dependencies import get_current_active_user # Import current user dependency
from app.models import User # Import User model
from app.crud import get_user_portfolio, create_portfolio # Import portfolio CRUD operations
from app.schemas import PortfolioCreate # Import schema for creating portfolio

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
    data: List[AssetOnboardingRequest],
    current_user: User = Depends(get_current_active_user), # Get current user
    db: AsyncSession = Depends(get_db)
):
    """
    Onboard multiple assets with their holdings.
    Fetches asset data from Yahoo Finance and creates holdings.
    """
    created_assets = []
    errors = []

    # Find or create portfolio for the current user
    portfolio = await get_user_portfolio(db, current_user.id)
    if not portfolio:
        # Create a default portfolio for the user
        default_portfolio_name = f"{current_user.username}'s Portfolio"
        portfolio_create_schema = PortfolioCreate(
            name=default_portfolio_name,
            description="Default portfolio created during onboarding",
            initial_value=0.0,
            currency="USD",
            risk_tolerance="Moderate",
            investment_objective="Growth",
            time_horizon="Long-term"
        )
        portfolio = await create_portfolio(db, current_user.id, portfolio_create_schema)
        logger.info(f"Created new default portfolio for user {current_user.id}: {portfolio.id}")

    portfolio_id = portfolio.id

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
            # Check if holding already exists for this portfolio and ticker
            existing_holding_stmt = select(Holding).where(
                Holding.portfolio_id == portfolio_id,
                Holding.ticker == ticker
            )
            existing_holding = (await db.execute(existing_holding_stmt)).scalar_one_or_none()

            if existing_holding:
                # Update existing holding
                new_total_quantity = existing_holding.quantity + item.quantity
                new_total_cost = (existing_holding.quantity * existing_holding.average_cost) + \
                                 (item.quantity * item.unit_cost)
                new_average_cost = new_total_cost / new_total_quantity

                existing_holding.quantity = new_total_quantity
                existing_holding.average_cost = new_average_cost
                existing_holding.cost_basis = new_total_quantity * new_average_cost
                existing_holding.market_value = new_total_quantity * (asset_obj.current_price or new_average_cost)
                existing_holding.current_price = asset_obj.current_price # Update current price
                
                holding_to_use = existing_holding
                logger.info(f"Updated existing holding for {ticker}. New quantity: {new_total_quantity}")
            else:
                # Create new holding
                holding = Holding(
                    asset_id=asset_obj.id,
                    ticker=asset_obj.ticker,
                                    quantity=item.quantity,
                                    average_cost=item.unit_cost,
                                    portfolio_id=portfolio_id,
                                    cost_basis=item.quantity * item.unit_cost,                    market_value=item.quantity
                    * (asset_obj.current_price or item.unit_cost),
                    current_price=asset_obj.current_price,
                )
                db.add(holding)
                holding_to_use = holding
                logger.info(f"Created new holding for {ticker}.")

            await db.flush()  # Ensure holding_to_use has an ID if new, or is updated

            # Create transaction (buy)
            transaction = Transaction(
                portfolio_id=holding_to_use.portfolio_id,
                asset_id=asset_obj.id,
                transaction_type="BUY",
                quantity=item.quantity,
                price=item.unit_cost,
                transaction_date=datetime.utcnow(),
            )
            db.add(transaction)
            await db.flush()
            created_assets.append(
                {
                    "ticker": ticker,
                    "name": asset_obj.name or ticker,
                    "quantity": item.quantity, # This quantity is for the current transaction
                    "unit_cost": item.unit_cost,
                    "current_price": asset_obj.current_price,
                    "market_value": holding_to_use.market_value,
                    "asset_id": asset_obj.id,
                    "holding_id": holding_to_use.id,
                    "transaction_id": transaction.id,
                }
            )
            logger.info(
                f"Successfully processed {ticker}: {item.quantity} shares at ${item.unit_cost}"
            )
        except Exception as e:
            logger.error(f"Error processing {item.ticker}: {str(e)}")
            errors.append(f"Error processing {item.ticker}: {str(e)}")
    if created_assets:
        await db.commit()
    return {"assets": created_assets, "errors": errors}


@router.post("/sell", status_code=201, response_model=dict)
async def sell_asset(data: AssetOnboardingRequest, db: AsyncSession = Depends(get_db)):
    """
    Sell (delete) asset from holdings and create a sell transaction.
    """
    try:
        ticker = data.ticker.upper().strip()
        # Find holding
        stmt = select(Holding).where(
            Holding.ticker == ticker, Holding.portfolio_id == 1
        )
        result = await db.execute(stmt)
        holding = result.scalar_one_or_none()
        if not holding or holding.quantity < data.quantity:
            raise HTTPException(status_code=400, detail="Not enough quantity to sell")
        # Update holding
        holding.quantity -= data.quantity
        holding.market_value = holding.quantity * (
            holding.current_price or data.unit_cost
        )
        holding.cost_basis = holding.quantity * holding.average_cost
        # Create transaction (sell)
        transaction = Transaction(
            portfolio_id=holding.portfolio_id,
            asset_id=holding.asset_id, # Use asset_id instead of ticker
            transaction_type="SELL",
            quantity=data.quantity,
            price=data.unit_cost,
            transaction_date=datetime.utcnow(),
        )
        db.add(transaction)
        await db.commit()
        return {
            "success": True,
            "message": f"Sold {data.quantity} of {ticker}",
            "transaction_id": transaction.id,
        }
    except Exception as e:
        logger.error(f"Error selling {data.ticker}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error selling {data.ticker}: {str(e)}"
        )


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
