"""
Tests for Asset class.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import date

from portfolio_manager.core.asset import Asset, AssetType


def test_asset_creation():
    """Test basic asset creation."""
    asset = Asset(
        symbol="AAPL",
        name="Apple Inc.",
        asset_type=AssetType.STOCK,
        currency="USD",
        exchange="NASDAQ"
    )
    
    assert asset.symbol == "AAPL"
    assert asset.name == "Apple Inc."
    assert asset.asset_type == AssetType.STOCK
    assert asset.currency == "USD"
    assert asset.exchange == "NASDAQ"


def test_symbol_validation():
    """Test symbol validation."""
    # Test empty symbol
    with pytest.raises(ValueError):
        Asset(symbol="", name="Test")
    
    # Test symbol normalization
    asset = Asset(symbol="  aapl  ", name="Apple Inc.")
    assert asset.symbol == "AAPL"


def test_set_price_data(sample_asset, sample_price_data):
    """Test setting price data."""
    assert sample_asset.price_data is not None
    assert len(sample_asset.price_data) > 0
    assert "Close" in sample_asset.price_data.columns


def test_get_current_price(sample_asset):
    """Test getting current price."""
    price = sample_asset.get_current_price()
    assert price is not None
    assert isinstance(price, float)
    assert price > 0


def test_get_returns(sample_asset):
    """Test returns calculation."""
    returns = sample_asset.get_returns()
    
    assert isinstance(returns, pd.Series)
    assert len(returns) > 0
    assert not returns.isna().all()


def test_get_volatility(sample_asset):
    """Test volatility calculation."""
    vol = sample_asset.get_volatility()
    
    assert isinstance(vol, float)
    assert vol >= 0


def test_get_sharpe_ratio(sample_asset):
    """Test Sharpe ratio calculation."""
    sharpe = sample_asset.get_sharpe_ratio()
    
    assert isinstance(sharpe, float)


def test_asset_summary(sample_asset):
    """Test asset summary generation."""
    summary = sample_asset.summary()
    
    assert summary["symbol"] == "AAPL"
    assert summary["name"] == "Apple Inc."
    assert summary["has_price_data"] is True
    assert "current_price" in summary
    assert "volatility" in summary


def test_invalid_price_data():
    """Test setting invalid price data."""
    asset = Asset(symbol="TEST", name="Test Asset")
    
    # Missing required column
    invalid_data = pd.DataFrame({
        "Open": [100, 101],
        "High": [102, 103]
        # Missing Close column
    })
    
    with pytest.raises(ValueError):
        asset.set_price_data(invalid_data)
