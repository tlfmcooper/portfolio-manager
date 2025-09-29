"""
Portfolio Manager - A comprehensive Python package for portfolio management and analysis.

This package provides tools for:
- Portfolio construction and management
- Risk analysis and metrics calculation
- Performance analytics
- Portfolio optimization
- Data integration from various sources

Based on EDHEC Risk Kit and modern portfolio theory implementations.
"""

__version__ = "0.1.0"
__author__ = "Ali Kone"
__email__ = "ali.kone@example.com"

# Core imports
from .core.portfolio import Portfolio
from .core.asset import Asset

# Analytics imports
from .analytics.performance import PerformanceAnalytics
from .analytics.risk import RiskAnalytics
from .analytics.optimization import PortfolioOptimizer

# Data provider imports
from .data.providers import DataProvider, YFinanceProvider

# Legacy functions (from existing risk.py) - for backward compatibility
from .legacy import risk_functions

__all__ = [
    "Portfolio",
    "Asset", 
    "PerformanceAnalytics",
    "RiskAnalytics",
    "PortfolioOptimizer",
    "DataProvider",
    "YFinanceProvider",
    "risk_functions",
    "__version__",
]
