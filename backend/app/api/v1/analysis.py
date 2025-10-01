"""
API endpoints for portfolio analysis.
"""
import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.portfolio_analysis import AdvancedPortfolioAnalytics
from app.core.redis_client import get_redis_client

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/portfolios/{portfolio_id}/analysis/metrics")
async def get_portfolio_metrics(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get portfolio metrics with Redis caching for faster response."""
    cache_key = f"portfolio:{portfolio_id}:metrics"
    redis_client = await get_redis_client()

    # Try cache first
    cached_metrics = await redis_client.get(cache_key)
    if cached_metrics:
        logger.info(f"Cache hit for portfolio {portfolio_id} metrics")
        return cached_metrics

    # Calculate if not cached
    analytics = AdvancedPortfolioAnalytics(portfolio_id, db)
    metrics = await analytics.calculate_portfolio_metrics()

    # Cache for 5 minutes
    await redis_client.set(cache_key, metrics, ttl=300)

    return metrics


@router.get("/portfolios/{portfolio_id}/analysis/sector-allocation")
async def get_sector_allocation(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get portfolio sector allocation with caching."""
    cache_key = f"portfolio:{portfolio_id}:sector-allocation"
    redis_client = await get_redis_client()

    # Try cache first
    cached_allocation = await redis_client.get(cache_key)
    if cached_allocation:
        logger.info(f"Cache hit for portfolio {portfolio_id} sector allocation")
        return cached_allocation

    # Calculate if not cached
    analytics = AdvancedPortfolioAnalytics(portfolio_id, db)
    allocation = await analytics.sector_analysis()

    # Cache for 10 minutes (sector allocation changes less frequently)
    await redis_client.set(cache_key, allocation, ttl=600)

    return allocation


@router.get("/portfolios/{portfolio_id}/analysis/efficient-frontier")
async def get_efficient_frontier(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get efficient frontier data."""
    analytics = AdvancedPortfolioAnalytics(portfolio_id, db)
    frontier_data = await analytics.generate_efficient_frontier()
    return frontier_data


@router.get("/portfolios/{portfolio_id}/analysis/monte-carlo")
async def run_monte_carlo_simulation(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    scenarios: int = 1000,
    time_horizon: int = 252,
):
    """Run a Monte Carlo simulation."""
    analytics = AdvancedPortfolioAnalytics(portfolio_id, db)
    simulation_data = await analytics.run_monte_carlo_simulation(
        scenarios=scenarios, time_horizon=time_horizon
    )
    return simulation_data


@router.get("/portfolios/{portfolio_id}/analysis/cppi")
async def run_cppi_simulation(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    multiplier: int = 3,
    floor: float = 0.8,
    time_horizon: int = 252,
):
    """Run a CPPI simulation."""
    analytics = AdvancedPortfolioAnalytics(portfolio_id, db)
    simulation_data = await analytics.run_cppi_simulation(
        multiplier=multiplier, floor=floor, time_horizon=time_horizon
    )
    return simulation_data
