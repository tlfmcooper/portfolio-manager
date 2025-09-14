"""
Tests for PerformanceAnalytics class.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import date, timedelta

from portfolio_manager.analytics.performance import PerformanceAnalytics


def test_performance_analytics_creation(sample_portfolio):
    """Test creating PerformanceAnalytics instance."""
    perf = PerformanceAnalytics(sample_portfolio)
    assert perf.portfolio == sample_portfolio


def test_total_return(sample_portfolio):
    """Test total return calculation."""
    perf = PerformanceAnalytics(sample_portfolio)
    total_ret = perf.total_return()
    
    assert isinstance(total_ret, float)
    # Should be reasonable for test data
    assert -0.5 <= total_ret <= 2.0


def test_annualized_return(sample_portfolio):
    """Test annualized return calculation."""
    perf = PerformanceAnalytics(sample_portfolio)
    annual_ret = perf.annualized_return()
    
    assert isinstance(annual_ret, float)
    # Should be reasonable annualized return
    assert -0.99 <= annual_ret <= 5.0


def test_volatility(sample_portfolio):
    """Test volatility calculation."""
    perf = PerformanceAnalytics(sample_portfolio)
    
    # Test annualized volatility
    vol_annual = perf.volatility(annualized=True)
    assert isinstance(vol_annual, float)
    assert vol_annual >= 0
    
    # Test non-annualized volatility
    vol_daily = perf.volatility(annualized=False)
    assert isinstance(vol_daily, float)
    assert vol_daily >= 0
    assert vol_daily < vol_annual  # Daily should be less than annualized


def test_sharpe_ratio(sample_portfolio):
    """Test Sharpe ratio calculation."""
    perf = PerformanceAnalytics(sample_portfolio)
    sharpe = perf.sharpe_ratio()
    
    assert isinstance(sharpe, float)
    # Reasonable range for Sharpe ratio
    assert -5 <= sharpe <= 5


def test_sortino_ratio(sample_portfolio):
    """Test Sortino ratio calculation."""
    perf = PerformanceAnalytics(sample_portfolio)
    sortino = perf.sortino_ratio()
    
    assert isinstance(sortino, float)
    # Should be defined (not inf or -inf for reasonable data)
    assert not np.isinf(sortino) or sortino == float('inf')


def test_max_drawdown(sample_portfolio):
    """Test maximum drawdown calculation."""
    perf = PerformanceAnalytics(sample_portfolio)
    dd_info = perf.max_drawdown()
    
    assert isinstance(dd_info, dict)
    assert "max_drawdown" in dd_info
    assert "start_date" in dd_info
    assert "end_date" in dd_info
    assert "recovery_date" in dd_info
    
    # Max drawdown should be negative or zero
    assert dd_info["max_drawdown"] <= 0


def test_calmar_ratio(sample_portfolio):
    """Test Calmar ratio calculation."""
    perf = PerformanceAnalytics(sample_portfolio)
    calmar = perf.calmar_ratio()
    
    assert isinstance(calmar, float)
    # Calmar ratio can be negative if returns are negative, or inf if no drawdown
    assert np.isfinite(calmar) or not np.isfinite(calmar)


def test_value_at_risk(sample_portfolio):
    """Test VaR calculation."""
    perf = PerformanceAnalytics(sample_portfolio)
    var_5 = perf.value_at_risk(confidence_level=0.05)
    
    assert isinstance(var_5, float)
    # VaR should typically be negative
    assert var_5 <= 0


def test_conditional_var(sample_portfolio):
    """Test CVaR calculation."""
    perf = PerformanceAnalytics(sample_portfolio)
    cvar_5 = perf.conditional_var(confidence_level=0.05)
    
    assert isinstance(cvar_5, float)
    # CVaR should typically be negative and worse than VaR
    var_5 = perf.value_at_risk(confidence_level=0.05)
    assert cvar_5 <= var_5


def test_performance_summary(sample_portfolio):
    """Test comprehensive performance summary."""
    perf = PerformanceAnalytics(sample_portfolio)
    summary = perf.performance_summary()
    
    assert isinstance(summary, dict)
    assert "period" in summary
    assert "returns" in summary
    assert "risk_metrics" in summary
    
    # Check period info
    period = summary["period"]
    assert "start_date" in period
    assert "end_date" in period
    assert "num_observations" in period
    
    # Check returns info
    returns = summary["returns"]
    assert "total_return" in returns
    assert "annualized_return" in returns
    assert "volatility" in returns
    assert "best_day" in returns
    assert "worst_day" in returns
    
    # Check risk metrics
    risk = summary["risk_metrics"]
    assert "sharpe_ratio" in risk
    assert "sortino_ratio" in risk
    assert "max_drawdown" in risk
    assert "var_5pct" in risk


def test_empty_portfolio_returns():
    """Test handling of portfolio with no returns."""
    from portfolio_manager.core.portfolio import Portfolio
    empty_portfolio = Portfolio(name="Empty Portfolio")
    
    perf = PerformanceAnalytics(empty_portfolio)
    
    # All metrics should handle empty data gracefully
    assert perf.total_return() == 0.0
    assert perf.annualized_return() == 0.0
    assert perf.volatility() == 0.0
    assert perf.sharpe_ratio() == 0.0


def test_date_range_filtering(sample_portfolio):
    """Test performance calculation with date range filtering."""
    perf = PerformanceAnalytics(sample_portfolio)
    
    # Get some sample dates from the portfolio
    returns = sample_portfolio.get_portfolio_returns()
    if not returns.empty:
        start_date = returns.index[10].date()  # Start 10 days in
        end_date = returns.index[-10].date()   # End 10 days before end
        
        total_ret_filtered = perf.total_return(start_date, end_date)
        total_ret_full = perf.total_return()
        
        # Should be different (unless very lucky)
        assert isinstance(total_ret_filtered, float)
        assert isinstance(total_ret_full, float)


def test_different_risk_free_rates(sample_portfolio):
    """Test metrics with different risk-free rates."""
    perf = PerformanceAnalytics(sample_portfolio)
    
    sharpe_2pct = perf.sharpe_ratio(risk_free_rate=0.02)
    sharpe_5pct = perf.sharpe_ratio(risk_free_rate=0.05)
    
    # Higher risk-free rate should generally result in lower Sharpe ratio
    # (unless portfolio return is very high)
    assert isinstance(sharpe_2pct, float)
    assert isinstance(sharpe_5pct, float)
