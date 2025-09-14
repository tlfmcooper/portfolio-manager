"""
Test configuration and fixtures.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import date, timedelta

from portfolio_manager.core.asset import Asset, AssetType
from portfolio_manager.core.portfolio import Portfolio


@pytest.fixture
def sample_price_data():
    """Create sample price data for testing."""
    dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='D')
    np.random.seed(42)
    
    # Generate realistic price data
    prices = []
    price = 100.0
    for _ in dates:
        change = np.random.normal(0, 0.02)  # 2% daily volatility
        price *= (1 + change)
        prices.append(price)
    
    data = pd.DataFrame({
        'Open': [p * (1 + np.random.normal(0, 0.001)) for p in prices],
        'High': [p * (1 + abs(np.random.normal(0, 0.005))) for p in prices], 
        'Low': [p * (1 - abs(np.random.normal(0, 0.005))) for p in prices],
        'Close': prices,
        'Volume': [np.random.randint(1000000, 5000000) for _ in prices]
    }, index=dates)
    
    return data


@pytest.fixture
def sample_asset(sample_price_data):
    """Create a sample asset for testing."""
    asset = Asset(
        symbol="AAPL",
        name="Apple Inc.",
        asset_type=AssetType.STOCK,
        currency="USD",
        exchange="NASDAQ"
    )
    asset.set_price_data(sample_price_data)
    return asset


@pytest.fixture
def sample_portfolio(sample_asset):
    """Create a sample portfolio for testing."""
    portfolio = Portfolio(name="Test Portfolio")
    portfolio.add_asset("AAPL", sample_asset, 0.7)  # Leave room for other assets
    return portfolio


@pytest.fixture  
def multiple_assets():
    """Create multiple assets for optimization testing."""
    # Create sample data for multiple assets
    dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='D')
    np.random.seed(42)
    
    assets = {}
    symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA']
    
    for symbol in symbols:
        # Generate correlated but different price series
        prices = []
        price = 100.0
        for i, _ in enumerate(dates):
            # Add some correlation between assets
            change = np.random.normal(0, 0.02) + 0.001 * np.sin(i / 10)
            price *= (1 + change)
            prices.append(price)
        
        data = pd.DataFrame({
            'Open': [p * (1 + np.random.normal(0, 0.001)) for p in prices],
            'High': [p * (1 + abs(np.random.normal(0, 0.005))) for p in prices], 
            'Low': [p * (1 - abs(np.random.normal(0, 0.005))) for p in prices],
            'Close': prices,
            'Volume': [np.random.randint(1000000, 5000000) for _ in prices]
        }, index=dates)
        
        asset = Asset(
            symbol=symbol,
            name=f"{symbol} Inc.",
            asset_type=AssetType.STOCK,
            currency="USD",
            exchange="NASDAQ"
        )
        asset.set_price_data(data)
        assets[symbol] = asset
    
    return assets
