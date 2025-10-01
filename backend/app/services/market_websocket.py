"""
WebSocket service for streaming live market data with Redis caching.
"""

import asyncio
import json
import logging
from typing import Set, Dict, Any, Optional
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis_client import get_redis_client
from app.services.finnhub_service import get_finnhub_service
from app.core.config import settings

logger = logging.getLogger(__name__)

# Tickers not supported by Finnhub free tier
UNSUPPORTED_TICKERS = ["MAU.TO"]


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
        redis_client = await get_redis_client()

        historical_data = {}
        for symbol in symbols:
            if symbol in UNSUPPORTED_TICKERS:
                continue

            cache_key = f"stock:history:{symbol}"
            cached_history = await redis_client.lrange(cache_key, 0, -1)

            if cached_history:
                # Redis returns newest first (LPUSH), so reverse for chronological order
                historical_data[symbol] = list(reversed(cached_history))

        if historical_data:
            await self.send_personal_message({
                "type": "historical",
                "data": historical_data,
                "timestamp": datetime.utcnow().isoformat()
            }, websocket)
            logger.info(f"Sent historical data for {len(historical_data)} symbols")

    async def fetch_and_cache_market_data(self, symbols: list[str]) -> Dict[str, Any]:
        """Fetch market data and cache it in Redis."""
        finnhub_service = get_finnhub_service()
        redis_client = await get_redis_client()

        market_data = {}
        current_time = datetime.utcnow()
        timestamp = current_time.isoformat()

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
                        "time": current_time.strftime("%H:%M:%S"),
                        "price": quote["current_price"],
                        "timestamp": int(current_time.timestamp())
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
        logger.info("Starting background market data update loop")

        while self.is_running:
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
                    logger.info(f"Broadcasted market data for {len(market_data)} symbols to {len(self.active_connections)} clients")

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
        if not self.is_running:
            self.is_running = True
            self.background_task = asyncio.create_task(self.background_update_loop())
            logger.info("Background market data updates started")

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
