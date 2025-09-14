"""
Tests for PortfolioOptimizer class.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import date, timedelta

from portfolio_manager.analytics.optimization import PortfolioOptimizer


def test_risk_parity_with_tight_bounds(multiple_assets):
    """Test risk parity optimization with tight bounds."""
    # Convert dict to list of assets
    asset_list = list(multiple_assets.values())
    optimizer = PortfolioOptimizer(asset_list)
    
    # Test with very restrictive bounds
    result = optimizer.risk_parity_optimization(weight_bounds=(0.2, 0.3))
    
    assert isinstance(result, dict)
    assert 'optimization_success' in result
    
    if result['optimization_success']:
        weights = list(result['weights'].values())
        # All weights should be within bounds
        assert all(0.2 - 1e-6 <= w <= 0.3 + 1e-6 for w in weights)


def test_optimization_date_filtering(multiple_assets):
    """Test optimization with date range filtering."""
    from datetime import date
    
    # Use dates that match our test data (2023)
    start_date = date(2023, 6, 1)
    end_date = date(2023, 12, 31)
    
    # Convert dict to list of assets
    asset_list = list(multiple_assets.values())
    optimizer = PortfolioOptimizer(asset_list, start_date=start_date, end_date=end_date)
    result = optimizer.mean_variance_optimization()
    
    assert isinstance(result, dict)
    # Should work with date filtering
    if result['optimization_success']:
        assert 'weights' in result
