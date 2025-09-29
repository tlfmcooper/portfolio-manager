"""
Performance analytics module for portfolio analysis.
"""

from typing import Dict, Optional, Union, List
from datetime import date, timedelta
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

from ..core.portfolio import Portfolio
from ..utils.cache import cached_analytics


class PerformanceAnalytics:
    """
    Performance analytics for portfolios and assets.
    
    This class provides comprehensive performance analysis including returns,
    risk-adjusted metrics, drawdowns, and benchmarking.
    """
    
    def __init__(self, portfolio: Portfolio):
        """
        Initialize performance analytics.
        
        Args:
            portfolio: Portfolio object to analyze
        """
        self.portfolio = portfolio
        self._cache = {}
    
    @cached_analytics('performance', ttl=1800)
    def total_return(self, start_date: Optional[date] = None, 
                    end_date: Optional[date] = None) -> float:
        """
        Calculate total return over period.
        
        Args:
            start_date: Start date for calculation
            end_date: End date for calculation
            
        Returns:
            Total return as decimal (0.1 = 10%)
        """
        returns = self.portfolio.get_portfolio_returns(start_date, end_date)
        if returns.empty:
            return 0.0
        
        return float((1 + returns).prod() - 1)
    
    def annualized_return(self, start_date: Optional[date] = None,
                         end_date: Optional[date] = None) -> float:
        """
        Calculate annualized return.
        
        Args:
            start_date: Start date for calculation  
            end_date: End date for calculation
            
        Returns:
            Annualized return as decimal
        """
        returns = self.portfolio.get_portfolio_returns(start_date, end_date)
        if returns.empty:
            return 0.0
        
        total_ret = self.total_return(start_date, end_date)
        days = (returns.index[-1] - returns.index[0]).days
        years = days / 365.25
        
        if years <= 0:
            return 0.0
        
        return float((1 + total_ret) ** (1 / years) - 1)
    
    def volatility(self, start_date: Optional[date] = None,
                  end_date: Optional[date] = None,
                  annualized: bool = True) -> float:
        """
        Calculate portfolio volatility.
        
        Args:
            start_date: Start date for calculation
            end_date: End date for calculation
            annualized: Whether to annualize the volatility
            
        Returns:
            Portfolio volatility
        """
        returns = self.portfolio.get_portfolio_returns(start_date, end_date)
        if returns.empty:
            return 0.0
        
        vol = float(returns.std())
        
        if annualized:
            # Assume daily returns, annualize with sqrt(252)
            vol *= np.sqrt(252)
        
        return vol
    
    def sharpe_ratio(self, risk_free_rate: float = 0.02,
                    start_date: Optional[date] = None,
                    end_date: Optional[date] = None) -> float:
        """
        Calculate Sharpe ratio.
        
        Args:
            risk_free_rate: Annual risk-free rate
            start_date: Start date for calculation
            end_date: End date for calculation
            
        Returns:
            Sharpe ratio
        """
        annual_return = self.annualized_return(start_date, end_date)
        vol = self.volatility(start_date, end_date, annualized=True)
        
        if vol == 0:
            return 0.0
        
        return (annual_return - risk_free_rate) / vol
    
    def sortino_ratio(self, risk_free_rate: float = 0.02,
                     start_date: Optional[date] = None,
                     end_date: Optional[date] = None) -> float:
        """
        Calculate Sortino ratio (risk-adjusted return using downside deviation).
        
        Args:
            risk_free_rate: Annual risk-free rate
            start_date: Start date for calculation
            end_date: End date for calculation
            
        Returns:
            Sortino ratio
        """
        returns = self.portfolio.get_portfolio_returns(start_date, end_date)
        if returns.empty:
            return 0.0
        
        annual_return = self.annualized_return(start_date, end_date)
        daily_rf = (1 + risk_free_rate) ** (1/252) - 1
        
        # Calculate downside deviation
        downside_returns = returns[returns < daily_rf]
        if len(downside_returns) == 0:
            return float('inf') if annual_return > risk_free_rate else 0.0
        
        downside_std = downside_returns.std() * np.sqrt(252)
        
        return (annual_return - risk_free_rate) / downside_std
    
    def max_drawdown(self, start_date: Optional[date] = None,
                    end_date: Optional[date] = None) -> Dict[str, Union[float, date]]:
        """
        Calculate maximum drawdown and related statistics.
        
        Args:
            start_date: Start date for calculation
            end_date: End date for calculation
            
        Returns:
            Dictionary with max drawdown, start date, end date, and recovery date
        """
        returns = self.portfolio.get_portfolio_returns(start_date, end_date)
        if returns.empty:
            return {"max_drawdown": 0.0, "start_date": None, "end_date": None, "recovery_date": None}
        
        # Calculate cumulative returns
        cum_returns = (1 + returns).cumprod()
        running_max = cum_returns.expanding().max()
        drawdown = (cum_returns - running_max) / running_max
        
        max_dd = drawdown.min()
        max_dd_date = drawdown.idxmin()
        
        # Find start of max drawdown period
        max_dd_start = running_max[running_max.index <= max_dd_date].idxmax()
        
        # Find recovery date (when drawdown returns to 0 after max DD)
        recovery_date = None
        post_dd = drawdown[drawdown.index > max_dd_date]
        recovery_idx = post_dd[post_dd >= -1e-6].first_valid_index()
        if recovery_idx is not None:
            recovery_date = recovery_idx.date()
        
        return {
            "max_drawdown": float(max_dd),
            "start_date": max_dd_start.date(),
            "end_date": max_dd_date.date(),
            "recovery_date": recovery_date
        }
    
    def calmar_ratio(self, start_date: Optional[date] = None,
                    end_date: Optional[date] = None) -> float:
        """
        Calculate Calmar ratio (annual return / max drawdown).
        
        Args:
            start_date: Start date for calculation
            end_date: End date for calculation
            
        Returns:
            Calmar ratio
        """
        annual_return = self.annualized_return(start_date, end_date)
        max_dd = abs(self.max_drawdown(start_date, end_date)["max_drawdown"])
        
        if max_dd == 0:
            return float('inf') if annual_return > 0 else 0.0
        
        return annual_return / max_dd
    
    def value_at_risk(self, confidence_level: float = 0.05,
                     start_date: Optional[date] = None,
                     end_date: Optional[date] = None) -> float:
        """
        Calculate Value at Risk (VaR).
        
        Args:
            confidence_level: Confidence level (0.05 = 5%)
            start_date: Start date for calculation
            end_date: End date for calculation
            
        Returns:
            VaR as decimal (negative value)
        """
        returns = self.portfolio.get_portfolio_returns(start_date, end_date)
        if returns.empty:
            return 0.0
        
        return float(np.percentile(returns, confidence_level * 100))
    
    def conditional_var(self, confidence_level: float = 0.05,
                       start_date: Optional[date] = None,
                       end_date: Optional[date] = None) -> float:
        """
        Calculate Conditional Value at Risk (Expected Shortfall).
        
        Args:
            confidence_level: Confidence level (0.05 = 5%)
            start_date: Start date for calculation
            end_date: End date for calculation
            
        Returns:
            CVaR as decimal (negative value)
        """
        returns = self.portfolio.get_portfolio_returns(start_date, end_date)
        if returns.empty:
            return 0.0
        
        var = self.value_at_risk(confidence_level, start_date, end_date)
        tail_returns = returns[returns <= var]
        
        if tail_returns.empty:
            return var
        
        return float(tail_returns.mean())
    
    def performance_summary(self, start_date: Optional[date] = None,
                           end_date: Optional[date] = None,
                           risk_free_rate: float = 0.02) -> Dict:
        """
        Generate comprehensive performance summary.
        
        Args:
            start_date: Start date for analysis
            end_date: End date for analysis
            risk_free_rate: Annual risk-free rate
            
        Returns:
            Dictionary with performance metrics
        """
        returns = self.portfolio.get_portfolio_returns(start_date, end_date)
        
        if returns.empty:
            return {"error": "No return data available"}
        
        max_dd_info = self.max_drawdown(start_date, end_date)
        
        summary = {
            "period": {
                "start_date": start_date or returns.index[0].date(),
                "end_date": end_date or returns.index[-1].date(),
                "num_observations": len(returns)
            },
            "returns": {
                "total_return": self.total_return(start_date, end_date),
                "annualized_return": self.annualized_return(start_date, end_date),
                "volatility": self.volatility(start_date, end_date),
                "best_day": float(returns.max()),
                "worst_day": float(returns.min()),
                "positive_days": int((returns > 0).sum()),
                "negative_days": int((returns < 0).sum())
            },
            "risk_metrics": {
                "sharpe_ratio": self.sharpe_ratio(risk_free_rate, start_date, end_date),
                "sortino_ratio": self.sortino_ratio(risk_free_rate, start_date, end_date),
                "calmar_ratio": self.calmar_ratio(start_date, end_date),
                "max_drawdown": max_dd_info["max_drawdown"],
                "max_drawdown_start": max_dd_info["start_date"],
                "max_drawdown_end": max_dd_info["end_date"],
                "recovery_date": max_dd_info["recovery_date"],
                "var_5pct": self.value_at_risk(0.05, start_date, end_date),
                "cvar_5pct": self.conditional_var(0.05, start_date, end_date)
            }
        }
        
        return summary
