"""
Portfolio optimization module using modern portfolio theory.
"""

from typing import Dict, List, Optional, Tuple, Callable
from datetime import date
import pandas as pd
import numpy as np
from scipy.optimize import minimize
import warnings

from ..core.portfolio import Portfolio
from ..core.asset import Asset


class PortfolioOptimizer:
    """
    Portfolio optimization using Modern Portfolio Theory.
    
    Provides various optimization strategies including mean-variance optimization,
    risk parity, maximum diversification, and custom objective functions.
    """
    
    def __init__(self, assets: List[Asset], 
                 start_date: Optional[date] = None,
                 end_date: Optional[date] = None):
        """
        Initialize portfolio optimizer.
        
        Args:
            assets: List of Asset objects to optimize
            start_date: Start date for historical data
            end_date: End date for historical data
        """
        self.assets = assets
        self.start_date = start_date
        self.end_date = end_date
        self._returns_data = None
        self._expected_returns = None
        self._cov_matrix = None
    
    def _prepare_data(self) -> None:
        """Prepare returns data and calculate statistics."""
        if self._returns_data is not None:
            return
        
        returns_data = {}
        for asset in self.assets:
            returns = asset.get_returns(self.start_date, self.end_date)
            if not returns.empty:
                returns_data[asset.symbol] = returns
        
        if not returns_data:
            raise ValueError("No return data available for optimization")
        
        self._returns_data = pd.DataFrame(returns_data).dropna()
        self._expected_returns = self._returns_data.mean() * 252  # Annualized
        self._cov_matrix = self._returns_data.cov() * 252  # Annualized
    
    def mean_variance_optimization(self, 
                                 target_return: Optional[float] = None,
                                 risk_aversion: Optional[float] = None,
                                 weight_bounds: Tuple[float, float] = (0.0, 1.0),
                                 constraints: Optional[List] = None) -> Dict:
        """
        Perform mean-variance optimization.
        
        Args:
            target_return: Target portfolio return (if None, maximize Sharpe ratio)
            risk_aversion: Risk aversion parameter (alternative to target_return)
            weight_bounds: Min and max weight for each asset
            constraints: Additional constraints
            
        Returns:
            Dictionary with optimal weights and portfolio statistics
        """
        self._prepare_data()
        
        n_assets = len(self._expected_returns)
        
        # Bounds for each weight
        bounds = [weight_bounds] * n_assets
        
        # Constraint: weights sum to 1
        weight_sum_constraint = {
            'type': 'eq',
            'fun': lambda weights: np.sum(weights) - 1.0
        }
        
        all_constraints = [weight_sum_constraint]
        if constraints:
            all_constraints.extend(constraints)
        
        if target_return is not None:
            # Minimize variance for target return
            return_constraint = {
                'type': 'eq',
                'fun': lambda weights: np.dot(weights, self._expected_returns) - target_return
            }
            all_constraints.append(return_constraint)
            
            def objective(weights):
                return np.dot(weights.T, np.dot(self._cov_matrix, weights))
            
        elif risk_aversion is not None:
            # Maximize utility: return - (risk_aversion/2) * variance
            def objective(weights):
                portfolio_return = np.dot(weights, self._expected_returns)
                portfolio_var = np.dot(weights.T, np.dot(self._cov_matrix, weights))
                return -(portfolio_return - 0.5 * risk_aversion * portfolio_var)
        
        else:
            # Maximize Sharpe ratio (minimize negative Sharpe)
            def objective(weights):
                portfolio_return = np.dot(weights, self._expected_returns)
                portfolio_std = np.sqrt(np.dot(weights.T, np.dot(self._cov_matrix, weights)))
                if portfolio_std == 0:
                    return -float('inf')
                return -portfolio_return / portfolio_std
        
        # Initial guess: equal weights
        initial_guess = np.array([1.0 / n_assets] * n_assets)
        
        # Optimize
        result = minimize(
            objective,
            initial_guess,
            method='SLSQP',
            bounds=bounds,
            constraints=all_constraints,
            options={'ftol': 1e-9, 'disp': False}
        )
        
        if not result.success:
            warnings.warn(f"Optimization did not converge: {result.message}")
        
        optimal_weights = result.x
        
        # Calculate portfolio statistics
        portfolio_return = np.dot(optimal_weights, self._expected_returns)
        
        # Calculate portfolio variance step by step for clarity
        cov_times_weights = np.dot(self._cov_matrix, optimal_weights)
        portfolio_var = np.dot(optimal_weights.T, cov_times_weights)
        
        # Ensure variance is positive (should always be for valid covariance matrix)
        if portfolio_var < 0:
            warnings.warn(f"Negative portfolio variance calculated: {portfolio_var}")
            portfolio_var = abs(portfolio_var)
        elif portfolio_var == 0:
            warnings.warn("Zero portfolio variance calculated - this indicates a problem")
            portfolio_var = 1e-10
            
        portfolio_std = np.sqrt(portfolio_var)
        sharpe_ratio = portfolio_return / portfolio_std if portfolio_std > 0 else 0
        
        weights_dict = {
            asset.symbol: float(weight) 
            for asset, weight in zip(self.assets, optimal_weights)
        }
        
        return {
            'weights': weights_dict,
            'expected_return': float(portfolio_return),
            'expected_volatility': float(portfolio_std),  # Fixed key name
            'expected_variance': float(portfolio_var),
            'expected_sharpe': float(sharpe_ratio),  # Fixed key name
            'optimization_success': result.success,
            'optimization_message': result.message
        }
    
    def risk_parity_optimization(self, 
                               weight_bounds: Tuple[float, float] = (0.01, 1.0)) -> Dict:
        """
        Risk parity optimization - equal risk contribution from each asset.
        
        Args:
            weight_bounds: Min and max weight for each asset
            
        Returns:
            Dictionary with optimal weights and portfolio statistics
        """
        self._prepare_data()
        
        n_assets = len(self._expected_returns)
        bounds = [weight_bounds] * n_assets
        
        # Constraint: weights sum to 1
        constraints = [{
            'type': 'eq',
            'fun': lambda weights: np.sum(weights) - 1.0
        }]
        
        def risk_parity_objective(weights):
            """Minimize sum of squared differences in risk contributions."""
            portfolio_var = np.dot(weights.T, np.dot(self._cov_matrix, weights))
            
            if portfolio_var == 0:
                return 1e6
            
            # Calculate risk contributions
            marginal_contrib = np.dot(self._cov_matrix, weights)
            risk_contrib = weights * marginal_contrib / portfolio_var
            
            # Target is equal risk contribution (1/n for each asset)
            target_contrib = 1.0 / n_assets
            
            # Minimize sum of squared deviations from target
            return np.sum((risk_contrib - target_contrib) ** 2)
        
        # Initial guess: equal weights
        initial_guess = np.array([1.0 / n_assets] * n_assets)
        
        result = minimize(
            risk_parity_objective,
            initial_guess,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'ftol': 1e-9, 'disp': False}
        )
        
        if not result.success:
            warnings.warn(f"Risk parity optimization did not converge: {result.message}")
        
        optimal_weights = result.x
        
        # Calculate portfolio statistics
        portfolio_return = np.dot(optimal_weights, self._expected_returns)
        portfolio_var = np.dot(optimal_weights.T, np.dot(self._cov_matrix, optimal_weights))
        portfolio_std = np.sqrt(portfolio_var)
        
        # Calculate actual risk contributions
        marginal_contrib = np.dot(self._cov_matrix, optimal_weights)
        risk_contrib = optimal_weights * marginal_contrib / portfolio_var if portfolio_var > 0 else np.zeros(len(optimal_weights))
        
        weights_dict = {
            asset.symbol: float(weight) 
            for asset, weight in zip(self.assets, optimal_weights)
        }
        
        risk_contrib_dict = {
            asset.symbol: float(contrib) 
            for asset, contrib in zip(self.assets, risk_contrib)
        }
        
        return {
            'weights': weights_dict,
            'risk_contributions': risk_contrib_dict,
            'expected_return': float(portfolio_return),
            'expected_volatility': float(portfolio_std),  # Fixed key name
            'expected_variance': float(portfolio_var),    # Fixed key name
            'optimization_success': result.success,
            'optimization_message': result.message
        }
    
    def efficient_frontier(self, 
                          num_portfolios: int = 100,
                          weight_bounds: Tuple[float, float] = (0.0, 1.0)) -> pd.DataFrame:
        """
        Generate efficient frontier.
        
        Args:
            num_portfolios: Number of portfolios to generate
            weight_bounds: Min and max weight for each asset
            
        Returns:
            DataFrame with efficient frontier portfolios
        """
        self._prepare_data()
        
        min_ret = self._expected_returns.min()
        max_ret = self._expected_returns.max()
        
        target_returns = np.linspace(min_ret, max_ret, num_portfolios)
        
        frontier_portfolios = []
        
        for target_ret in target_returns:
            try:
                result = self.mean_variance_optimization(
                    target_return=target_ret,
                    weight_bounds=weight_bounds
                )
                
                if result['optimization_success']:
                    portfolio_data = {
                        'target_return': target_ret,
                        'expected_return': result['expected_return'],
                        'volatility': result['volatility'],
                        'sharpe_ratio': result['sharpe_ratio']
                    }
                    
                    # Add weights
                    for symbol, weight in result['weights'].items():
                        portfolio_data[f'weight_{symbol}'] = weight
                    
                    frontier_portfolios.append(portfolio_data)
                    
            except Exception as e:
                warnings.warn(f"Failed to optimize for return {target_ret}: {str(e)}")
                continue
        
        return pd.DataFrame(frontier_portfolios)
