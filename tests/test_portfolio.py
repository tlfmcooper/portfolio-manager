"""
Tests for Portfolio class.
"""

import pytest
import pandas as pd
from datetime import date

from portfolio_manager.core.portfolio import Portfolio
from portfolio_manager.core.asset import Asset, AssetType


def test_portfolio_creation():
    """Test basic portfolio creation."""
    portfolio = Portfolio(name="Test Portfolio")
    
    assert portfolio.name == "Test Portfolio"
    assert len(portfolio.assets) == 0
    assert len(portfolio.weights) == 0
    assert portfolio.cash == 0.0
    assert portfolio.base_currency == "USD"


def test_add_asset(sample_asset):
    """Test adding assets to portfolio."""
    portfolio = Portfolio(name="Test Portfolio")
    portfolio.add_asset("AAPL", sample_asset, 0.5)
    
    assert len(portfolio.assets) == 1
    assert "AAPL" in portfolio.assets
    assert portfolio.weights["AAPL"] == 0.5


def test_invalid_weight():
    """Test adding asset with invalid weight."""
    portfolio = Portfolio(name="Test Portfolio")
    asset = Asset(symbol="AAPL", name="Apple Inc.")
    
    with pytest.raises(ValueError):
        portfolio.add_asset("AAPL", asset, 1.5)  # Weight > 1


def test_portfolio_summary(sample_portfolio):
    """Test portfolio summary generation."""
    summary = sample_portfolio.summary()
    
    assert summary["name"] == "Test Portfolio"
    assert summary["num_assets"] == 1
    assert summary["total_weight"] == 0.7  # Updated to match our fixture
    assert "AAPL" in summary["assets"]


def test_get_portfolio_returns(sample_portfolio):
    """Test portfolio returns calculation."""
    returns = sample_portfolio.get_portfolio_returns()
    
    assert isinstance(returns, pd.Series)
    assert len(returns) > 0
    assert not returns.isna().all()


def test_rebalance(sample_portfolio, sample_asset):
    """Test portfolio rebalancing."""
    # Add another asset
    asset2 = Asset(symbol="GOOGL", name="Alphabet Inc.")
    sample_portfolio.assets["GOOGL"] = asset2
    
    # Rebalance
    new_weights = {"AAPL": 0.6, "GOOGL": 0.4}
    sample_portfolio.rebalance(new_weights)
    
    assert sample_portfolio.weights["AAPL"] == 0.6
    assert sample_portfolio.weights["GOOGL"] == 0.4


def test_remove_asset(sample_portfolio):
    """Test removing asset from portfolio."""
    sample_portfolio.remove_asset("AAPL")
    
    assert len(sample_portfolio.assets) == 0
    assert len(sample_portfolio.weights) == 0
