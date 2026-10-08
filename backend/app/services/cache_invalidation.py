"""Invalidate every currency and analytics variant after a portfolio mutation."""
from app.core.redis_client import get_redis_client


async def invalidate_portfolio_cache(portfolio_id):
    cache = await get_redis_client()
    await cache.delete_prefix(f"portfolio:{portfolio_id}:")
    await cache.delete_prefix(f"dashboard:overview:{portfolio_id}:")
