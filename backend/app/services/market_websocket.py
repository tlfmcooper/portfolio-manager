"""
WebSocket service for streaming live market data with Redis caching.
"""

import asyncio
import json
import logging
from typing import Set, Dict, Any, Optional
from datetime import datetime, time
from zoneinfo import ZoneInfo
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis_client import get_redis_client
from app.services.finnhub_service import get_finnhub_service
from app.core.config import settings

logger = logging.getLogger(__name__)

# Tickers not supported by Finnhub free tier
UNSUPPORTED_TICKERS = ["MAU.TO", "BTCC.TO"]

# US market hours (Eastern Time)
MARKET_OPEN_TIME = time(9, 30)  # 9:30 AM ET
MARKET_CLOSE_TIME = time(16, 0)  # 4:00 PM ET


def get_market_open_today() -> datetime:
    """Get today's market open time in UTC."""
    et_tz = ZoneInfo("America/New_York")
    now_et = datetime.now(et_tz)
    market_open_et = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
    return market_open_et.astimezone(ZoneInfo("UTC"))


def is_market_hours() -> bool:
    """Check if current time is during market hours (9:30 AM - 4:00 PM ET)."""
    et_tz = ZoneInfo("America/New_York")
    now_et = datetime.now(et_tz)
    current_time = now_et.time()

    # Check if it's a weekday (Monday=0, Sunday=6)
    if now_et.weekday() >= 5:  # Saturday or Sunday
        return False

    return MARKET_OPEN_TIME <= current_time <= MARKET_CLOSE_TIME


def filter_historical_data_for_today(historical_data: list) -> list:
    """
    Filter historical data to only include points from today's market session.
    This prevents showing flat data from after-hours/overnight periods.
    """
    if not historical_data:
        return historical_data

    is_market_open = is_market_hours()
    logger.info(f"Filter: Market is {'OPEN' if is_market_open else 'CLOSED'}")

    # Only filter during market hours or shortly after
    if not is_market_open:
        # If markets are closed, check if we should still filter
        et_tz = ZoneInfo("America/New_York")
        now_et = datetime.now(et_tz)

        logger.info(f"Filter: Markets closed. Current ET time: {now_et.time()}")

        # If it's before market open today, show all historical data
        if now_et.time() < MARKET_OPEN_TIME:
            logger.info("Filter: Before market open - showing all data")
            return historical_data

        # If it's after market close but same day, filter to today's session
        if now_et.time() > MARKET_CLOSE_TIME and now_et.weekday() < 5:
            logger.info("Filter: After close same day - filtering to today")
            # Continue to filter for today's session
            pass
        else:
            # Weekend or way after hours, show all data
            logger.info("Filter: Weekend/late - showing all data")
            return historical_data

    # Get today's market open time
    market_open_utc = get_market_open_today()
    market_open_timestamp = int(market_open_utc.timestamp())

    logger.info(f"Filter: Market open timestamp: {market_open_timestamp} ({market_open_utc})")

    # Filter data points to only those from market open onwards
    filtered_data = [
        point for point in historical_data
        if isinstance(point, dict) and point.get("timestamp", 0) >= market_open_timestamp
    ]

    logger.info(f"Filter: Original: {len(historical_data)} points, Filtered: {len(filtered_data)} points")

    # If filtering removed all data, return at least the last few points
    if not filtered_data and len(historical_data) > 0:
        logger.info("Filter: No data after filtering - returning last 10 points")
        return historical_data[-10:]  # Last 10 points as fallback

    return filtered_data


class MarketDataWebSocketManager:
    """Manages WebSocket connections for live market data streaming."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.background_task: Optional[asyncio.Task] = None
        self.is_running = False
        self.update_interval = 15  # seconds - Finnhub free tier safe rate

    async def connect(self, websocket: WebSocket):
        """Accept WebSocket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

        # Start background task if not running
        if not self.is_running:
            self.start_background_updates()

    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection."""
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

        # Stop background task if no connections
        if len(self.active_connections) == 0 and self.background_task:
            self.stop_background_updates()

    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """Send message to specific WebSocket."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending message to WebSocket: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected WebSockets."""
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to WebSocket: {e}")
                disconnected.add(connection)

        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)

    async def send_historical_data(self, websocket: WebSocket, symbols: list[str]):
        """Send cached historical data to newly connected client."""
        print(f"\n{'='*80}")
        print(f">>> send_historical_data called for symbols: {symbols}")
        print(f"{'='*80}\n")
        logger.info(f"=== send_historical_data called for symbols: {symbols} ===")
        redis_client = await get_redis_client()

        historical_data = {}
        print(f">>> Processing {len(symbols)} symbols...")
        for symbol in symbols:
            print(f">>> Checking symbol: {symbol}")
            if symbol in UNSUPPORTED_TICKERS:
                print(f">>> {symbol} is UNSUPPORTED, skipping")
                continue

            cache_key = f"stock:history:{symbol}"
            cached_history = await redis_client.lrange(cache_key, 0, -1)
            print(f">>> {symbol}: Found {len(cached_history) if cached_history else 0} cached points")

            if cached_history:
                # Redis returns newest first (LPUSH), so reverse for chronological order
                chronological_data = list(reversed(cached_history))

                logger.info(f"[{symbol}] Cached history: {len(chronological_data)} points")
                if chronological_data:
                    first_ts = chronological_data[0].get("timestamp", 0) if isinstance(chronological_data[0], dict) else 0
                    last_ts = chronological_data[-1].get("timestamp", 0) if isinstance(chronological_data[-1], dict) else 0
                    logger.info(f"[{symbol}] Time range: {datetime.fromtimestamp(first_ts)} to {datetime.fromtimestamp(last_ts)}")

                # Filter to only show data from today's market session
                # This prevents showing flat overnight/after-hours data
                filtered_data = filter_historical_data_for_today(chronological_data)

                logger.info(f"[{symbol}] After filtering: {len(filtered_data)} points")
                if filtered_data:
                    first_ts = filtered_data[0].get("timestamp", 0) if isinstance(filtered_data[0], dict) else 0
                    last_ts = filtered_data[-1].get("timestamp", 0) if isinstance(filtered_data[-1], dict) else 0
                    logger.info(f"[{symbol}] Filtered range: {datetime.fromtimestamp(first_ts)} to {datetime.fromtimestamp(last_ts)}")

                if filtered_data:
                    historical_data[symbol] = filtered_data

        if historical_data:
            await self.send_personal_message({
                "type": "historical",
                "data": historical_data,
                "timestamp": datetime.utcnow().isoformat()
            }, websocket)
            logger.info(f"Sent filtered historical data for {len(historical_data)} symbols")

    async def fetch_and_cache_market_data(self, symbols: list[str]) -> Dict[str, Any]:
        """Fetch market data and cache it in Redis."""
        finnhub_service = get_finnhub_service()
        redis_client = await get_redis_client()

        market_data = {}
        # Use Eastern Time for display consistency with US stock market
        et_tz = ZoneInfo("America/New_York")
        current_time_et = datetime.now(et_tz)
        current_time_utc = datetime.utcnow()
        timestamp = current_time_utc.isoformat()

        # Filter out unsupported symbols
        supported_symbols = [s for s in symbols if s not in UNSUPPORTED_TICKERS]

        if not supported_symbols:
            return {}

        # Fetch quotes with rate limiting
        for symbol in supported_symbols:
            try:
                quote = await finnhub_service.get_quote(symbol)
                if quote:
                    market_data[symbol] = quote

                    # Cache the quote
                    cache_key = f"stock:quote:{symbol}"
                    await redis_client.set(cache_key, quote, ttl=settings.STOCK_DATA_CACHE_TTL)

                    # Add to history list (keep last 200 points = ~50 minutes at 15s intervals)
                    history_key = f"stock:history:{symbol}"
                    data_point = {
                        "time": current_time_et.strftime("%H:%M:%S"),  # Display in ET
                        "price": quote["current_price"],
                        "timestamp": int(current_time_utc.timestamp())  # Keep UTC timestamp for calculations
                    }
                    await redis_client.lpush(history_key, data_point, max_length=200)

                # Rate limiting: 1.1 seconds between requests
                if len(supported_symbols) > 1:
                    await asyncio.sleep(1.1)

            except Exception as e:
                logger.error(f"Error fetching quote for {symbol}: {e}")

        return market_data

    async def background_update_loop(self):
        """Background task to continuously fetch and broadcast market data."""
        print("\n>>> BACKGROUND LOOP STARTED!")
        logger.info("Starting background market data update loop")

        while self.is_running:
            print(f">>> Background loop iteration, connections={len(self.active_connections)}")
            try:
                # Get active symbols from cache or default set
                redis_client = await get_redis_client()
                symbols_data = await redis_client.get("active:symbols")

                if symbols_data:
                    symbols = symbols_data
                else:
                    # Default symbols if none cached
                    symbols = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA"]

                # Fetch and cache market data
                market_data = await self.fetch_and_cache_market_data(symbols)

                if market_data and len(self.active_connections) > 0:
                    # Broadcast to all connected clients
                    await self.broadcast({
                        "type": "update",
                        "data": market_data,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    print(f">>> BROADCASTED {len(market_data)} symbols to {len(self.active_connections)} clients")
                    logger.info(f"Broadcasted market data for {len(market_data)} symbols to {len(self.active_connections)} clients")
                else:
                    print(f">>> No broadcast: market_data={len(market_data) if market_data else 0}, connections={len(self.active_connections)}")

                # Wait before next update
                await asyncio.sleep(self.update_interval)

            except asyncio.CancelledError:
                logger.info("Background update loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in background update loop: {e}")
                await asyncio.sleep(self.update_interval)

    def start_background_updates(self):
        """Start background update task."""
        print(f"\n>>> start_background_updates called, is_running={self.is_running}")
        if not self.is_running:
            self.is_running = True
            self.background_task = asyncio.create_task(self.background_update_loop())
            print(">>> Background task created!")
            logger.info("Background market data updates started")
        else:
            print(">>> Background task already running")

    def stop_background_updates(self):
        """Stop background update task."""
        if self.is_running and self.background_task:
            self.is_running = False
            self.background_task.cancel()
            logger.info("Background market data updates stopped")

    async def update_active_symbols(self, symbols: list[str]):
        """Update the list of symbols to track."""
        redis_client = await get_redis_client()
        # Store unique symbols, excluding unsupported ones
        unique_symbols = list(set([s for s in symbols if s not in UNSUPPORTED_TICKERS]))
        await redis_client.set("active:symbols", unique_symbols)
        logger.info(f"Updated active symbols: {unique_symbols}")


# Singleton instance
_ws_manager: Optional[MarketDataWebSocketManager] = None


def get_ws_manager() -> MarketDataWebSocketManager:
    """Get or create WebSocket manager instance."""
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = MarketDataWebSocketManager()
    return _ws_manager
