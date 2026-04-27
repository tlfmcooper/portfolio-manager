"""
API endpoints for asset onboarding (ticker, quantity, unit cost).
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Body, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.models.asset import Asset
from app.models.holding import Holding
from app.models.transaction import Transaction, TransactionType
from app.schemas.holding_extended import AssetSellRequest
from app.services.finance_service import FinanceService
from pydantic import BaseModel
from typing import List, Optional, Dict, Tuple
from datetime import datetime
import logging
import csv
import io
import asyncio

from app.utils.dependencies import get_current_active_user # Import current user dependency
from app.models import User # Import User model
from app.crud import get_user_portfolio, create_portfolio # Import portfolio CRUD operations
from app.schemas import PortfolioCreate # Import schema for creating portfolio

logger = logging.getLogger(__name__)
router = APIRouter()


async def invalidate_portfolio_transaction_caches(portfolio_id: int):
    """Invalidate cached portfolio data after buy/sell cash mutations."""
    try:
        from app.core.redis_client import get_redis_client

        redis_client = await get_redis_client()
        for currency in ["USD", "CAD"]:
            await redis_client.delete(f"dashboard:overview:{portfolio_id}:{currency}")
            await redis_client.delete(f"portfolio:{portfolio_id}:holdings:{currency}")
        await redis_client.delete(f"portfolio:{portfolio_id}:returns_cache")
        await redis_client.delete(f"portfolio:{portfolio_id}:analytics_cache")
    except Exception as e:
        logger.warning(f"Failed to invalidate portfolio caches for {portfolio_id}: {e}")


async def convert_amount_to_portfolio_currency(
    amount: float,
    amount_currency: str,
    portfolio_currency: str
) -> Tuple[float, float]:
    """Convert an amount into the portfolio currency."""
    source_currency = (amount_currency or portfolio_currency or "USD").upper()
    target_currency = (portfolio_currency or "USD").upper()

    if source_currency == target_currency:
        return amount, 1.0

    from app.services.exchange_rate_service import get_exchange_rate_service

    exchange_service = get_exchange_rate_service()
    exchange_rate = await exchange_service.get_exchange_rate(source_currency, target_currency)
    return amount * exchange_rate, exchange_rate


class AssetOnboardingRequest(BaseModel):
    ticker: str
    quantity: float
    average_cost: float  # Changed from unit_cost to match update route
    asset_type: Optional[str] = "Stock"  # Stock, Mutual Fund, Crypto
    currency: Optional[str] = "USD"  # USD, CAD, EUR, etc.


class AssetOnboardingResponse(BaseModel):
    ticker: str
    name: str
    quantity: float
    average_cost: float
    current_price: float
    market_value: float
    asset_id: int
    holding_id: int


def normalize_asset_type(asset_type: str) -> str:
    """
    Normalize asset type from CSV format to internal format.
    Maps: "Stock" -> "stock", "Mutual Fund" -> "mutual_fund", "Crypto" -> "crypto"
    """
    normalized = asset_type.lower().strip()

    # Map common variations
    type_mapping = {
        'stock': 'stock',
        'mutual fund': 'mutual_fund',
        'mutualfund': 'mutual_fund',
        'mutual_fund': 'mutual_fund',
        'crypto': 'crypto',
        'cryptocurrency': 'crypto',
        'etf': 'etf',
        'bond': 'bond'
    }

    return type_mapping.get(normalized, 'stock')  # Default to stock


async def parse_csv_file(file: UploadFile) -> List[AssetOnboardingRequest]:
    """Parse CSV file and return list of AssetOnboardingRequest objects."""
    contents = await file.read()
    decoded = contents.decode('utf-8-sig')  # Handle BOM
    csv_reader = csv.DictReader(io.StringIO(decoded))

    assets = []
    for row in csv_reader:
        # Map CSV headers (case-insensitive) to expected fields
        ticker = row.get('TICKER', row.get('ticker', '')).strip()
        quantity = float(row.get('Quantity', row.get('quantity', 0)))
        average_cost = float(row.get('Cost', row.get('cost', row.get('average_cost', 0))))
        asset_type_raw = row.get('ASSET_TYPE', row.get('asset_type', 'Stock')).strip()
        currency = row.get('CURRENCY', row.get('currency', 'USD')).strip()

        # Normalize asset_type to match FinanceService expectations
        asset_type = normalize_asset_type(asset_type_raw)

        if ticker and quantity > 0 and average_cost > 0:
            assets.append(AssetOnboardingRequest(
                ticker=ticker,
                quantity=quantity,
                average_cost=average_cost,
                asset_type=asset_type,
                currency=currency
            ))

    return assets


async def batch_fetch_asset_data(
    items: List[AssetOnboardingRequest],
    existing_assets: Dict[str, Asset]
) -> Dict[str, Optional[dict]]:
    """
    Fetch asset data for multiple tickers in parallel.

    Args:
        items: List of asset onboarding requests
        existing_assets: Dictionary of existing assets by ticker

    Returns:
        Dictionary mapping ticker to asset data (or None if fetch failed)
    """
    async def fetch_single_asset(item: AssetOnboardingRequest) -> Tuple[str, Optional[dict]]:
        ticker = item.ticker.upper().strip()

        # Skip if asset already exists
        if ticker in existing_assets:
            return (ticker, None)

        try:
            asset_data = await FinanceService.get_asset_info(ticker, item.asset_type)
            if asset_data and item.currency:
                asset_data['currency'] = item.currency
            return (ticker, asset_data)
        except Exception as e:
            logger.error(f"Error fetching data for {ticker}: {e}")
            return (ticker, None)

    # Fetch all asset data in parallel
    results = await asyncio.gather(*[fetch_single_asset(item) for item in items])

    # Convert to dictionary
    return dict(results)


@router.post("/onboard", status_code=201, response_model=dict)
async def onboard_asset(
    request: Request,
    affect_cash: bool = Query(False, description="When true, treat this as a real buy and debit portfolio cash."),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Onboard multiple assets with their holdings.
    Supports both JSON data and CSV file upload.
    Fetches asset data from Yahoo Finance and creates holdings.

    CSV Format: TICKER,CURRENCY,ASSET_TYPE,Quantity,Cost

    For JSON: Send array of objects with ticker, quantity, average_cost, asset_type, currency
    For CSV: Upload file via 'file' form field
    """
    created_assets = []
    errors = []
    data = None

    # Check content type to determine how to parse the request
    content_type = request.headers.get('content-type', '')

    if 'multipart/form-data' in content_type:
        # Handle file upload
        form = await request.form()
        file = form.get('file')
        if file and hasattr(file, 'filename') and file.filename:
            try:
                data = await parse_csv_file(file)
                if not data:
                    raise HTTPException(status_code=400, detail="No valid data found in CSV file")
            except Exception as e:
                logger.error(f"Error parsing CSV file: {str(e)}")
                raise HTTPException(status_code=400, detail=f"Error parsing CSV file: {str(e)}")
        else:
            raise HTTPException(status_code=400, detail="No file uploaded")
    elif 'application/json' in content_type:
        # Handle JSON body
        try:
            json_data = await request.json()
            if isinstance(json_data, list):
                data = [AssetOnboardingRequest(**item) for item in json_data]
            else:
                raise HTTPException(status_code=400, detail="JSON data must be an array")
        except Exception as e:
            logger.error(f"Error parsing JSON data: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Invalid JSON data: {str(e)}")
    else:
        raise HTTPException(status_code=400, detail="Unsupported content type. Use application/json or multipart/form-data")

    if not data:
        raise HTTPException(status_code=400, detail="No data provided. Send JSON data or upload CSV file.")

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

    # Pre-fetch existing assets from database
    tickers = [item.ticker.upper().strip() for item in data]
    stmt = select(Asset).where(Asset.ticker.in_(tickers))
    result = await db.execute(stmt)
    existing_assets_list = result.scalars().all()
    existing_assets = {asset.ticker: asset for asset in existing_assets_list}

    # Batch fetch asset data for new tickers in parallel
    logger.info(f"Batch fetching data for {len(data)} assets in parallel...")
    asset_data_map = await batch_fetch_asset_data(data, existing_assets)
    logger.info(f"Batch fetch complete. Processing assets...")

    for item in data:
        try:
            ticker = item.ticker.upper().strip()

            # Get asset from existing assets or create new one
            asset_obj = existing_assets.get(ticker)

            if not asset_obj:
                # Use pre-fetched asset data
                asset_data = asset_data_map.get(ticker)

                if not asset_data:
                    errors.append(f"Could not fetch data for ticker: {ticker}")
                    continue

                # Filter out fields that are not part of the Asset model
                # (e.g., change_percent, change, previous_close from mutual fund data)
                asset_model_fields = {
                    'ticker', 'name', 'asset_type', 'sector', 'industry', 'description',
                    'currency', 'exchange', 'current_price', 'market_cap', 'dividend_yield',
                    'pe_ratio', 'beta', 'last_price_update'
                }
                filtered_asset_data = {k: v for k, v in asset_data.items() if k in asset_model_fields}

                # Create Asset object with filtered data
                asset_obj = Asset(**filtered_asset_data)
                db.add(asset_obj)
                await db.flush()  # Get the ID
                logger.info(f"Created new asset: {ticker} with ID: {asset_obj.id}")
            else:
                # Update existing asset with fresh data if needed
                if not asset_obj.current_price:
                    current_price = await FinanceService.get_current_price(ticker, asset_obj.asset_type or item.asset_type)
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
                                 (item.quantity * item.average_cost)
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
                    average_cost=item.average_cost,
                    portfolio_id=portfolio_id,
                    cost_basis=item.quantity * item.average_cost,
                    market_value=item.quantity * (asset_obj.current_price or item.average_cost),
                    current_price=asset_obj.current_price,
                )
                db.add(holding)
                holding_to_use = holding
                logger.info(f"Created new holding for {ticker}.")

            await db.flush()  # Ensure holding_to_use has an ID if new, or is updated

            # Calculate purchase cost
            purchase_cost = item.quantity * item.average_cost

            # Create transaction (buy)
            transaction = Transaction(
                portfolio_id=holding_to_use.portfolio_id,
                asset_id=asset_obj.id,
                transaction_type=TransactionType.BUY,
                quantity=item.quantity,
                price=item.average_cost,
                transaction_date=datetime.utcnow(),
            )
            db.add(transaction)
            await db.flush()

            purchase_cost_portfolio_currency = purchase_cost
            exchange_rate = 1.0
            if affect_cash:
                purchase_cost_portfolio_currency, exchange_rate = await convert_amount_to_portfolio_currency(
                    purchase_cost,
                    item.currency,
                    portfolio.currency
                )
                portfolio.cash_balance -= purchase_cost_portfolio_currency
                portfolio.updated_at = datetime.utcnow()

            created_assets.append(
                {
                    "ticker": ticker,
                    "name": asset_obj.name or ticker,
                    "quantity": item.quantity, # This quantity is for the current transaction
                    "average_cost": item.average_cost,
                    "purchase_cost": purchase_cost,
                    "purchase_cost_portfolio_currency": purchase_cost_portfolio_currency,
                    "purchase_cost_currency": portfolio.currency,
                    "cash_affected": affect_cash,
                    "exchange_rate": exchange_rate,
                    "new_cash_balance": portfolio.cash_balance if affect_cash else None,
                    "current_price": asset_obj.current_price,
                    "market_value": holding_to_use.market_value,
                    "asset_id": asset_obj.id,
                    "holding_id": holding_to_use.id,
                    "transaction_id": transaction.id,
                }
            )
            logger.info(
                f"Successfully processed {ticker}: {item.quantity} shares at ${item.average_cost}"
            )
        except Exception as e:
            logger.error(f"Error processing {item.ticker}: {str(e)}")
            errors.append(f"Error processing {item.ticker}: {str(e)}")
    if created_assets:
        await db.commit()
        if affect_cash:
            await invalidate_portfolio_transaction_caches(portfolio_id)
    return {"assets": created_assets, "errors": errors}


@router.post("/sell", status_code=201, response_model=dict)
async def sell_asset(
    data: AssetSellRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Sell an asset from the authenticated user's portfolio and credit cash.
    """
    try:
        ticker = data.ticker.upper().strip()
        portfolio = await get_user_portfolio(db, current_user.id)
        if not portfolio:
            raise HTTPException(status_code=404, detail="Portfolio not found")

        # Find holding
        stmt = select(Holding).where(
            Holding.ticker == ticker,
            Holding.portfolio_id == portfolio.id
        )
        result = await db.execute(stmt)
        holding = result.scalar_one_or_none()
        if not holding or holding.quantity < data.quantity:
            raise HTTPException(status_code=400, detail="Not enough quantity to sell")

        asset_obj = await db.get(Asset, holding.asset_id)

        from app.crud.transaction import calculate_realized_gain_loss_fifo

        realized_gain_loss = await calculate_realized_gain_loss_fifo(
            db=db,
            portfolio_id=portfolio.id,
            asset_id=holding.asset_id,
            sell_quantity=data.quantity,
            sell_price=data.price
        )

        sale_proceeds_original = data.quantity * data.price
        asset_currency = asset_obj.currency if asset_obj and asset_obj.currency else "USD"
        sale_proceeds, exchange_rate = await convert_amount_to_portfolio_currency(
            sale_proceeds_original,
            asset_currency,
            portfolio.currency
        )

        # Update holding
        holding.quantity -= data.quantity
        holding.market_value = holding.quantity * (
            holding.current_price or data.price
        )
        holding.cost_basis = holding.quantity * holding.average_cost

        # Mark holding as inactive if quantity reaches zero
        if holding.quantity <= 0:
            holding.is_active = False

        # Create transaction (sell)
        transaction = Transaction(
            portfolio_id=holding.portfolio_id,
            asset_id=holding.asset_id, # Use asset_id instead of ticker
            transaction_type=TransactionType.SELL,
            quantity=data.quantity,
            price=data.price,
            transaction_date=datetime.utcnow(),
            realized_gain_loss=realized_gain_loss,
        )
        db.add(transaction)

        portfolio.cash_balance += sale_proceeds
        portfolio.updated_at = datetime.utcnow()

        await db.commit()
        await invalidate_portfolio_transaction_caches(portfolio.id)

        return {
            "success": True,
            "message": f"Sold {data.quantity} of {ticker}",
            "transaction_id": transaction.id,
            "quantity_sold": data.quantity,
            "sale_price": data.price,
            "sale_proceeds_original": sale_proceeds_original,
            "sale_proceeds_original_currency": asset_currency,
            "sale_proceeds": sale_proceeds,
            "sale_proceeds_currency": portfolio.currency,
            "exchange_rate": exchange_rate,
            "realized_gain_loss": realized_gain_loss,
            "new_cash_balance": portfolio.cash_balance,
        }
    except HTTPException:
        raise
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
