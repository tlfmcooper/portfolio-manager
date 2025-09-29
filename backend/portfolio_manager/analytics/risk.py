"""
Risk analytics module for portfolio risk assessment.
"""

from typing import Dict, Optional, List, Tuple
from datetime import date
import pandas as pd
import numpy as np
from scipy import stats
from scipy.optimize import minimize
import warnings

from ..core.portfolio import Portfolio


class RiskAnalytics:
    """
    Risk analytics for portfolios.
    
    Provides comprehensive risk analysis including correlation analysis,
    factor exposure, stress testing, and risk attribution.
    """
    
    def __init__(self, portfolio: Portfolio):
        """
        Initialize risk analytics.
        
        Args:
            portfolio: Portfolio object to analyze
        """
        self.portfolio = portfolio
        self._cache = {}
    
    def correlation_matrix(self, start_date: Optional[date] = None,
                          end_date: Optional[date] = None) -> pd.DataFrame:
        """
        Calculate correlation matrix of portfolio assets.
        
        Args:
            start_date: Start date for calculation
            end_date: End date for calculation
            
        Returns:
            Correlation matrix DataFrame
        """
        returns_data = {}
        
        for symbol, asset in self.portfolio.assets.items():
            returns = asset.get_returns(start_date, end_date)
            if not returns.empty:
                returns_data[symbol] = returns
        
        if not returns_data:
            return pd.DataFrame()
        
        returns_df = pd.DataFrame(returns_data)
        return returns_df.corr()
    
    def covariance_matrix(self, start_date: Optional[date] = None,
                         end_date: Optional[date] = None,
                         annualized: bool = True) -> pd.DataFrame:
        """
        Calculate covariance matrix of portfolio assets.
        
        Args:
            start_date: Start date for calculation
            end_date: End date for calculation
            annualized: Whether to annualize the covariance
            
        Returns:
            Covariance matrix DataFrame
        """
        returns_data = {}
        
        for symbol, asset in self.portfolio.assets.items():
            returns = asset.get_returns(start_date, end_date)
            if not returns.empty:
                returns_data[symbol] = returns
        
        if not returns_data:
            return pd.DataFrame()
        
        returns_df = pd.DataFrame(returns_data)
        cov_matrix = returns_df.cov()
        
        if annualized:
            cov_matrix *= 252  # Assuming daily returns
        
        return cov_matrix
    
    def portfolio_variance(self, start_date: Optional[date] = None,
                          end_date: Optional[date] = None) -> float:
        """
        Calculate portfolio variance using weights and covariance matrix.
        
        Args:
            start_date: Start date for calculation
            end_date: End date for calculation
            
        Returns:
            Portfolio variance
        """
        cov_matrix = self.covariance_matrix(start_date, end_date)
        
        if cov_matrix.empty:
            return 0.0
        
        # Get weights in same order as covariance matrix
        weights = []
        for symbol in cov_matrix.index:
            weights.append(self.portfolio.weights.get(symbol, 0.0))
        
        weights = np.array(weights)
        
        # Portfolio variance = w^T * Σ * w
        portfolio_var = np.dot(weights.T, np.dot(cov_matrix.values, weights))
        
        return float(portfolio_var)
    
    def portfolio_volatility(self, start_date: Optional[date] = None,
                           end_date: Optional[date] = None) -> float:
        """
        Calculate portfolio volatility (standard deviation).
        
        Args:
            start_date: Start date for calculation
            end_date: End date for calculation
            
        Returns:
            Portfolio volatility (annualized)
        """
        portfolio_var = self.portfolio_variance(start_date, end_date)
        return float(np.sqrt(portfolio_var))
    
    def risk_contribution(self, start_date: Optional[date] = None,
                         end_date: Optional[date] = None) -> Dict[str, float]:
        """
        Calculate risk contribution of each asset to total portfolio risk.
        
        Args:
            start_date: Start date for calculation
            end_date: End date for calculation
            
        Returns:
            Dictionary mapping asset symbols to risk contributions
        """
        cov_matrix = self.covariance_matrix(start_date, end_date)
        
        if cov_matrix.empty:
            return {}
        
        # Get weights in same order as covariance matrix
        weights = []
        symbols = list(cov_matrix.index)
        for symbol in symbols:
            weights.append(self.portfolio.weights.get(symbol, 0.0))
        
        weights = np.array(weights)
        portfolio_var = self.portfolio_variance(start_date, end_date)
        
        if portfolio_var == 0:
            return {symbol: 0.0 for symbol in symbols}
        
        # Risk contribution = (w_i * (Σ * w)_i) / σ_p^2
        cov_dot_weights = np.dot(cov_matrix.values, weights)
        risk_contributions = {}
        
        for i, symbol in enumerate(symbols):
            risk_contrib = (weights[i] * cov_dot_weights[i]) / portfolio_var
            risk_contributions[symbol] = float(risk_contrib)
        
        return risk_contributions
    
    def concentration_risk(self) -> Dict[str, float]:
        """
        Calculate concentration risk metrics.
        
        Returns:
            Dictionary with concentration risk measures
        """
        weights = list(self.portfolio.weights.values())
        
        if not weights:
            return {"herfindahl_index": 0.0, "effective_number_assets": 0.0, "max_weight": 0.0}
        
        weights = np.array(weights)
        
        # Herfindahl-Hirschman Index
        hhi = np.sum(weights ** 2)
        
        # Effective number of assets
        effective_n = 1 / hhi if hhi > 0 else 0
        
        # Maximum weight
        max_weight = np.max(weights)
        
        return {
            "herfindahl_index": float(hhi),
            "effective_number_assets": float(effective_n),
            "max_weight": float(max_weight),
            "num_assets": len(weights)
        }
    
    def stress_test(self, stress_scenarios: Dict[str, float],
                   start_date: Optional[date] = None,
                   end_date: Optional[date] = None) -> Dict[str, float]:
        """
        Perform stress testing on portfolio.
        
        Args:
            stress_scenarios: Dictionary mapping asset symbols to stress returns
            start_date: Start date for baseline calculation
            end_date: End date for baseline calculation
            
        Returns:
            Dictionary with stress test results
        """
        # Calculate baseline portfolio value (assume starting value of 1)
        baseline_value = 1.0
        
        # Calculate stressed portfolio value
        stressed_value = 0.0
        
        for symbol, weight in self.portfolio.weights.items():
            if symbol in stress_scenarios:
                # Apply stress scenario
                stressed_return = stress_scenarios[symbol]
                stressed_value += weight * (1 + stressed_return)
            else:
                # No stress, assume no change
                stressed_value += weight
        
        # Add cash position
        stressed_value += self.portfolio.cash
        
        stress_return = (stressed_value - baseline_value) / baseline_value
        
        return {
            "baseline_value": baseline_value,
            "stressed_value": stressed_value,
            "stress_return": stress_return,
            "value_change": stressed_value - baseline_value
        }
