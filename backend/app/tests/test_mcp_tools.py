"""
Tests for MCP Portfolio Tools
"""
import pytest
from app.services.mcp_server import PortfolioMCPTools


@pytest.fixture
def mcp_tools():
    return PortfolioMCPTools()


def test_get_portfolio_summary(mcp_tools):
    """Test portfolio summary retrieval"""
    result = mcp_tools.get_portfolio_summary(portfolio_id=1)

    assert result is not None
    assert "portfolio_id" in result
    assert result["portfolio_id"] == 1
    assert "total_value" in result
    assert "holdings_count" in result


def test_calculate_portfolio_metrics(mcp_tools):
    """Test portfolio metrics calculation"""
    result = mcp_tools.calculate_portfolio_metrics(portfolio_id=1)

    assert result is not None
    assert "annual_return" in result
    assert "volatility" in result
    assert "sharpe_ratio" in result
    assert "sortino_ratio" in result
    assert "max_drawdown" in result


def test_get_sector_allocation(mcp_tools):
    """Test sector allocation retrieval"""
    result = mcp_tools.get_sector_allocation(portfolio_id=1)

    assert result is not None
    assert isinstance(result, dict)
    assert len(result) > 0
    # Check that percentages sum to approximately 1
    total = sum(result.values())
    assert 0.99 <= total <= 1.01


def test_get_risk_metrics(mcp_tools):
    """Test risk metrics calculation"""
    result = mcp_tools.get_risk_metrics(portfolio_id=1)

    assert result is not None
    assert "var_95" in result
    assert "var_99" in result
    assert "cvar_95" in result
    assert "volatility" in result
    assert "beta" in result


def test_simulate_rebalancing(mcp_tools):
    """Test rebalancing simulation"""
    allocation_changes = {"AAPL": -10, "QBTS": 50}
    result = mcp_tools.simulate_rebalancing(
        portfolio_id=1,
        allocation_changes=allocation_changes
    )

    assert result is not None
    assert "current" in result
    assert "proposed" in result
    assert "changes" in result
    assert "allocation_changes" in result


def test_run_efficient_frontier(mcp_tools):
    """Test efficient frontier calculation"""
    result = mcp_tools.run_efficient_frontier(portfolio_id=1)

    assert result is not None
    assert "frontier" in result
    assert "current_portfolio" in result
    assert "max_sharpe_portfolio" in result
    assert "min_volatility_portfolio" in result
    assert len(result["frontier"]["returns"]) == len(result["frontier"]["volatilities"])


def test_run_monte_carlo(mcp_tools):
    """Test Monte Carlo simulation"""
    result = mcp_tools.run_monte_carlo(
        portfolio_id=1,
        scenarios=1000,
        time_horizon=252
    )

    assert result is not None
    assert result["scenarios"] == 1000
    assert result["time_horizon_days"] == 252
    assert "final_values" in result
    assert "percentiles" in result
    assert "probability_of_loss" in result


def test_run_cppi_simulation(mcp_tools):
    """Test CPPI simulation"""
    result = mcp_tools.run_cppi_simulation(
        portfolio_id=1,
        multiplier=3.0,
        floor=0.8
    )

    assert result is not None
    assert result["strategy"] == "CPPI"
    assert result["parameters"]["multiplier"] == 3.0
    assert result["parameters"]["floor"] == 0.8
    assert "performance" in result


def test_get_performance_comparison(mcp_tools):
    """Test performance comparison"""
    allocation_changes = {"AAPL": -10, "QBTS": 50}
    result = mcp_tools.get_performance_comparison(
        portfolio_id=1,
        allocation_changes=allocation_changes
    )

    assert result is not None
    assert "current" in result
    assert "proposed" in result
    assert "improvement_score" in result
    assert "risk_reward_tradeoff" in result
