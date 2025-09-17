"""
Portfolio analysis service for advanced financial calculations.
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import yfinance as yf
from scipy import stats

from app.models import Portfolio, Holding


class PortfolioAnalysisService:
    """Service for advanced portfolio analysis and risk metrics."""
    
    def __init__(self):
        self.risk_free_rate = 0.02  # 2% risk-free rate
    
    async def fetch_market_data(self, symbols: List[str], period: str = "2y") -> Dict[str, pd.DataFrame]:
        """Fetch market data for given symbols."""
        data = {}
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period=period)
                if not hist.empty:
                    data[symbol] = hist
            except Exception as e:
                print(f"Error fetching data for {symbol}: {e}")
        return data
    
    def calculate_returns(self, price_data: pd.DataFrame) -> pd.Series:
        """Calculate daily returns from price data."""
        return price_data['Close'].pct_change().dropna()
    
    def calculate_portfolio_metrics(self, returns_data: Dict[str, pd.Series], weights: Dict[str, float]) -> Dict[str, float]:
        """Calculate comprehensive portfolio metrics."""
        if not returns_data or not weights:
            return self._empty_metrics()
        
        # Align returns data
        returns_df = pd.DataFrame(returns_data).dropna()
        if returns_df.empty:
            return self._empty_metrics()
        
        # Calculate portfolio returns
        portfolio_weights = np.array([weights.get(symbol, 0) for symbol in returns_df.columns])
        portfolio_returns = (returns_df * portfolio_weights).sum(axis=1)
        
        # Annualized metrics
        annual_return = portfolio_returns.mean() * 252
        annual_volatility = portfolio_returns.std() * np.sqrt(252)
        sharpe_ratio = (annual_return - self.risk_free_rate) / annual_volatility if annual_volatility > 0 else 0
        
        # Sortino ratio (downside deviation)
        downside_returns = portfolio_returns[portfolio_returns < 0]
        semideviation = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else 0
        sortino_ratio = (annual_return - self.risk_free_rate) / semideviation if semideviation > 0 else 0
        
        # Maximum drawdown
        cumulative_returns = (1 + portfolio_returns).cumprod()
        running_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - running_max) / running_max
        max_drawdown = drawdown.min()
        
        # Calmar ratio
        calmar_ratio = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0
        
        # Higher moments
        skewness = stats.skew(portfolio_returns)
        kurtosis = stats.kurtosis(portfolio_returns)
        
        # Compound return
        compound_return = (1 + portfolio_returns).prod() ** (252 / len(portfolio_returns)) - 1
        
        return {
            'annual_return': float(annual_return),
            'annual_volatility': float(annual_volatility),
            'sharpe_ratio': float(sharpe_ratio),
            'sortino_ratio': float(sortino_ratio),
            'max_drawdown': float(max_drawdown),
            'calmar_ratio': float(calmar_ratio),
            'compound_return': float(compound_return),
            'skewness': float(skewness),
            'kurtosis': float(kurtosis),
            'semideviation': float(semideviation)
        }
    
    def calculate_risk_metrics(self, portfolio_returns: pd.Series) -> Dict[str, float]:
        """Calculate risk analytics."""
        if portfolio_returns.empty:
            return {
                'var_95': 0.0,
                'var_99': 0.0,
                'cvar': 0.0,
                'portfolio_volatility': 0.0,
                'semideviation': 0.0
            }
        
        # VaR calculations
        var_95 = np.percentile(portfolio_returns, 5)
        var_99 = np.percentile(portfolio_returns, 1)
        
        # CVaR (Expected Shortfall)
        cvar = portfolio_returns[portfolio_returns <= var_95].mean()
        
        # Portfolio volatility
        portfolio_volatility = portfolio_returns.std() * np.sqrt(252)
        
        # Semideviation
        downside_returns = portfolio_returns[portfolio_returns < 0]
        semideviation = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else 0
        
        return {
            'var_95': float(var_95),
            'var_99': float(var_99),
            'cvar': float(cvar if not pd.isna(cvar) else 0.0),
            'portfolio_volatility': float(portfolio_volatility),
            'semideviation': float(semideviation)
        }
    
    def _empty_metrics(self) -> Dict[str, float]:
        """Return empty metrics when data is insufficient."""
        return {
            'annual_return': 0.0,
            'annual_volatility': 0.0,
            'sharpe_ratio': 0.0,
            'sortino_ratio': 0.0,
            'max_drawdown': 0.0,
            'calmar_ratio': 0.0,
            'compound_return': 0.0,
            'skewness': 0.0,
            'kurtosis': 0.0,
            'semideviation': 0.0
        }
    
    async def generate_portfolio_analysis(self, portfolio: Portfolio) -> Dict[str, Any]:
        """Generate complete portfolio analysis."""
        if not portfolio.holdings:
            return {
                "portfolio_metrics": self._empty_metrics(),
                "risk_analytics": self._empty_metrics(),
                "asset_allocation": {},
                "message": "No holdings in portfolio"
            }
        
        # Extract symbols and weights
        symbols = []
        weights = {}
        total_value = 0.0
        
        for holding in portfolio.holdings:
            if holding.is_active and holding.asset:
                symbols.append(holding.asset.ticker)
                value = holding.quantity * (holding.current_price or holding.average_cost)
                weights[holding.asset.ticker] = value
                total_value += value
        
        if total_value == 0:
            return {
                "portfolio_metrics": self._empty_metrics(),
                "risk_analytics": self._empty_metrics(),
                "asset_allocation": {},
                "message": "Portfolio has no value"
            }
        
        # Normalize weights to percentages
        weights = {symbol: (value / total_value) for symbol, value in weights.items()}
        
        try:
            # Fetch market data
            market_data = await self.fetch_market_data(symbols)
            
            if not market_data:
                return {
                    "portfolio_metrics": self._empty_metrics(),
                    "risk_analytics": self._empty_metrics(),
                    "asset_allocation": weights,
                    "message": "Unable to fetch market data"
                }
            
            # Calculate returns
            returns_data = {}
            for symbol, data in market_data.items():
                if not data.empty:
                    returns_data[symbol] = self.calculate_returns(data)
            
            if not returns_data:
                return {
                    "portfolio_metrics": self._empty_metrics(),
                    "risk_analytics": self._empty_metrics(),
                    "asset_allocation": weights,
                    "message": "Unable to calculate returns"
                }
            
            # Calculate portfolio metrics
            portfolio_metrics = self.calculate_portfolio_metrics(returns_data, weights)
            
            # Calculate portfolio returns for risk analysis
            returns_df = pd.DataFrame(returns_data).dropna()
            if not returns_df.empty:
                portfolio_weights_array = np.array([weights.get(symbol, 0) for symbol in returns_df.columns])
                portfolio_returns = (returns_df * portfolio_weights_array).sum(axis=1)
                risk_metrics = self.calculate_risk_metrics(portfolio_returns)
            else:
                risk_metrics = self._empty_metrics()
            
            return {
                "portfolio_metrics": portfolio_metrics,
                "risk_analytics": risk_metrics,
                "asset_allocation": {k: v * 100 for k, v in weights.items()},  # Convert to percentages
                "total_value": total_value,
                "last_updated": datetime.utcnow().isoformat(),
            }
            
        except Exception as e:
            print(f"Error in portfolio analysis: {e}")
            return {
                "portfolio_metrics": self._empty_metrics(),
                "risk_analytics": self._empty_metrics(),
                "asset_allocation": weights,
                "error": str(e)
            }


# Create service instance
portfolio_analysis_service = PortfolioAnalysisService()
