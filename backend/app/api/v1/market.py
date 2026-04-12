"""
Market data API routes for live stock prices.
"""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import asyncio
import logging

from app.core.database import get_db
from app.crud import get_user_portfolio, get_portfolio_holdings
from app.utils.dependencies import get_current_active_user
from app.models import User
from app.services.finnhub_service import get_finnhub_service
from app.services.market_websocket import get_ws_manager
from app.services.finance_service import FinanceService
from app.core.redis_client import get_redis_client
from app.services.exchange_rate_service import get_exchange_rate_service

logger = logging.getLogger(__name__)

router = APIRouter()

# Tickers not supported by Finnhub free tier
UNSUPPORTED_TICKERS = ["MAU.TO"]


def convert_price(price: float, from_currency: str, to_currency: str, exchange_rates: Dict[str, float]) -> float:
    """Convert price from one currency to another using exchange rates."""
    if from_currency == to_currency:
        return price
    if from_currency in exchange_rates:
        return price * exchange_rates[from_currency]
    return price


@router.get("/live")
async def get_live_market_data(
    currency: Optional[str] = Query(None, description="Currency for display (USD or CAD)"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get live market data for all holdings in current user's portfolio with currency conversion.
    Uses Redis cache when available for faster response times.
    """
    portfolio = await get_user_portfolio(db, current_user.id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )

    # Determine display currency
    display_currency = (currency or portfolio.currency or "USD").upper()

    # ── Full-response cache (5 min TTL) ──────────────────────────────────────
    redis_client = await get_redis_client()
    live_cache_key = f"portfolio:{portfolio.id}:live_market:{display_currency}"
    cached_response = await redis_client.get(live_cache_key)
    if cached_response:
        logger.info(f"[MARKET_LIVE] Full cache hit for portfolio {portfolio.id}")
        return cached_response

    exchange_service = get_exchange_rate_service()

    # Pre-fetch exchange rates
    exchange_rates = {}

    # Get all holdings
    holdings = await get_portfolio_holdings(db, portfolio.id)

    if not holdings:
        return {
            "holdings": [],
            "market_data": {},
            "cash_balance": convert_price(portfolio.cash_balance or 0, portfolio.currency, display_currency, {}),
            "portfolio_currency": portfolio.currency,
            "display_currency": display_currency,
            "updated_at": datetime.utcnow().isoformat(),
            "message": "No holdings found in portfolio"
        }

    # Collect all currencies needed for conversion
    currencies_needed = set()
    for holding in holdings:
        if holding.asset and holding.asset.currency:
            currencies_needed.add(holding.asset.currency)

    # Pre-fetch exchange rates
    for curr in currencies_needed:
        if curr != display_currency:
            rate = await exchange_service.get_exchange_rate(curr, display_currency)
            exchange_rates[curr] = rate
            logger.info(f"[MARKET_LIVE] Exchange rate {curr} -> {display_currency}: {rate}")

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

    # ── Helpers: cached wrappers for slow asset-info calls ───────────────────
    async def get_cached_asset_info(ticker: str, asset_type: str):
        """Return cached asset info or fetch + cache with 15-min TTL.

        Mutual fund fetches use a shared Barchart XSRF session and must NOT
        be called from multiple threads simultaneously. All other asset types
        are safe to run in a thread-pool executor for true parallelism.
        """
        ck = f"asset_info:{ticker}:{asset_type}"
        cached = await redis_client.get(ck)
        if cached:
            return cached
        if asset_type == 'mutual_fund':
            # Keep on event-loop thread — shared session, XSRF-token safety
            data = await FinanceService.get_asset_info(ticker, asset_type)
        else:
            # yfinance / etc. are blocking; run in thread pool so gather() parallelises
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(
                None,
                lambda t=ticker, at=asset_type: asyncio.run(FinanceService.get_asset_info(t, at))
            )
        if data:
            await redis_client.set(ck, data, ttl=900)
        return data

    async def get_cached_ohlc(ticker: str):
        """Return cached OHLC data or fetch + cache with 15-min TTL."""
        ck = f"ohlc:{ticker}"
        cached = await redis_client.get(ck)
        if cached:
            return cached
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None,
            lambda t=ticker: asyncio.run(FinanceService.get_ohlc_data(t))
        )
        if data:
            await redis_client.set(ck, data, ttl=900)
        return data

    # ── Fetch mutual fund / crypto / OHLC data in parallel ───────────────────
    async def fetch_mf(holding):
        try:
            data = await get_cached_asset_info(holding.ticker, 'mutual_fund')
            if data and 'current_price' in data:
                holding.current_price = data['current_price']
                holding._temp_change_percent = data.get('change_percent', 0)
                holding._temp_change = data.get('change', 0)
                if holding.asset:
                    holding.asset.current_price = data['current_price']
                    holding.asset.last_price_update = datetime.utcnow()
            else:
                holding._temp_change_percent = 0
                holding._temp_change = 0
        except Exception as e:
            logger.error(f"Error fetching mutual fund data for {holding.ticker}: {e}")
            holding._temp_change_percent = 0
            holding._temp_change = 0

    async def fetch_crypto(holding):
        try:
            data = await get_cached_asset_info(holding.ticker, 'crypto')
            if data and 'current_price' in data:
                holding.current_price = data['current_price']
                if holding.asset and holding.asset.current_price:
                    old_price = holding.asset.current_price
                    holding._temp_change_percent = ((data['current_price'] - old_price) / old_price) * 100
                else:
                    holding._temp_change_percent = 0
                if holding.asset:
                    holding.asset.current_price = data['current_price']
                    holding.asset.last_price_update = datetime.utcnow()
            else:
                holding._temp_change_percent = 0
        except Exception as e:
            logger.error(f"Error fetching crypto data for {holding.ticker}: {e}")
            holding._temp_change_percent = 0

    async def fetch_ohlc(holding):
        try:
            data = await get_cached_ohlc(holding.ticker)
            if data and 'current_price' in data:
                holding.current_price = data['current_price']
                holding._temp_change_percent = data.get('change_percent', 0)
                holding._temp_change = data.get('change', 0)
                if holding.asset:
                    holding.asset.current_price = data['current_price']
                    holding.asset.last_price_update = datetime.utcnow()
            else:
                holding._temp_change_percent = 0
                holding._temp_change = 0
        except Exception as e:
            logger.error(f"Error fetching OHLC data for {holding.ticker}: {e}")
            holding._temp_change_percent = 0
            holding._temp_change = 0

    # Mutual funds must run sequentially — shared Barchart XSRF session
    for h in mutual_fund_holdings:
        await fetch_mf(h)

    # Crypto and OHLC: truly parallel via thread-pool executors inside helpers
    await asyncio.gather(
        *[fetch_crypto(h) for h in crypto_holdings],
        *[fetch_ohlc(h) for h in unsupported_stock_holdings],
    )

    # Commit database updates for prices
    await db.commit()

    if not stock_symbols:
        # Still return holdings even if no Finnhub-supported tickers
        enriched_holdings = []
        for holding in holdings:
            # Get asset currency
            asset_currency = holding.asset.currency if holding.asset else "USD"

            # CRITICAL FIX: Always calculate cost_basis and market_value from database fields
            current_price_fallback = holding.current_price or holding.average_cost

            # Apply currency conversion
            converted_avg_cost = convert_price(holding.average_cost, asset_currency, display_currency, exchange_rates)
            converted_current_price = convert_price(current_price_fallback, asset_currency, display_currency, exchange_rates)

            calculated_cost_basis = holding.quantity * converted_avg_cost
            calculated_market_value = holding.quantity * converted_current_price

            holding_dict = {
                "id": holding.id,
                "ticker": holding.ticker,
                "quantity": holding.quantity,
                "average_cost": converted_avg_cost,
                "cost_basis": calculated_cost_basis,  # Always calculate fresh
                "asset": {
                    "name": holding.asset.name if holding.asset else holding.ticker,
                    "ticker": holding.ticker
                },
                "current_price": converted_current_price,
                "market_value": calculated_market_value,  # Always calculate fresh
            }

            # Check if we have temp change_percent (for mutual funds, crypto, and unsupported stocks)
            if hasattr(holding, '_temp_change_percent'):
                holding_dict["change_percent"] = holding._temp_change_percent
                # Use temp_change if available (from OHLC), otherwise calculate
                if hasattr(holding, '_temp_change'):
                    # Convert the change amount to display currency
                    converted_change = convert_price(holding._temp_change, asset_currency, display_currency, exchange_rates)
                    holding_dict["change"] = converted_change
                elif holding._temp_change_percent and converted_current_price:
                    holding_dict["change"] = (converted_current_price * holding._temp_change_percent) / 100
                else:
                    holding_dict["change"] = 0
            else:
                holding_dict["change_percent"] = 0
                holding_dict["change"] = 0

            enriched_holdings.append(holding_dict)

        early_response = {
            "holdings": enriched_holdings,
            "market_data": {},
            "cash_balance": convert_price(portfolio.cash_balance or 0, portfolio.currency, display_currency, exchange_rates),
            "portfolio_currency": portfolio.currency,
            "display_currency": display_currency,
            "updated_at": datetime.utcnow().isoformat()
        }
        await redis_client.set(live_cache_key, early_response, ttl=300)
        return early_response

    # Update active symbols for WebSocket background task (only for stocks)
    if stock_symbols:
        ws_manager = get_ws_manager()
        await ws_manager.update_active_symbols(stock_symbols)

    # Try to get cached data first for faster response
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
            await redis_client.set(cache_key, quote, ttl=900)  # 15 minute cache

    # Enrich holdings with live market data
    enriched_holdings = []
    for holding in holdings:
        # Get asset currency
        asset_currency = holding.asset.currency if holding.asset else "USD"

        # CRITICAL FIX: Always calculate cost_basis from database fields, never use cached value
        converted_avg_cost = convert_price(holding.average_cost, asset_currency, display_currency, exchange_rates)
        calculated_cost_basis = holding.quantity * converted_avg_cost

        holding_dict = {
            "id": holding.id,
            "ticker": holding.ticker,
            "quantity": holding.quantity,
            "average_cost": converted_avg_cost,
            "cost_basis": calculated_cost_basis,  # Always calculate fresh
            "asset": {
                "name": holding.asset.name if holding.asset else holding.ticker,
                "ticker": holding.ticker
            }
        }

        # Add live market data if available
        if holding.ticker in market_data:
            # Stock data from Finnhub - convert to display currency
            quote = market_data[holding.ticker]
            converted_current_price = convert_price(quote["current_price"], asset_currency, display_currency, exchange_rates)
            converted_change = convert_price(quote["change"], asset_currency, display_currency, exchange_rates)

            holding_dict["current_price"] = converted_current_price
            holding_dict["market_value"] = converted_current_price * holding.quantity
            holding_dict["change_percent"] = quote["change_percent"]  # Percentage stays the same
            holding_dict["change"] = converted_change
        else:
            # Use stored price if live data not available (e.g., MAU.TO, mutual funds, crypto)
            # CRITICAL FIX: Always calculate market_value from quantity and price
            current_price_fallback = holding.current_price or holding.average_cost
            converted_current_price = convert_price(current_price_fallback, asset_currency, display_currency, exchange_rates)

            holding_dict["current_price"] = converted_current_price
            holding_dict["market_value"] = holding.quantity * converted_current_price

            # Check if we have temp change_percent (for mutual funds, crypto, and unsupported stocks)
            if hasattr(holding, '_temp_change_percent'):
                holding_dict["change_percent"] = holding._temp_change_percent
                # Use temp_change if available (from OHLC), otherwise calculate
                if hasattr(holding, '_temp_change'):
                    converted_change = convert_price(holding._temp_change, asset_currency, display_currency, exchange_rates)
                    holding_dict["change"] = converted_change
                elif holding._temp_change_percent and converted_current_price:
                    holding_dict["change"] = (converted_current_price * holding._temp_change_percent) / 100
                else:
                    holding_dict["change"] = 0
            else:
                holding_dict["change_percent"] = 0
                holding_dict["change"] = 0

        enriched_holdings.append(holding_dict)

    response = {
        "holdings": enriched_holdings,
        "market_data": market_data,
        "cash_balance": convert_price(portfolio.cash_balance or 0, portfolio.currency, display_currency, exchange_rates),
        "portfolio_currency": portfolio.currency,
        "display_currency": display_currency,
        "updated_at": datetime.utcnow().isoformat()
    }
    # Cache full response for 5 minutes
    await redis_client.set(live_cache_key, response, ttl=300)
    return response


@router.get("/ytd")
async def get_ytd_data(
    currency: Optional[str] = Query(None, description="Currency for display (USD or CAD)"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get YTD return for each holding. Cached for 24h since YTD is a daily metric.
    """
    portfolio = await get_user_portfolio(db, current_user.id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )

    display_currency = (currency or portfolio.currency or "USD").upper()
    cache_key = f"portfolio:{portfolio.id}:ytd:v2"
    redis_client = await get_redis_client()

    # Try cache first (24h TTL — YTD only changes meaningfully once a day)
    cached = await redis_client.get(cache_key)
    if cached:
        logger.info(f"Cache hit for portfolio {portfolio.id} YTD data")
        return cached

    holdings = await get_portfolio_holdings(db, portfolio.id)
    valid_holdings = [h for h in holdings if h.ticker]

    # Separate by data source
    mutual_fund_holdings = [h for h in valid_holdings if h.asset and h.asset.asset_type == "mutual_fund"]
    other_holdings = [h for h in valid_holdings if h not in mutual_fund_holdings]

    ytd_map: Dict[str, Optional[float]] = {}

    # ── Stocks / ETFs / Crypto: single batch yfinance download ──────────────
    if other_holdings:
        import yfinance as yf
        from datetime import datetime as dt

        year_start = dt(dt.now().year, 1, 1)
        # Crypto tickers need "-USD" suffix for yfinance
        def yf_symbol(holding):
            t = holding.ticker
            if holding.asset and holding.asset.asset_type == "crypto" and "-USD" not in t.upper():
                return f"{t.upper()}-USD"
            return t

        symbol_map = {yf_symbol(h): h.ticker for h in other_holdings}
        symbols = list(symbol_map.keys())

        try:
            loop = asyncio.get_event_loop()
            # yfinance download is blocking — run in thread pool
            hist = await loop.run_in_executor(
                None,
                lambda: yf.download(symbols, start=year_start, progress=False, auto_adjust=True, threads=True)
            )

            if hist is not None and not hist.empty:
                import pandas as _pd
                # yfinance multi-ticker download → MultiIndex columns ('Close','AAPL')
                # Single-ticker download (older yfinance) → flat columns 'Close', 'Open'
                if isinstance(hist.columns, _pd.MultiIndex):
                    close = hist["Close"]   # DataFrame with ticker symbols as columns
                else:
                    # Flat: rename Close → ticker so the lookup below works uniformly
                    close = hist[["Close"]].rename(columns={"Close": symbols[0]}) if len(symbols) == 1 else hist

                for yf_sym, orig_ticker in symbol_map.items():
                    try:
                        col = yf_sym if yf_sym in close.columns else (
                            orig_ticker if orig_ticker in close.columns else None
                        )
                        if col is None:
                            ytd_map[orig_ticker] = None
                            continue
                        series = close[col].dropna()
                        if len(series) >= 2:
                            ytd_map[orig_ticker] = round(
                                (float(series.iloc[-1]) - float(series.iloc[0])) / float(series.iloc[0]) * 100, 2
                            )
                        else:
                            ytd_map[orig_ticker] = None
                    except Exception as e:
                        logger.warning(f"YTD parse failed for {orig_ticker}: {e}")
                        ytd_map[orig_ticker] = None
        except Exception as e:
            logger.warning(f"Batch yfinance YTD download failed: {e}")
            for h in other_holdings:
                ytd_map[h.ticker] = None

    # ── Mutual funds: run sequentially in one thread ─────────────────────────
    # The Barchart XSRF fetch uses a shared module-level requests.Session, so
    # parallel threads would clobber each other's cookies. Sequential is safe
    # and still non-blocking for the main event loop.
    if mutual_fund_holdings:
        def sync_all_mf_ytd():
            import asyncio as _aio
            results: Dict[str, Optional[float]] = {}
            for h in mutual_fund_holdings:
                try:
                    perf = _aio.run(FinanceService.calculate_ticker_performance(
                        h.ticker, "mutual_fund", ["ytd"]
                    ))
                    results[h.ticker] = perf.get("ytd_return")
                except Exception as e:
                    logger.warning(f"Mutual fund YTD failed for {h.ticker}: {e}")
                    results[h.ticker] = None
            return results

        loop = asyncio.get_event_loop()
        mf_map = await loop.run_in_executor(None, sync_all_mf_ytd)
        ytd_map.update(mf_map)

    ytd_data = [{"ticker": h.ticker, "ytd_return": ytd_map.get(h.ticker)} for h in valid_holdings]
    result = {"ytd_data": ytd_data}
    # Only use 24h TTL when we actually got data — a transient failure (e.g. network error
    # on first cold start) would otherwise poison the cache for a full day.
    has_data = any(d.get("ytd_return") is not None for d in ytd_data)
    await redis_client.set(cache_key, result, ttl=86400 if has_data else 60)
    return result


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
