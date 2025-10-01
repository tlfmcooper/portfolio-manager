"""
Market data API routes for live stock prices.
"""
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import logging

from app.core.database import get_db
from app.crud import get_user_portfolio, get_portfolio_holdings
from app.utils.dependencies import get_current_active_user
from app.models import User
from app.services.finnhub_service import get_finnhub_service
from app.services.market_websocket import get_ws_manager
from app.core.redis_client import get_redis_client

logger = logging.getLogger(__name__)

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
    Uses Redis cache when available for faster response times.
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

    # Update active symbols for WebSocket background task
    ws_manager = get_ws_manager()
    await ws_manager.update_active_symbols(symbols)

    # Try to get cached data first for faster response
    redis_client = await get_redis_client()
    market_data = {}
    uncached_symbols = []

    # Check cache for each symbol
    for symbol in symbols:
        cache_key = f"stock:quote:{symbol}"
        cached_quote = await redis_client.get(cache_key)
        if cached_quote:
            market_data[symbol] = cached_quote
        else:
            uncached_symbols.append(symbol)

    # If some symbols not cached, fetch only those from Finnhub
    if uncached_symbols:
        logger.info(f"Fetching {len(uncached_symbols)} uncached symbols from Finnhub")
        finnhub_service = get_finnhub_service()
        fresh_data = await finnhub_service.get_multiple_quotes_async(uncached_symbols)

        # Cache the new results and add to market_data
        for symbol, quote in fresh_data.items():
            market_data[symbol] = quote
            cache_key = f"stock:quote:{symbol}"
            await redis_client.set(cache_key, quote, ttl=300)  # 5 minute cache

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


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for streaming live market data.
    Sends historical cached data on connect, then streams updates.
    """
    ws_manager = get_ws_manager()
    await ws_manager.connect(websocket)

    try:
        # Wait for initial message with symbols to track
        data = await websocket.receive_json()

        if data.get("type") == "subscribe":
            symbols = data.get("symbols", [])

            # Send historical cached data first
            await ws_manager.send_historical_data(websocket, symbols)

            # Update active symbols
            await ws_manager.update_active_symbols(symbols)

            # Keep connection alive and handle messages
            while True:
                data = await websocket.receive_json()

                if data.get("type") == "ping":
                    await ws_manager.send_personal_message(
                        {"type": "pong", "timestamp": datetime.utcnow().isoformat()},
                        websocket
                    )
                elif data.get("type") == "subscribe":
                    # Update symbols to track
                    symbols = data.get("symbols", [])
                    await ws_manager.update_active_symbols(symbols)
                    await ws_manager.send_historical_data(websocket, symbols)

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket)
