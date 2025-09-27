"""
Advanced Features Demo for Portfolio Dashboard
This module demonstrates advanced analytics and features for portfolio management.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import json
from dataclasses import dataclass
from scipy import stats
import matplotlib.pyplot as plt
from io import BytesIO
import base64

@dataclass
class PortfolioPosition:
    """Represents a single portfolio position"""
    symbol: str
    name: str
    shares: float
    current_price: float
    cost_basis: float
    sector: str
    
    @property
    def market_value(self) -> float:
        return self.shares * self.current_price
    
    @property
    def unrealized_gain_loss(self) -> float:
        return (self.current_price - self.cost_basis) * self.shares
    
    @property
    def return_percentage(self) -> float:
        if self.cost_basis == 0:
            return 0
        return ((self.current_price - self.cost_basis) / self.cost_basis) * 100

class AdvancedPortfolioAnalytics:
    """Advanced analytics engine for portfolio management"""
    
    def __init__(self):
        self.risk_free_rate = 0.02  # 2% risk-free rate
        
    def calculate_portfolio_metrics(self, positions: List[PortfolioPosition], 
                                  price_history: Dict[str, List[float]]) -> Dict:
        """Calculate comprehensive portfolio metrics"""
        
        # Calculate portfolio weights
        total_value = sum(pos.market_value for pos in positions)
        weights = [pos.market_value / total_value for pos in positions]
        
        # Calculate returns for each position
        returns_data = self._calculate_returns(price_history)
        
        # Portfolio-level calculations
        portfolio_return = self._calculate_portfolio_return(weights, returns_data)
        portfolio_volatility = self._calculate_portfolio_volatility(weights, returns_data)
        sharpe_ratio = self._calculate_sharpe_ratio(portfolio_return, portfolio_volatility)
        
        # Risk metrics
        var_95 = self._calculate_var(returns_data, weights, confidence_level=0.95)
        max_drawdown = self._calculate_max_drawdown(price_history, weights)
        
        return {
            "portfolio_return_annualized": portfolio_return * 252,  # Daily to annual
            "portfolio_volatility_annualized": portfolio_volatility * np.sqrt(252),
            "sharpe_ratio": sharpe_ratio,
            "value_at_risk_95": var_95,
            "max_drawdown": max_drawdown,
            "total_portfolio_value": total_value,
            "number_of_positions": len(positions),
            "concentration_risk": max(weights)  # Largest position weight
        }
    def _calculate_returns(self, price_history: Dict[str, List[float]]) -> pd.DataFrame:
        """Calculate daily returns for all positions"""
        returns_dict = {}
        for symbol, prices in price_history.items():
            prices_array = np.array(prices)
            returns = np.diff(prices_array) / prices_array[:-1]
            returns_dict[symbol] = returns
        
        return pd.DataFrame(returns_dict)
    
    def _calculate_portfolio_return(self, weights: List[float], returns_data: pd.DataFrame) -> float:
        """Calculate weighted portfolio return"""
        avg_returns = returns_data.mean()
        portfolio_return = sum(w * r for w, r in zip(weights, avg_returns))
        return portfolio_return
    
    def _calculate_portfolio_volatility(self, weights: List[float], returns_data: pd.DataFrame) -> float:
        """Calculate portfolio volatility using covariance matrix"""
        cov_matrix = returns_data.cov()
        weights_array = np.array(weights)
        portfolio_variance = np.dot(weights_array.T, np.dot(cov_matrix, weights_array))
        return np.sqrt(portfolio_variance)
    
    def _calculate_sharpe_ratio(self, portfolio_return: float, portfolio_volatility: float) -> float:
        """Calculate Sharpe ratio"""
        if portfolio_volatility == 0:
            return 0
        return (portfolio_return - self.risk_free_rate / 252) / portfolio_volatility
    
    def _calculate_var(self, returns_data: pd.DataFrame, weights: List[float], 
                      confidence_level: float = 0.95) -> float:
        """Calculate Value at Risk using historical simulation"""
        portfolio_returns = returns_data.dot(weights)
        var_value = np.percentile(portfolio_returns, (1 - confidence_level) * 100)
        return abs(var_value)
    def _calculate_max_drawdown(self, price_history: Dict[str, List[float]], 
                               weights: List[float]) -> float:
        """Calculate maximum drawdown"""
        # Simulate portfolio value over time
        portfolio_values = []
        for i in range(len(list(price_history.values())[0])):
            portfolio_value = sum(
                weights[j] * list(price_history.values())[j][i] 
                for j in range(len(weights))
            )
            portfolio_values.append(portfolio_value)
        
        portfolio_values = np.array(portfolio_values)
        running_max = np.maximum.accumulate(portfolio_values)
        drawdowns = (portfolio_values - running_max) / running_max
        return abs(min(drawdowns))
    
    def optimize_portfolio(self, expected_returns: List[float], 
                          cov_matrix: np.ndarray, risk_tolerance: float = 0.5) -> Dict:
        """
        Simple portfolio optimization using mean-variance optimization
        Risk tolerance: 0 = minimum risk, 1 = maximum return
        """
        from scipy.optimize import minimize
        
        n_assets = len(expected_returns)
        
        def objective(weights):
            portfolio_return = np.dot(weights, expected_returns)
            portfolio_variance = np.dot(weights.T, np.dot(cov_matrix, weights))
            # Combine return and risk based on risk tolerance
            return -(risk_tolerance * portfolio_return - (1 - risk_tolerance) * portfolio_variance)
        
        constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
        bounds = tuple((0, 1) for _ in range(n_assets))
        initial_guess = np.array([1/n_assets] * n_assets)
        
        result = minimize(objective, initial_guess, method='SLSQP', 
                         bounds=bounds, constraints=constraints)
        
        if result.success:
            optimal_weights = result.x
            expected_portfolio_return = np.dot(optimal_weights, expected_returns)
            expected_portfolio_risk = np.sqrt(np.dot(optimal_weights.T, 
                                                   np.dot(cov_matrix, optimal_weights)))
            
            return {
                "optimal_weights": optimal_weights.tolist(),
                "expected_return": expected_portfolio_return,
                "expected_risk": expected_portfolio_risk,
                "optimization_success": True
            }
        else:
            return {"optimization_success": False, "error": result.message}
    def generate_correlation_matrix(self, returns_data: pd.DataFrame) -> Dict:
        """Generate correlation matrix for portfolio positions"""
        correlation_matrix = returns_data.corr()
        
        return {
            "correlation_matrix": correlation_matrix.to_dict(),
            "symbols": list(returns_data.columns),
            "highest_correlation": correlation_matrix.max().max(),
            "lowest_correlation": correlation_matrix.min().min()
        }
    
    def sector_analysis(self, positions: List[PortfolioPosition]) -> Dict:
        """Analyze portfolio by sector"""
        sector_data = {}
        total_value = sum(pos.market_value for pos in positions)
        
        for position in positions:
            if position.sector not in sector_data:
                sector_data[position.sector] = {
                    "value": 0,
                    "positions": 0,
                    "total_gain_loss": 0
                }
            
            sector_data[position.sector]["value"] += position.market_value
            sector_data[position.sector]["positions"] += 1
            sector_data[position.sector]["total_gain_loss"] += position.unrealized_gain_loss
        
        # Calculate percentages
        for sector in sector_data:
            sector_data[sector]["percentage"] = (
                sector_data[sector]["value"] / total_value * 100
            )
        
        return sector_data

# Demo function to showcase the analytics
def run_portfolio_demo():
    """Demonstrate the advanced portfolio analytics features with AAPL and NVDA"""
    
    # Create sample portfolio positions matching the actual database
    positions = [
        PortfolioPosition("AAPL", "Apple Inc.", 248, 255.46, 73.0, "Technology"),
        PortfolioPosition("NVDA", "NVIDIA Corporation", 110, 178.19, 125.0, "Technology"),
    ]
    
    # Generate sample price history (30 days)
    np.random.seed(42)  # For reproducible results
    price_history = {}
    for pos in positions:
        prices = [pos.current_price]
        for _ in range(29):  # 29 more days
            change = np.random.normal(0, 0.02)  # 2% daily volatility
            new_price = prices[-1] * (1 + change)
            prices.append(max(new_price, 0.01))  # Ensure positive prices
        price_history[pos.symbol] = prices
    
    # Initialize analytics engine
    analytics = AdvancedPortfolioAnalytics()
    
    # Calculate metrics
    metrics = analytics.calculate_portfolio_metrics(positions, price_history)
    sector_analysis = analytics.sector_analysis(positions)
    
    print("=== Portfolio Analytics Demo ===")
    print(f"Total Portfolio Value: ${metrics['total_portfolio_value']:,.2f}")
    print(f"Annualized Return: {metrics['portfolio_return_annualized']:.2%}")
    print(f"Annualized Volatility: {metrics['portfolio_volatility_annualized']:.2%}")
    print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.3f}")
    print(f"Value at Risk (95%): {metrics['value_at_risk_95']:.2%}")
    print(f"Maximum Drawdown: {metrics['max_drawdown']:.2%}")
    print(f"Concentration Risk: {metrics['concentration_risk']:.2%}")
    
    print("\n=== Sector Analysis ===")
    for sector, data in sector_analysis.items():
        print(f"{sector}: {data['percentage']:.1f}% (${data['value']:,.2f})")

if __name__ == "__main__":
    run_portfolio_demo()
