"""
Exchange rate service for currency conversion.
Uses exchangerate.host API with API key and frankfurter.app as backup.
"""

import httpx
from typing import Optional, Dict
from datetime import datetime, timedelta
from app.core.redis_client import get_redis_client
from app.core.config import settings
import json
import logging

logger = logging.getLogger(__name__)

# Exchange rate API configuration
# Primary API (requires API key) - Updated to /live endpoint
EXCHANGE_RATE_API_URL = "https://api.exchangerate.host/live"
# Backup API (frankfurter.app is free and doesn't require API key)
BACKUP_API_URL = "https://api.frankfurter.app/latest"
CACHE_TTL = 3600  # 1 hour in seconds
SUPPORTED_CURRENCIES = ["USD", "CAD"]


class ExchangeRateService:
    """Service for fetching and caching exchange rates."""

    def __init__(self):
        self.redis_client = None
        self._redis_initialized = False

    async def _ensure_redis(self):
        """Ensure Redis client is initialized."""
        if not self._redis_initialized:
            try:
                self.redis_client = await get_redis_client()
                self._redis_initialized = True
            except Exception as e:
                logger.warning(
                    f"Redis not available, exchange rates will not be cached: {e}"
                )
                self.redis_client = None

    def _get_cache_key(self, from_currency: str, to_currency: str) -> str:
        """Generate cache key for exchange rate."""
        return f"exchange_rate:{from_currency}:{to_currency}"

    async def _get_from_cache(
        self, from_currency: str, to_currency: str
    ) -> Optional[float]:
        """Get exchange rate from cache."""
        await self._ensure_redis()

        if not self.redis_client:
            return None

        try:
            cache_key = self._get_cache_key(from_currency, to_currency)
            cached_value = await self.redis_client.get(cache_key)

            if cached_value:
                # cached_value is already deserialized by RedisClient
                return float(cached_value.get("rate"))
        except Exception as e:
            logger.warning(f"Error getting exchange rate from cache: {e}")

        return None

    async def _set_to_cache(self, from_currency: str, to_currency: str, rate: float):
        """Set exchange rate to cache."""
        await self._ensure_redis()

        if not self.redis_client:
            return

        try:
            cache_key = self._get_cache_key(from_currency, to_currency)
            cache_data = {"rate": rate, "timestamp": datetime.utcnow().isoformat()}
            await self.redis_client.set(cache_key, cache_data, ttl=CACHE_TTL)
        except Exception as e:
            logger.warning(f"Error setting exchange rate to cache: {e}")

    async def _fetch_from_api(
        self, from_currency: str, to_currency: str
    ) -> Optional[float]:
        """Fetch exchange rate from external API with fallback."""
        # Try primary API first (with API key)
        if settings.EXCHANGE_RATES_API_KEY:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    params = {
                        "source": from_currency,
                        "currencies": to_currency,
                        "access_key": settings.EXCHANGE_RATES_API_KEY
                    }
                    response = await client.get(EXCHANGE_RATE_API_URL, params=params)
                    response.raise_for_status()

                    data = response.json()

                    if data.get("success") and "quotes" in data:
                        # The API returns quotes in format like "USDCAD": 1.36
                        quote_key = f"{from_currency}{to_currency}"
                        rate = data["quotes"].get(quote_key)
                        if rate:
                            logger.info(
                                f"Fetched exchange rate from primary API: {from_currency}/{to_currency} = {rate}"
                            )
                            return float(rate)

            except httpx.HTTPError as e:
                logger.warning(f"Primary API failed: {e}. Trying backup API...")
            except Exception as e:
                logger.warning(f"Primary API error: {e}. Trying backup API...")
        else:
            logger.info("No API key configured for primary API, using backup API")

        # Try backup API (frankfurter.app)
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                params = {"from": from_currency, "to": to_currency}
                response = await client.get(BACKUP_API_URL, params=params)
                response.raise_for_status()

                data = response.json()

                if "rates" in data:
                    rate = data["rates"].get(to_currency)
                    if rate:
                        logger.info(
                            f"Fetched exchange rate from backup API: {from_currency}/{to_currency} = {rate}"
                        )
                        return float(rate)

                logger.error(f"Invalid response from backup API: {data}")
                return None

        except httpx.HTTPError as e:
            logger.error(f"Backup API HTTP error: {e}")
            return None
        except Exception as e:
            logger.error(f"Backup API error: {e}")
            return None

    async def get_exchange_rate(
        self, from_currency: str, to_currency: str, use_cache: bool = True
    ) -> float:
        """
        Get exchange rate from one currency to another.

        Args:
            from_currency: Source currency code (e.g., 'USD')
            to_currency: Target currency code (e.g., 'CAD')
            use_cache: Whether to use cached rates (default: True)

        Returns:
            Exchange rate as float. Returns 1.0 if same currency or on error.
        """
        # Normalize currency codes
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()

        # Same currency check
        if from_currency == to_currency:
            return 1.0

        # Validate currencies
        if (
            from_currency not in SUPPORTED_CURRENCIES
            or to_currency not in SUPPORTED_CURRENCIES
        ):
            logger.warning(f"Unsupported currency pair: {from_currency}/{to_currency}")
            return 1.0

        # Try cache first
        if use_cache:
            cached_rate = await self._get_from_cache(from_currency, to_currency)
            if cached_rate is not None:
                logger.info(
                    f"Using cached exchange rate {from_currency}/{to_currency}: {cached_rate}"
                )
                return cached_rate

        # Fetch from API
        logger.info(f"Fetching exchange rate {from_currency}/{to_currency} from API")
        rate = await self._fetch_from_api(from_currency, to_currency)

        if rate is not None:
            # Cache the rate
            await self._set_to_cache(from_currency, to_currency, rate)
            return rate

        # Fallback: try to use stale cache or return 1.0
        logger.warning(f"Failed to fetch exchange rate, using fallback")
        cached_rate = await self._get_from_cache(from_currency, to_currency)
        return cached_rate if cached_rate is not None else 1.0

    async def convert_amount(
        self,
        amount: float,
        from_currency: str,
        to_currency: str,
        use_cache: bool = True,
    ) -> float:
        """
        Convert an amount from one currency to another.

        Args:
            amount: Amount to convert
            from_currency: Source currency code
            to_currency: Target currency code
            use_cache: Whether to use cached rates

        Returns:
            Converted amount
        """
        if amount == 0:
            return 0.0

        rate = await self.get_exchange_rate(from_currency, to_currency, use_cache)
        return amount * rate

    async def get_rate_info(self, from_currency: str, to_currency: str) -> Dict:
        """
        Get exchange rate with metadata.

        Returns:
            Dictionary with rate, timestamp, and source information
        """
        rate = await self.get_exchange_rate(from_currency, to_currency)

        return {
            "from_currency": from_currency.upper(),
            "to_currency": to_currency.upper(),
            "rate": rate,
            "timestamp": datetime.utcnow().isoformat(),
            "source": "exchangerate.host",
        }


# Singleton instance
_exchange_rate_service = None


def get_exchange_rate_service() -> ExchangeRateService:
    """Get or create exchange rate service instance."""
    global _exchange_rate_service
    if _exchange_rate_service is None:
        _exchange_rate_service = ExchangeRateService()
    return _exchange_rate_service
