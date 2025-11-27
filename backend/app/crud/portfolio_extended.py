"""
Portfolio CRUD operations continued - Update, Delete, Analysis.
"""
from typing import Optional, List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from datetime import datetime

from app.models import Portfolio, Holding, Asset
from app.schemas import PortfolioUpdate
from app.services.exchange_rate_service import get_exchange_rate_service


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


async def calculate_portfolio_metrics(
    db: AsyncSession,
    portfolio_id: int,
    display_currency: Optional[str] = None
) -> Dict:
    """
    Calculate portfolio performance metrics.

    Args:
        db: Database session
        portfolio_id: Portfolio ID
        display_currency: Currency to display values in (USD or CAD).
                         If None, uses portfolio's base currency.

    Returns:
        Dictionary with portfolio metrics in the requested currency
    """
    portfolio = await get_portfolio(db, portfolio_id)
    if not portfolio or not portfolio.holdings:
        return {
            "total_invested": 0.0,
            "total_value": 0.0,
            "total_return": 0.0,
            "total_return_percentage": 0.0,
            "asset_allocation": {},
            "holdings_count": 0,
            "display_currency": display_currency or "USD",
        }

    # Use portfolio currency if not specified
    if not display_currency:
        display_currency = portfolio.currency

    display_currency = display_currency.upper()
    exchange_service = get_exchange_rate_service()

    print(f"[CURRENCY] Calculating portfolio metrics in {display_currency}")

    # Pre-fetch exchange rates for all currencies to avoid repeated API calls
    # We only need USD<->CAD conversions
    exchange_rates = {}
    currencies_needed = set()
    for holding in portfolio.holdings:
        if holding.is_active and holding.asset:
            currencies_needed.add(holding.asset.currency)

    print(f"[CURRENCY] Currencies in portfolio: {currencies_needed}")

    # Fetch all needed exchange rates upfront
    for currency in currencies_needed:
        if currency != display_currency:
            rate = await exchange_service.get_exchange_rate(currency, display_currency)
            exchange_rates[currency] = rate
            print(f"[CURRENCY] Exchange rate {currency} -> {display_currency}: {rate}")

    total_cost = 0.0
    total_value = 0.0
    asset_allocation = {}

    for holding in portfolio.holdings:
        if not holding.is_active:
            continue

        # Get asset currency
        asset_currency = holding.asset.currency if holding.asset else "USD"

        # Calculate cost and value in original currency
        cost = holding.quantity * holding.average_cost
        current_value = holding.quantity * (holding.current_price or holding.average_cost)

        # Convert to display currency if different using pre-fetched rate
        if asset_currency != display_currency and asset_currency in exchange_rates:
            rate = exchange_rates[asset_currency]
            original_cost = cost
            original_value = current_value
            cost = cost * rate
            current_value = current_value * rate
            print(f"[CURRENCY] {holding.asset.ticker}: {original_value:.2f} {asset_currency} -> {current_value:.2f} {display_currency} (rate: {rate})")

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

    print(f"[CURRENCY] Final totals in {display_currency}: Value={total_value:.2f}, Cost={total_cost:.2f}, Return={total_return:.2f}")

    return {
        "total_invested": total_cost,
        "total_value": total_value,
        "total_return": total_return,
        "total_return_percentage": total_return_percentage,
        "asset_allocation": asset_allocation,
        "holdings_count": len([h for h in portfolio.holdings if h.is_active]),
        "display_currency": display_currency,
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


async def update_portfolio_cash_balance(
    db: AsyncSession,
    portfolio_id: int,
    amount: float,
    operation: str = "add"
) -> Optional[Portfolio]:
    """
    Update portfolio cash balance.

    Args:
        db: Database session
        portfolio_id: Portfolio ID
        amount: Amount to add or subtract (positive value)
        operation: "add" or "subtract"

    Returns:
        Updated portfolio or None if not found
    """
    portfolio = await get_portfolio(db, portfolio_id)
    if not portfolio:
        return None

    if operation == "add":
        portfolio.cash_balance += amount
    elif operation == "subtract":
        portfolio.cash_balance -= amount
    else:
        raise ValueError("Operation must be 'add' or 'subtract'")

    portfolio.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(portfolio)

    return portfolio


async def get_portfolio_cash_balance(
    db: AsyncSession,
    portfolio_id: int,
    display_currency: Optional[str] = None
) -> Dict:
    """
    Get portfolio cash balance with optional currency conversion.

    Args:
        db: Database session
        portfolio_id: Portfolio ID
        display_currency: Currency to convert to (optional)

    Returns:
        Dictionary with cash balance info
    """
    portfolio = await get_portfolio(db, portfolio_id)
    if not portfolio:
        return {
            "cash_balance": 0.0,
            "portfolio_currency": "USD",
            "display_currency": display_currency or "USD",
            "exchange_rate": 1.0
        }

    cash_balance = portfolio.cash_balance
    portfolio_currency = portfolio.currency

    # If no display currency specified, use portfolio currency
    if not display_currency:
        return {
            "cash_balance": cash_balance,
            "portfolio_currency": portfolio_currency,
            "display_currency": portfolio_currency,
            "exchange_rate": 1.0
        }

    display_currency = display_currency.upper()

    # Convert if needed
    if portfolio_currency != display_currency:
        exchange_service = get_exchange_rate_service()
        rate = await exchange_service.get_exchange_rate(portfolio_currency, display_currency)
        cash_balance = cash_balance * rate
    else:
        rate = 1.0

    return {
        "cash_balance": cash_balance,
        "portfolio_currency": portfolio_currency,
        "display_currency": display_currency,
        "exchange_rate": rate
    }


# Import to avoid circular imports
from app.crud.portfolio import get_portfolio
