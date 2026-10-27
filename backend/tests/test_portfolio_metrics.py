"""Regression checks for risk metrics on a single modeled return series."""
import numpy as np
import pandas as pd
import pytest

from app.services.portfolio_analysis import AdvancedPortfolioAnalytics


def metrics(values):
    engine = AdvancedPortfolioAnalytics(1, None)
    return engine._compute_metrics_from_returns(pd.Series(values, dtype=float), {}, {}, 1000)


def test_sortino_measures_shortfall_over_all_observations():
    values = np.array([.02, -.01, .015, -.01] * 20)
    daily_rf = 1.042 ** (1 / 252) - 1
    annual_return = np.prod(1 + values) ** (252 / len(values)) - 1
    downside = np.sqrt(np.mean(np.minimum(values - daily_rf, 0) ** 2)) * np.sqrt(252)
    assert metrics(values)['sortino_ratio'] == pytest.approx((annual_return - .042) / downside)


def test_drawdown_includes_initial_capital_and_calmar_uses_same_return():
    result = metrics([-.1, .02, .01])
    assert result['max_drawdown'] == pytest.approx(-.1)
    assert result['calmar_ratio'] == pytest.approx(result['portfolio_return_annualized'] / .1)


def test_no_downside_returns_undefined_sortino_and_calmar_as_null():
    result = metrics([.01] * 60)
    assert result['sortino_ratio'] is None
    assert result['max_drawdown'] == 0
    assert result['calmar_ratio'] is None
