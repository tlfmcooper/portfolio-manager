"""
Finnhub API service for fetching real-time market data.
"""

import httpx
from typing import Dict, List, Optional
from datetime import datetime
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


class FinnhubService:
    """Service for interacting with Finnhub API."""

    BASE_URL = "https://finnhub.io/api/v1"

    def __init__(self):
        self.api_key = settings.FINNHUB_API_KEY
        if not self.api_key:
            logger.warning("FINNHUB_API_KEY not found in settings")

    async def get_quote(self, symbol: str) -> Optional[Dict]:
        """
        Get real-time quote for a symbol.

        Args:
            symbol: Stock ticker symbol

        Returns:
            Dict with quote data or None if error
        """
        if not self.api_key:
            return None

        try:
            url = f"{self.BASE_URL}/quote"
            params = {"symbol": symbol.upper(), "token": self.api_key}

            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=10.0)
                response.raise_for_status()

                data = response.json()

                # Finnhub returns: c (current), h (high), l (low), o (open), pc (previous close), t (timestamp)
                if data.get("c"):
                    return {
                        "symbol": symbol.upper(),
                        "current_price": data.get("c"),
                        "open": data.get("o"),
                        "high": data.get("h"),
                        "low": data.get("l"),
                        "previous_close": data.get("pc"),
                        "change": (
                            data.get("c") - data.get("pc")
                            if data.get("c") and data.get("pc")
                            else 0
                        ),
                        "change_percent": (
                            ((data.get("c") - data.get("pc")) / data.get("pc") * 100)
                            if data.get("c") and data.get("pc")
                            else 0
                        ),
                        "timestamp": data.get("t"),
                        "updated_at": datetime.utcnow().isoformat(),
                    }

                return None

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching quote for {symbol}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching quote for {symbol}: {str(e)}")
            return None

    def get_multiple_quotes(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        Get quotes for multiple symbols (synchronous version for batch requests).

        Args:
            symbols: List of stock ticker symbols

        Returns:
            Dictionary mapping symbols to their quote data
        """
        if not self.api_key:
            return {}

        import asyncio

        async def fetch_all():
            results = {}
            for symbol in symbols:
                quote = await self.get_quote(symbol)
                if quote:
                    results[symbol.upper()] = quote
            return results

        try:
            # Run async code in sync context
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If already in async context, create new loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                results = loop.run_until_complete(fetch_all())
                loop.close()
            else:
                results = loop.run_until_complete(fetch_all())
            return results
        except Exception as e:
            logger.error(f"Error fetching multiple quotes: {str(e)}")
            return {}

    async def get_multiple_quotes_async(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        Get quotes for multiple symbols (async version for async contexts).
        Fetches quotes concurrently with rate limiting to respect Finnhub free tier limits (60/min).

        Args:
            symbols: List of stock ticker symbols

        Returns:
            Dictionary mapping symbols to their quote data
        """
        if not self.api_key:
            return {}

        import asyncio

        # Finnhub free tier: 60 calls/min
        # Use semaphore to limit concurrent requests (allow 30 concurrent requests)
        semaphore = asyncio.Semaphore(30)

        async def fetch_with_limit(symbol: str):
            async with semaphore:
                try:
                    quote = await self.get_quote(symbol)
                    return symbol.upper(), quote
                except Exception as e:
                    logger.warning(f"Failed to fetch quote for {symbol}: {e}")
                    return symbol.upper(), None

        # Fetch all quotes concurrently
        tasks = [fetch_with_limit(symbol) for symbol in symbols]
        results_list = await asyncio.gather(*tasks)

        # Convert to dict, filtering out None values
        results = {symbol: quote for symbol, quote in results_list if quote is not None}

        return results

    async def get_candles(
        self, symbol: str, resolution: str, from_timestamp: int, to_timestamp: int
    ) -> Optional[Dict]:
        """
        Get candlestick data for a symbol.

        Args:
            symbol: Stock ticker symbol
            resolution: Time resolution (1, 5, 15, 30, 60 for minutes; D, W, M for day/week/month)
            from_timestamp: Start time as UNIX timestamp
            to_timestamp: End time as UNIX timestamp

        Returns:
            Dict with candle data or None if error
        """
        if not self.api_key:
            return None

        try:
            url = f"{self.BASE_URL}/stock/candle"
            params = {
                "symbol": symbol.upper(),
                "resolution": resolution,
                "from": from_timestamp,
                "to": to_timestamp,
                "token": self.api_key,
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=10.0)
                response.raise_for_status()

                data = response.json()

                # Finnhub returns: c (close), h (high), l (low), o (open), t (timestamp), v (volume), s (status)
                if data.get("s") == "ok" and data.get("t"):
                    candles = []
                    timestamps = data.get("t", [])
                    opens = data.get("o", [])
                    highs = data.get("h", [])
                    lows = data.get("l", [])
                    closes = data.get("c", [])
                    volumes = data.get("v", [])

                    for i in range(len(timestamps)):
                        candles.append(
                            {
                                "time": datetime.fromtimestamp(timestamps[i]).strftime(
                                    "%H:%M"
                                ),
                                "timestamp": timestamps[i],
                                "open": opens[i],
                                "high": highs[i],
                                "low": lows[i],
                                "close": closes[i],
                                "volume": volumes[i],
                            }
                        )

                    return {
                        "symbol": symbol.upper(),
                        "resolution": resolution,
                        "candles": candles,
                        "status": "ok",
                    }
                else:
                    logger.warning(
                        f"No candle data available for {symbol}: status={data.get('s')}"
                    )
                    return None

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching candles for {symbol}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching candles for {symbol}: {str(e)}")
            return None


# Singleton instance
_finnhub_service = None


def get_finnhub_service() -> FinnhubService:
    """Get or create Finnhub service instance."""
    global _finnhub_service
    if _finnhub_service is None:
        _finnhub_service = FinnhubService()
    return _finnhub_service
