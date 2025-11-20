"""
Warm up Redis cache with stock data.
Run this locally or in Railway to pre-populate cache.
"""
import asyncio
from app.core.redis_client import get_redis_client
from app.services.finnhub_service import FinnhubService
from app.services.exchange_rate_service import ExchangeRateService
from app.core.config import settings


async def warm_cache():
    """Pre-populate Redis with common stock data."""
    print("🔥 Warming up Redis cache...")
    
    redis_client = await get_redis_client()
    finnhub = FinnhubService(settings.FINNHUB_API_KEY)
    exchange_service = ExchangeRateService(settings.EXCHANGE_RATES_API_KEY)
    
    # Popular stocks to cache
    symbols = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "META",
        "TSLA", "NVDA", "AMD", "NFLX", "DIS"
    ]
    
    print(f"📊 Fetching quotes for {len(symbols)} symbols...")
    for symbol in symbols:
        try:
            quote = await finnhub.get_quote(symbol)
            if quote:
                cache_key = f"stock:quote:{symbol}"
                await redis_client.set(
                    cache_key, 
                    quote, 
                    ttl=settings.STOCK_DATA_CACHE_TTL
                )
                print(f"✅ Cached {symbol}: ${quote.get('current_price', 'N/A')}")
        except Exception as e:
            print(f"❌ Failed to cache {symbol}: {e}")
        
        # Rate limiting
        await asyncio.sleep(0.5)
    
    # Cache exchange rates
    print("\n💱 Caching exchange rates...")
    try:
        rates = await exchange_service.get_exchange_rates("USD")
        if rates:
            print(f"✅ Cached {len(rates)} exchange rates")
    except Exception as e:
        print(f"❌ Failed to cache exchange rates: {e}")
    
    print("\n✨ Cache warming complete!")


if __name__ == "__main__":
    asyncio.run(warm_cache())
