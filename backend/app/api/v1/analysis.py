"""Owned portfolio analytics with currency-aware caching and coalesced requests."""
from typing import Annotated, Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis_client import get_redis_client
from app.models import Portfolio, User
from app.services.portfolio_analysis import AdvancedPortfolioAnalytics
from app.schemas.scenario import ScenarioRequest
from app.services.portfolio_scenarios import PortfolioScenarioService
from app.utils.dependencies import get_current_active_user


async def require_portfolio(
    portfolio_id: int, db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(select(Portfolio.id).where(
        Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id, Portfolio.is_active.is_(True)))
    if result.scalar_one_or_none() is None:
        raise HTTPException(404, "Portfolio not found")


router = APIRouter(dependencies=[Depends(require_portfolio)])
Currency = Literal["USD", "CAD"]


async def cached_analysis(portfolio_id, db, currency, kind, method, ttl, **params):
    cache = await get_redis_client()
    key = f"portfolio:{portfolio_id}:{kind}:v3:{currency or 'default'}:{tuple(sorted(params.items()))}"

    async def load():
        analytics = AdvancedPortfolioAnalytics(portfolio_id, db, display_currency=currency)
        return await getattr(analytics, method)(**params)

    return await cache.get_or_load(key, load, ttl)


@router.post("/portfolios/{portfolio_id}/scenario")
async def analyze_scenario(portfolio_id: int, request: ScenarioRequest, db: AsyncSession = Depends(get_db)):
    """Preview allocations without persisting targets or changing holdings/cash."""
    return await PortfolioScenarioService(portfolio_id, db, request.currency).analyze(
        request.kind, preset=request.preset,
        weights=request.weights.weights if request.weights else None,
        scenarios=request.scenarios, time_horizon=request.time_horizon,
        multiplier=request.multiplier, floor=request.floor,
        cppi_time_horizon=request.cppi_time_horizon,
    )


@router.get("/portfolios/{portfolio_id}/metrics")
async def get_portfolio_metrics(portfolio_id: int, currency: Currency | None = None, db: AsyncSession = Depends(get_db)):
    return await cached_analysis(portfolio_id, db, currency, "metrics", "calculate_portfolio_metrics", 300)


@router.get("/portfolios/{portfolio_id}/account-performance")
async def get_account_performance(portfolio_id: int, currency: Currency | None = None, db: AsyncSession = Depends(get_db)):
    from datetime import date
    from app.services.account_performance import calculate_account_performance
    cache = await get_redis_client()
    return await cache.get_or_load(
        f"portfolio:{portfolio_id}:account-ytd:v1:{currency or 'default'}:{date.today()}",
        lambda: calculate_account_performance(portfolio_id, db, currency), 120)


@router.get("/portfolios/{portfolio_id}/sector-allocation")
async def get_sector_allocation(portfolio_id: int, currency: Currency | None = None, db: AsyncSession = Depends(get_db)):
    return await cached_analysis(portfolio_id, db, currency, "sector-allocation", "sector_analysis", 600, display_currency=currency)


@router.get("/portfolios/{portfolio_id}/efficient-frontier")
async def get_efficient_frontier(portfolio_id: int, currency: Currency | None = None, db: AsyncSession = Depends(get_db)):
    return await cached_analysis(portfolio_id, db, currency, "efficient-frontier", "generate_efficient_frontier", 900)


@router.get("/portfolios/{portfolio_id}/monte-carlo")
async def run_monte_carlo_simulation(
    portfolio_id: int, currency: Currency | None = None, db: AsyncSession = Depends(get_db),
    scenarios: Annotated[int, Query(ge=1, le=10000)] = 1000, time_horizon: Annotated[int, Query(ge=1, le=2520)] = 252,
):
    return await cached_analysis(portfolio_id, db, currency, "monte-carlo", "run_monte_carlo_simulation", 600,
                                 scenarios=scenarios, time_horizon=time_horizon)


@router.get("/portfolios/{portfolio_id}/cppi")
async def run_cppi_simulation(
    portfolio_id: int, currency: Currency | None = None, db: AsyncSession = Depends(get_db),
    multiplier: Annotated[int, Query(ge=1, le=10)] = 3, floor: Annotated[float, Query(gt=0, le=1)] = 0.8,
    time_horizon: Annotated[int, Query(ge=1, le=2520)] = 252,
):
    return await cached_analysis(portfolio_id, db, currency, "cppi", "run_cppi_simulation", 600,
                                 multiplier=multiplier, floor=floor, time_horizon=time_horizon)
