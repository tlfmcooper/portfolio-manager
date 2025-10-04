"""
Portfolio Analysis API Endpoints
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from app.services.mcp_server import PortfolioMCPTools

router = APIRouter()
mcp_tools = PortfolioMCPTools()


@router.get("/portfolios/{portfolio_id}/summary")
async def get_portfolio_summary(portfolio_id: int) -> Dict[str, Any]:
    """Get portfolio summary"""
    return mcp_tools.get_portfolio_summary(portfolio_id)


@router.get("/portfolios/{portfolio_id}/metrics")
async def get_portfolio_metrics(portfolio_id: int) -> Dict[str, Any]:
    """Get portfolio performance metrics"""
    return mcp_tools.calculate_portfolio_metrics(portfolio_id)


@router.get("/portfolios/{portfolio_id}/sector-allocation")
async def get_sector_allocation(portfolio_id: int) -> Dict[str, float]:
    """Get sector allocation breakdown"""
    return mcp_tools.get_sector_allocation(portfolio_id)


@router.get("/portfolios/{portfolio_id}/risk-metrics")
async def get_risk_metrics(portfolio_id: int) -> Dict[str, Any]:
    """Get comprehensive risk metrics"""
    return mcp_tools.get_risk_metrics(portfolio_id)


@router.get("/portfolios/{portfolio_id}/efficient-frontier")
async def get_efficient_frontier(portfolio_id: int) -> Dict[str, Any]:
    """Calculate efficient frontier"""
    return mcp_tools.run_efficient_frontier(portfolio_id)


@router.get("/portfolios/{portfolio_id}/monte-carlo")
async def run_monte_carlo(
    portfolio_id: int,
    scenarios: int = 1000,
    time_horizon: int = 252
) -> Dict[str, Any]:
    """Run Monte Carlo simulation"""
    return mcp_tools.run_monte_carlo(portfolio_id, scenarios, time_horizon)


@router.get("/portfolios/{portfolio_id}/cppi")
async def run_cppi(
    portfolio_id: int,
    multiplier: float = 3.0,
    floor: float = 0.8
) -> Dict[str, Any]:
    """Run CPPI strategy simulation"""
    return mcp_tools.run_cppi_simulation(portfolio_id, multiplier, floor)


@router.post("/portfolios/{portfolio_id}/simulate-rebalancing")
async def simulate_rebalancing(
    portfolio_id: int,
    allocation_changes: Dict[str, float]
) -> Dict[str, Any]:
    """Simulate portfolio rebalancing"""
    return mcp_tools.simulate_rebalancing(portfolio_id, allocation_changes)
