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
from app.services.finance_service import FinanceService
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

    # Separate holdings by asset type
    stock_symbols = []
    mutual_fund_holdings = []
    crypto_holdings = []
    unsupported_stock_holdings = []

    for holding in holdings:
        if not holding.ticker:
            continue

        asset_type = holding.asset.asset_type if holding.asset else 'stock'

        if asset_type == 'mutual_fund':
            mutual_fund_holdings.append(holding)
        elif asset_type == 'crypto':
            crypto_holdings.append(holding)
        elif holding.ticker in UNSUPPORTED_TICKERS:
            # Unsupported by Finnhub, will use Yahoo Finance OHLC
            unsupported_stock_holdings.append(holding)
        else:
            stock_symbols.append(holding.ticker)

    # Remove duplicates
    stock_symbols = list(set(stock_symbols))

    # Fetch mutual fund data
    for holding in mutual_fund_holdings:
        try:
            mf_data = await FinanceService.get_asset_info(holding.ticker, 'mutual_fund')
            if mf_data and 'current_price' in mf_data:
                # Update holding's current price
                holding.current_price = mf_data['current_price']
                # Store change_percent temporarily (we'll use it below)
                holding._temp_change_percent = mf_data.get('change_percent', 0)

                # Update asset's current price in database
                if holding.asset:
                    holding.asset.current_price = mf_data['current_price']
                    holding.asset.last_price_update = datetime.utcnow()
            else:
                holding._temp_change_percent = 0
        except Exception as e:
            logger.error(f"Error fetching mutual fund data for {holding.ticker}: {e}")
            holding._temp_change_percent = 0

    # Fetch crypto data
    for holding in crypto_holdings:
        try:
            crypto_data = await FinanceService.get_asset_info(holding.ticker, 'crypto')
            if crypto_data and 'current_price' in crypto_data:
                holding.current_price = crypto_data['current_price']
                # Calculate change percent if available
                if holding.asset and holding.asset.current_price:
                    old_price = holding.asset.current_price
                    new_price = crypto_data['current_price']
                    holding._temp_change_percent = ((new_price - old_price) / old_price) * 100
                else:
                    holding._temp_change_percent = 0

                # Update asset's current price in database
                if holding.asset:
                    holding.asset.current_price = crypto_data['current_price']
                    holding.asset.last_price_update = datetime.utcnow()
            else:
                holding._temp_change_percent = 0
        except Exception as e:
            logger.error(f"Error fetching crypto data for {holding.ticker}: {e}")
            holding._temp_change_percent = 0

    # Fetch data for unsupported stocks using Yahoo Finance OHLC
    for holding in unsupported_stock_holdings:
        try:
            ohlc_data = await FinanceService.get_ohlc_data(holding.ticker)
            if ohlc_data and 'current_price' in ohlc_data:
                holding.current_price = ohlc_data['current_price']
                holding._temp_change_percent = ohlc_data.get('change_percent', 0)
                holding._temp_change = ohlc_data.get('change', 0)

                # Update asset's current price in database
                if holding.asset:
                    holding.asset.current_price = ohlc_data['current_price']
                    holding.asset.last_price_update = datetime.utcnow()
            else:
                holding._temp_change_percent = 0
                holding._temp_change = 0
        except Exception as e:
            logger.error(f"Error fetching OHLC data for {holding.ticker}: {e}")
            holding._temp_change_percent = 0
            holding._temp_change = 0

    # Commit database updates for prices
    await db.commit()

    if not stock_symbols:
        # Still return holdings even if no Finnhub-supported tickers
        enriched_holdings = []
        for holding in holdings:
            # CRITICAL FIX: Always calculate cost_basis and market_value from database fields
            calculated_cost_basis = holding.quantity * holding.average_cost
            current_price_fallback = holding.current_price or holding.average_cost
            calculated_market_value = holding.quantity * current_price_fallback

            holding_dict = {
                "id": holding.id,
                "ticker": holding.ticker,
                "quantity": holding.quantity,
                "average_cost": holding.average_cost,
                "cost_basis": calculated_cost_basis,  # Always calculate fresh
                "asset": {
                    "name": holding.asset.name if holding.asset else holding.ticker,
                    "ticker": holding.ticker
                },
                "current_price": current_price_fallback,
                "market_value": calculated_market_value,  # Always calculate fresh
            }

            # Check if we have temp change_percent (for mutual funds, crypto, and unsupported stocks)
            if hasattr(holding, '_temp_change_percent'):
                holding_dict["change_percent"] = holding._temp_change_percent
                # Use temp_change if available (from OHLC), otherwise calculate
                if hasattr(holding, '_temp_change'):
                    holding_dict["change"] = holding._temp_change
                elif holding._temp_change_percent and current_price_fallback:
                    holding_dict["change"] = (current_price_fallback * holding._temp_change_percent) / 100
                else:
                    holding_dict["change"] = 0
            else:
                holding_dict["change_percent"] = 0
                holding_dict["change"] = 0

            enriched_holdings.append(holding_dict)

        return {
            "holdings": enriched_holdings,
            "market_data": {},
            "updated_at": datetime.utcnow().isoformat()
        }

    # Update active symbols for WebSocket background task (only for stocks)
    if stock_symbols:
        ws_manager = get_ws_manager()
        await ws_manager.update_active_symbols(stock_symbols)

    # Try to get cached data first for faster response
    redis_client = await get_redis_client()
    market_data = {}
    uncached_symbols = []

    # Check cache for each symbol
    for symbol in stock_symbols:
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
        # CRITICAL FIX: Always calculate cost_basis from database fields, never use cached value
        calculated_cost_basis = holding.quantity * holding.average_cost

        holding_dict = {
            "id": holding.id,
            "ticker": holding.ticker,
            "quantity": holding.quantity,
            "average_cost": holding.average_cost,
            "cost_basis": calculated_cost_basis,  # Always calculate fresh
            "asset": {
                "name": holding.asset.name if holding.asset else holding.ticker,
                "ticker": holding.ticker
            }
        }

        # Add live market data if available
        if holding.ticker in market_data:
            # Stock data from Finnhub
            quote = market_data[holding.ticker]
            holding_dict["current_price"] = quote["current_price"]
            holding_dict["market_value"] = quote["current_price"] * holding.quantity
            holding_dict["change_percent"] = quote["change_percent"]
            holding_dict["change"] = quote["change"]
        else:
            # Use stored price if live data not available (e.g., MAU.TO, mutual funds, crypto)
            # CRITICAL FIX: Always calculate market_value from quantity and price
            current_price_fallback = holding.current_price or holding.average_cost
            holding_dict["current_price"] = current_price_fallback
            holding_dict["market_value"] = holding.quantity * current_price_fallback

            # Check if we have temp change_percent (for mutual funds, crypto, and unsupported stocks)
            if hasattr(holding, '_temp_change_percent'):
                holding_dict["change_percent"] = holding._temp_change_percent
                # Use temp_change if available (from OHLC), otherwise calculate
                if hasattr(holding, '_temp_change'):
                    holding_dict["change"] = holding._temp_change
                elif holding._temp_change_percent and current_price_fallback:
                    holding_dict["change"] = (current_price_fallback * holding._temp_change_percent) / 100
                else:
                    holding_dict["change"] = 0
            else:
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
