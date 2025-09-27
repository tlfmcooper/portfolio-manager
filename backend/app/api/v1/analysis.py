"""
API endpoints for portfolio analysis.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.portfolio_analysis import AdvancedPortfolioAnalytics

router = APIRouter()


@router.get("/portfolios/{portfolio_id}/analysis/metrics")
async def get_portfolio_metrics(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get portfolio metrics."""
    analytics = AdvancedPortfolioAnalytics(portfolio_id, db)
    metrics = await analytics.calculate_portfolio_metrics()
    return metrics


@router.get("/portfolios/{portfolio_id}/analysis/sector-allocation")
async def get_sector_allocation(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get portfolio sector allocation."""
    analytics = AdvancedPortfolioAnalytics(portfolio_id, db)
    allocation = await analytics.sector_analysis()
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
