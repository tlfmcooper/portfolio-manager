"""
Market data API routes for live stock prices.
"""
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.core.database import get_db
from app.crud import get_user_portfolio, get_portfolio_holdings
from app.utils.dependencies import get_current_active_user
from app.models import User
from app.services.finnhub_service import get_finnhub_service

router = APIRouter()

# Tickers not supported by Finnhub free tier
UNSUPPORTED_TICKERS = ["MAU.TO"]


@router.get("/live")
async def get_live_market_data(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get live market data for all holdings in current user's portfolio.
    Fetches real-time quotes from Finnhub API.
    """
    portfolio = await get_user_portfolio(db, current_user.id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )
    
    # Get all holdings
    holdings = await get_portfolio_holdings(db, portfolio.id)
    
    if not holdings:
        return {
            "holdings": [],
            "market_data": {},
            "updated_at": datetime.utcnow().isoformat(),
            "message": "No holdings found in portfolio"
        }
    
    # Extract unique ticker symbols, excluding unsupported ones
    symbols = list(set([
        holding.ticker for holding in holdings 
        if holding.ticker and holding.ticker not in UNSUPPORTED_TICKERS
    ]))
    
    if not symbols:
        # Still return holdings even if no Finnhub-supported tickers
        enriched_holdings = []
        for holding in holdings:
            holding_dict = {
                "id": holding.id,
                "ticker": holding.ticker,
                "quantity": holding.quantity,
                "average_cost": holding.average_cost,
                "cost_basis": holding.cost_basis,
                "asset": {
                    "name": holding.asset.name if holding.asset else holding.ticker,
                    "ticker": holding.ticker
                },
                "current_price": holding.average_cost,
                "market_value": holding.market_value,
                "change_percent": 0,
                "change": 0
            }
            enriched_holdings.append(holding_dict)
        
        return {
            "holdings": enriched_holdings,
            "market_data": {},
            "updated_at": datetime.utcnow().isoformat()
        }
    
    # Fetch live quotes from Finnhub
    finnhub_service = get_finnhub_service()
    market_data = await finnhub_service.get_multiple_quotes_async(symbols)
    
    # Enrich holdings with live market data
    enriched_holdings = []
    for holding in holdings:
        holding_dict = {
            "id": holding.id,
            "ticker": holding.ticker,
            "quantity": holding.quantity,
            "average_cost": holding.average_cost,
            "cost_basis": holding.cost_basis,
            "asset": {
                "name": holding.asset.name if holding.asset else holding.ticker,
                "ticker": holding.ticker
            }
        }
        
        # Add live market data if available
        if holding.ticker in market_data:
            quote = market_data[holding.ticker]
            holding_dict["current_price"] = quote["current_price"]
            holding_dict["market_value"] = quote["current_price"] * holding.quantity
            holding_dict["change_percent"] = quote["change_percent"]
            holding_dict["change"] = quote["change"]
        else:
            # Use stored price if live data not available (e.g., MAU.TO)
            holding_dict["current_price"] = holding.current_price or holding.average_cost
            holding_dict["market_value"] = holding.market_value
            holding_dict["change_percent"] = 0
            holding_dict["change"] = 0
        
        enriched_holdings.append(holding_dict)
    
    return {
        "holdings": enriched_holdings,
        "market_data": market_data,
        "updated_at": datetime.utcnow().isoformat()
    }
