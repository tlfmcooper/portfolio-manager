"""
Portfolio management API routes.
"""
from datetime import datetime, timezone
from typing import Any, Dict, Optional, List, Literal
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.schemas import PortfolioInDB, PortfolioUpdate, PortfolioSummary, PortfolioAnalysisResponse, HoldingSummary
from app.crud import (
    get_user_portfolio,
    update_portfolio,
    calculate_portfolio_metrics,
    update_portfolio_metrics,
    get_portfolio_holdings
)
from app.utils.dependencies import get_current_active_user
from app.models import User
from app.models.transaction import Transaction
from app.services.portfolio_analysis import AdvancedPortfolioAnalytics
from app.services.exchange_rate_service import get_exchange_rate_service
from app.services.finance_service import FinanceService
from app.services.portfolio_ytd import calculate_portfolio_ytd_metrics

router = APIRouter()
logger = logging.getLogger(__name__)


def _build_summary_from_live_market(portfolio, live_payload: Dict[str, Any]) -> Dict[str, Any]:
    holdings = live_payload.get("holdings", [])
    holdings_value = sum(float(holding.get("market_value") or 0.0) for holding in holdings)
    total_cost = sum(float(holding.get("cost_basis") or 0.0) for holding in holdings)
    cash_balance = float(live_payload.get("cash_balance") or 0.0)
    total_return = holdings_value - total_cost
    total_return_percentage = (total_return / total_cost * 100) if total_cost > 0 else 0.0

    return {
        "id": portfolio.id,
        "name": portfolio.name,
        "total_value": holdings_value + cash_balance,
        "total_return": total_return,
        "total_return_percentage": total_return_percentage,
        "cash_balance": cash_balance,
        "total_holdings_count": len(holdings),
        "diversification_score": portfolio.diversification_score,
        "currency": live_payload.get("display_currency") or portfolio.currency,
        "last_updated": live_payload.get("updated_at") or portfolio.updated_at,
    }


async def _build_ytd_fields(
    *,
    db: AsyncSession,
    portfolio,
    live_payload: Dict[str, Any] | None,
    currency: str,
) -> Dict[str, Any]:
    holdings = await get_portfolio_holdings(db, portfolio.id, skip=0, limit=None)
    current_holdings: list[Dict[str, Any]] = []

    live_holdings_by_ticker = {
        str(item.get("ticker") or "").upper(): item
        for item in (live_payload or {}).get("holdings", [])
        if item.get("ticker")
    }

    exchange_service = get_exchange_rate_service()
    exchange_rates: Dict[str, float] = {}
    for holding in holdings:
        asset_currency = (holding.asset.currency if holding.asset and holding.asset.currency else portfolio.currency).upper()
        if asset_currency != currency and asset_currency not in exchange_rates:
            exchange_rates[asset_currency] = await exchange_service.get_exchange_rate(asset_currency, currency)

    for holding in holdings:
        if not holding.is_active:
            continue

        asset_currency = (holding.asset.currency if holding.asset and holding.asset.currency else portfolio.currency).upper()
        live_entry = live_holdings_by_ticker.get(holding.ticker.upper())
        if live_entry:
            current_price = live_entry.get("current_price")
            market_value = live_entry.get("market_value")
        else:
            rate = exchange_rates.get(asset_currency, 1.0)
            current_price = (holding.current_price or holding.average_cost) * rate if asset_currency != currency else (holding.current_price or holding.average_cost)
            market_value = holding.quantity * current_price

        current_holdings.append(
            {
                "ticker": holding.ticker,
                "quantity": holding.quantity,
                "current_price": current_price,
                "market_value": market_value,
                "asset_type": holding.asset.asset_type if holding.asset else None,
                "currency": currency,
            }
        )

    transactions_result = await db.execute(
        select(Transaction)
        .options(selectinload(Transaction.asset))
        .where(Transaction.portfolio_id == portfolio.id)
    )
    transactions = transactions_result.scalars().all()

    transaction_items = []
    for transaction in transactions:
        asset_currency = None
        asset_type = None
        if transaction.asset is not None:
            asset_currency = transaction.asset.currency
            asset_type = transaction.asset.asset_type
            if asset_currency and asset_currency.upper() != currency and asset_currency.upper() not in exchange_rates:
                exchange_rates[asset_currency.upper()] = await exchange_service.get_exchange_rate(asset_currency.upper(), currency)

        transaction_items.append(
            {
                "transaction_type": getattr(transaction.transaction_type, "value", transaction.transaction_type),
                "asset_ticker": transaction.asset.ticker if transaction.asset else None,
                "quantity": transaction.quantity,
                "price": transaction.price,
                "transaction_date": transaction.transaction_date,
                "notes": transaction.notes,
                "asset_currency": asset_currency,
                "asset_type": asset_type,
            }
        )

    cash_balance = float((live_payload or {}).get("cash_balance", portfolio.cash_balance or 0.0))

    return await calculate_portfolio_ytd_metrics(
        current_holdings=current_holdings,
        transactions=transaction_items,
        current_cash_balance=cash_balance,
        portfolio_currency=portfolio.currency.upper(),
        display_currency=currency,
        exchange_rates=exchange_rates,
        performance_fetcher=FinanceService.calculate_ticker_performance,
        as_of=datetime.now(timezone.utc),
    )


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
    db: AsyncSession = Depends(get_db),
    currency: Optional[str] = Query(None, description="Display currency (USD or CAD)")
) -> Any:
    """
    Get portfolio summary with key metrics.

    Args:
        currency: Optional currency to display values in (USD or CAD)
    """
    portfolio = await get_user_portfolio(db, current_user.id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )

    try:
        from app.api.v1.market import get_live_market_data

        live_payload = await get_live_market_data(currency=currency, current_user=current_user, db=db)
        summary = _build_summary_from_live_market(portfolio, live_payload)
        summary.update(
            await _build_ytd_fields(
                db=db,
                portfolio=portfolio,
                live_payload=live_payload,
                currency=summary["currency"],
            )
        )
        return summary
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Falling back to cached portfolio summary metrics", exc_info=exc)

    # Calculate metrics with currency conversion
    metrics = await calculate_portfolio_metrics(db, portfolio.id, currency)

    summary = {
        "id": portfolio.id,
        "name": portfolio.name,
        "total_value": metrics["total_value"],
        "total_return": metrics["total_return"],
        "total_return_percentage": metrics["total_return_percentage"],
        "cash_balance": metrics.get("cash_balance", portfolio.cash_balance or 0.0),
        "total_holdings_count": metrics["holdings_count"],
        "diversification_score": portfolio.diversification_score,
        "currency": metrics["display_currency"],
        "last_updated": portfolio.updated_at,
    }
    summary.update(
        await _build_ytd_fields(
            db=db,
            portfolio=portfolio,
            live_payload=None,
            currency=metrics["display_currency"],
        )
    )
    return summary


@router.get("/metrics", response_model=Dict)
async def get_portfolio_metrics(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    currency: Optional[str] = Query(None, description="Display currency (USD or CAD)")
) -> Any:
    """
    Get detailed portfolio metrics and analysis.

    Args:
        currency: Optional currency to display values in (USD or CAD)
    """
    portfolio = await get_user_portfolio(db, current_user.id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )

    metrics = await calculate_portfolio_metrics(db, portfolio.id, currency)
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
    db: AsyncSession = Depends(get_db),
    currency: Optional[str] = Query(None, description="Display currency (USD or CAD)")
) -> Any:
    """
    Get comprehensive portfolio analysis with advanced metrics.

    Args:
        currency: Optional currency to display values in (USD or CAD)
    """
    portfolio = await get_user_portfolio(db, current_user.id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )

    analysis = AdvancedPortfolioAnalytics(portfolio.id, db, display_currency=currency)
    metrics = await analysis.calculate_portfolio_metrics()
    return metrics


@router.get("/analyze", response_model=PortfolioAnalysisResponse)
async def analyze_portfolio(
    query_type: Literal[
        "largest_holding",
        "smallest_holding",
        "top_performers",
        "worst_performers",
        "holdings_summary",
        "sector_breakdown"
    ] = Query(..., description="Type of analysis to perform"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    currency: Optional[str] = Query(None, description="Display currency (USD or CAD)"),
    period: Optional[str] = Query("ytd", description="Time period for performance: ytd, 1m, 3m, 1y"),
    limit: int = Query(5, ge=1, le=50, description="Number of results for list queries")
) -> Any:
    """
    Perform portfolio analysis based on query type.
    
    This endpoint provides various analyses for the agent to answer portfolio questions:
    - largest_holding: Returns the holding with the highest market value
    - smallest_holding: Returns the holding with the lowest market value
    - top_performers: Returns top N performers by YTD return (or specified period)
    - worst_performers: Returns worst N performers by YTD return (or specified period)
    - holdings_summary: Returns summary of all holdings with key metrics
    - sector_breakdown: Returns sector allocation breakdown
    
    For mutual funds, historical period returns are not available - only cost-basis returns.
    """
    portfolio = await get_user_portfolio(db, current_user.id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )
    
    display_currency = currency.upper() if currency else portfolio.currency
    
    # Get all holdings
    holdings = await get_portfolio_holdings(db, portfolio.id, skip=0, limit=None)
    active_holdings = [h for h in holdings if h.is_active]
    
    if not active_holdings:
        return PortfolioAnalysisResponse(
            query_type=query_type,
            result=[],
            currency=display_currency,
            period=period,
            total_portfolio_value=0,
            holdings_count=0,
            message="No active holdings in portfolio"
        )
    
    # Get exchange rates
    exchange_service = get_exchange_rate_service()
    exchange_rates = {}
    for holding in active_holdings:
        if holding.asset:
            asset_curr = holding.asset.currency
            if asset_curr != display_currency and asset_curr not in exchange_rates:
                rate = await exchange_service.get_exchange_rate(asset_curr, display_currency)
                exchange_rates[asset_curr] = rate
    
    # Calculate metrics for each holding
    holdings_data = []
    total_portfolio_value = 0
    
    for holding in active_holdings:
        asset = holding.asset
        asset_currency = asset.currency if asset else "USD"
        asset_type = asset.asset_type if asset else None
        
        # Calculate values with currency conversion
        rate = exchange_rates.get(asset_currency, 1.0)
        cost_basis = holding.quantity * holding.average_cost * rate
        market_value = holding.quantity * (holding.current_price or holding.average_cost) * rate
        gain_loss_percent = ((market_value - cost_basis) / cost_basis * 100) if cost_basis > 0 else 0
        
        total_portfolio_value += market_value
        
        # Get performance data for period returns (only for stocks/ETFs/crypto)
        perf_data = await FinanceService.calculate_ticker_performance(
            ticker=holding.ticker,
            asset_type=asset_type,
            periods=["ytd", "1m", "3m", "1y"]
        )
        
        # Map period to field
        period_map = {
            "ytd": "ytd_return",
            "1m": "one_month_return",
            "3m": "three_month_return",
            "1y": "one_year_return"
        }
        period_return = perf_data.get(period_map.get(period, "ytd_return"))
        
        holdings_data.append({
            "ticker": holding.ticker,
            "name": asset.name if asset else holding.ticker,
            "asset_type": asset_type,
            "quantity": holding.quantity,
            "market_value": round(market_value, 2),
            "cost_basis": round(cost_basis, 2),
            "gain_loss_percent": round(gain_loss_percent, 2),
            "period_return": period_return,
            "historical_data_available": perf_data.get("historical_data_available", True)
        })
    
    # Calculate weight percentages
    for h in holdings_data:
        h["weight_percent"] = round((h["market_value"] / total_portfolio_value * 100), 2) if total_portfolio_value > 0 else 0
    
    # Perform the requested analysis
    result = None
    message = None
    
    if query_type == "largest_holding":
        sorted_holdings = sorted(holdings_data, key=lambda x: x["market_value"], reverse=True)
        result = sorted_holdings[0] if sorted_holdings else None
        message = f"Largest holding by market value in {display_currency}"
        
    elif query_type == "smallest_holding":
        sorted_holdings = sorted(holdings_data, key=lambda x: x["market_value"])
        result = sorted_holdings[0] if sorted_holdings else None
        message = f"Smallest holding by market value in {display_currency}"
        
    elif query_type == "top_performers":
        # Filter out holdings without period return data, then sort
        with_returns = [h for h in holdings_data if h["period_return"] is not None]
        without_returns = [h for h in holdings_data if h["period_return"] is None]
        
        sorted_holdings = sorted(with_returns, key=lambda x: x["period_return"], reverse=True)[:limit]
        result = sorted_holdings
        
        if without_returns:
            mf_tickers = [h["ticker"] for h in without_returns if h["asset_type"] == "mutual_fund"]
            if mf_tickers:
                message = f"Top {limit} performers by {period.upper()} return. Note: Mutual funds ({', '.join(mf_tickers)}) excluded - historical data not available."
            else:
                message = f"Top {limit} performers by {period.upper()} return"
        else:
            message = f"Top {limit} performers by {period.upper()} return"
            
    elif query_type == "worst_performers":
        # Filter out holdings without period return data, then sort
        with_returns = [h for h in holdings_data if h["period_return"] is not None]
        without_returns = [h for h in holdings_data if h["period_return"] is None]
        
        sorted_holdings = sorted(with_returns, key=lambda x: x["period_return"])[:limit]
        result = sorted_holdings
        
        if without_returns:
            mf_tickers = [h["ticker"] for h in without_returns if h["asset_type"] == "mutual_fund"]
            if mf_tickers:
                message = f"Worst {limit} performers by {period.upper()} return. Note: Mutual funds ({', '.join(mf_tickers)}) excluded - historical data not available."
            else:
                message = f"Worst {limit} performers by {period.upper()} return"
        else:
            message = f"Worst {limit} performers by {period.upper()} return"
            
    elif query_type == "holdings_summary":
        # Return all holdings with key metrics, sorted by market value
        result = sorted(holdings_data, key=lambda x: x["market_value"], reverse=True)
        message = f"Summary of all {len(holdings_data)} holdings"
        
    elif query_type == "sector_breakdown":
        # Group by sector
        sector_breakdown = {}
        for h in holdings_data:
            asset = next((holding.asset for holding in active_holdings if holding.ticker == h["ticker"]), None)
            sector = asset.sector if asset and asset.sector else "Unknown"
            
            if sector not in sector_breakdown:
                sector_breakdown[sector] = {
                    "sector": sector,
                    "market_value": 0,
                    "holdings_count": 0,
                    "tickers": []
                }
            
            sector_breakdown[sector]["market_value"] += h["market_value"]
            sector_breakdown[sector]["holdings_count"] += 1
            sector_breakdown[sector]["tickers"].append(h["ticker"])
        
        # Calculate percentages and sort by value
        for sector_data in sector_breakdown.values():
            sector_data["weight_percent"] = round((sector_data["market_value"] / total_portfolio_value * 100), 2) if total_portfolio_value > 0 else 0
            sector_data["market_value"] = round(sector_data["market_value"], 2)
        
        result = sorted(sector_breakdown.values(), key=lambda x: x["market_value"], reverse=True)
        message = f"Sector breakdown across {len(sector_breakdown)} sectors"
    
    return PortfolioAnalysisResponse(
        query_type=query_type,
        result=result,
        currency=display_currency,
        period=period,
        total_portfolio_value=round(total_portfolio_value, 2),
        holdings_count=len(active_holdings),
        message=message
    )


@router.post("/recalculate-cash-from-buys")
async def recalculate_cash_from_buys(
    since: Optional[str] = Query(None, description="ISO date YYYY-MM-DD. Defaults to today UTC."),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Retroactively debit cash for BUY transactions that were recorded without
    affecting cash (before affect_cash was deployed). Call once per date range.
    """
    from app.models.transaction import TransactionType
    from app.models.asset import Asset

    portfolio = await get_user_portfolio(db, current_user.id)
    if not portfolio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")

    if since:
        since_dt = datetime.fromisoformat(since).replace(tzinfo=timezone.utc)
    else:
        today = datetime.now(timezone.utc)
        since_dt = today.replace(hour=0, minute=0, second=0, microsecond=0)

    stmt = (
        select(Transaction)
        .where(
            and_(
                Transaction.portfolio_id == portfolio.id,
                Transaction.transaction_type == TransactionType.BUY,
                Transaction.transaction_date >= since_dt,
            )
        )
        .options(selectinload(Transaction.asset))
    )
    result = await db.execute(stmt)
    buy_transactions = result.scalars().all()

    cash_before = portfolio.cash_balance or 0.0

    if not buy_transactions:
        return {
            "adjusted": False,
            "message": f"No BUY transactions found since {since_dt.date().isoformat()}",
            "transactions_found": 0,
            "total_deducted": 0.0,
            "currency": portfolio.currency,
            "cash_balance_before": cash_before,
            "cash_balance_after": cash_before,
        }

    exchange_service = get_exchange_rate_service()
    portfolio_currency = portfolio.currency or "USD"
    total_cost = 0.0
    breakdown = []

    for txn in buy_transactions:
        asset_currency = (txn.asset.currency if txn.asset and txn.asset.currency else "USD")
        cost_original = (txn.quantity or 0.0) * txn.price

        if asset_currency != portfolio_currency:
            rate = await exchange_service.get_exchange_rate(asset_currency, portfolio_currency)
            cost_converted = cost_original * rate
        else:
            rate = 1.0
            cost_converted = cost_original

        total_cost += cost_converted
        breakdown.append({
            "transaction_id": txn.id,
            "asset_currency": asset_currency,
            "cost_original": round(cost_original, 4),
            "exchange_rate": rate,
            "cost_portfolio_currency": round(cost_converted, 4),
        })

    portfolio.cash_balance = cash_before - total_cost
    portfolio.updated_at = datetime.utcnow()
    await db.commit()

    try:
        from app.core.redis_client import get_redis_client
        redis_client = await get_redis_client()
        for currency in ["USD", "CAD"]:
            await redis_client.delete(f"dashboard:overview:{portfolio.id}:{currency}")
            await redis_client.delete(f"portfolio:{portfolio.id}:holdings:{currency}")
        await redis_client.delete(f"portfolio:{portfolio.id}:returns_cache")
        await redis_client.delete(f"portfolio:{portfolio.id}:analytics_cache")
    except Exception as e:
        logger.warning(f"Cache invalidation failed: {e}")

    return {
        "adjusted": True,
        "since": since_dt.date().isoformat(),
        "transactions_found": len(buy_transactions),
        "total_deducted": round(total_cost, 2),
        "currency": portfolio_currency,
        "cash_balance_before": round(cash_before, 2),
        "cash_balance_after": round(portfolio.cash_balance, 2),
        "breakdown": breakdown,
    }
