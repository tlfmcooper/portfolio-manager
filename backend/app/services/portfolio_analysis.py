"""Portfolio Analysis Service - Wraps the portfolio_manager library"""
from typing import Dict, List, Any, Optional
from datetime import date, timedelta
from portfolio_manager import Portfolio, YFinanceProvider
from portfolio_manager.analytics.performance import PerformanceAnalytics
from portfolio_manager.analytics.risk import RiskAnalytics
from portfolio_manager.analytics.optimization import PortfolioOptimizer
import numpy as np


class PortfolioAnalysisService:
    """Service for portfolio analytics using the portfolio_manager library"""

    def __init__(self):
        self.provider = YFinanceProvider()

    def create_portfolio_from_holdings(
        self,
        holdings: List[Dict[str, Any]],
        start_date: Optional[date] = None
    ) -> Portfolio:
        """Create a Portfolio instance from holdings data"""
        if start_date is None:
            start_date = date.today() - timedelta(days=365)

        # Get tickers
        tickers = [h["ticker"] for h in holdings]

        # Fetch assets
        assets = self.provider.get_multiple_assets(tickers, start_date=start_date)

        # Create portfolio
        portfolio = Portfolio(name="Analysis Portfolio")

        # Add assets with weights
        for holding, asset in zip(holdings, assets):
            portfolio.add_asset(holding["ticker"], asset, holding["weight"])

        return portfolio

    def get_portfolio_metrics(self, holdings: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate comprehensive portfolio metrics"""
        portfolio = self.create_portfolio_from_holdings(holdings)
        perf = PerformanceAnalytics(portfolio)

        return {
            "total_return": perf.total_return(),
            "annualized_return": perf.annualized_return(),
            "volatility": perf.volatility(annualize=True),
            "sharpe_ratio": perf.sharpe_ratio(),
            "sortino_ratio": perf.sortino_ratio(),
            "max_drawdown": perf.max_drawdown()["max_drawdown"],
            "var_95": perf.value_at_risk(confidence_level=0.95),
            "cvar_95": perf.conditional_value_at_risk(confidence_level=0.95),
        }

    def get_risk_metrics(self, holdings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate risk metrics"""
        portfolio = self.create_portfolio_from_holdings(holdings)
        risk = RiskAnalytics(portfolio)
        perf = PerformanceAnalytics(portfolio)

        correlation_matrix = risk.correlation_matrix()

        return {
            "var_95": perf.value_at_risk(confidence_level=0.95),
            "var_99": perf.value_at_risk(confidence_level=0.99),
            "cvar_95": perf.conditional_value_at_risk(confidence_level=0.95),
            "cvar_99": perf.conditional_value_at_risk(confidence_level=0.99),
            "volatility": perf.volatility(annualize=True),
            "max_drawdown": perf.max_drawdown()["max_drawdown"],
            "correlation_matrix": correlation_matrix.to_dict(),
        }

    def simulate_rebalancing(
        self,
        current_holdings: List[Dict[str, Any]],
        allocation_changes: Dict[str, float]
    ) -> Dict[str, Any]:
        """Simulate portfolio rebalancing with allocation changes"""
        # Convert current holdings to dict
        current_weights = {h["ticker"]: h["weight"] for h in current_holdings}

        # Apply changes
        new_weights = current_weights.copy()
        for ticker, change in allocation_changes.items():
            if ticker in new_weights:
                new_weights[ticker] = new_weights[ticker] + (change / 100.0)
            else:
                new_weights[ticker] = change / 100.0

        # Normalize to sum to 1.0
        total = sum(new_weights.values())
        if total > 0:
            new_weights = {k: v / total for k, v in new_weights.items()}

        # Create new holdings list
        new_holdings = [{"ticker": k, "weight": v} for k, v in new_weights.items() if v > 0]

        # Get metrics for both portfolios
        current_metrics = self.get_portfolio_metrics(current_holdings)
        new_metrics = self.get_portfolio_metrics(new_holdings)

        # Calculate differences
        differences = {
            f"{key}_diff": new_metrics[key] - current_metrics[key]
            for key in current_metrics.keys()
        }

        return {
            "current": current_metrics,
            "proposed": new_metrics,
            "differences": differences,
            "new_allocations": new_weights,
        }

    def run_efficient_frontier(
        self,
        holdings: List[Dict[str, Any]],
        num_portfolios: int = 100
    ) -> Dict[str, Any]:
        """Generate efficient frontier"""
        portfolio = self.create_portfolio_from_holdings(holdings)

        # Get assets for optimization
        tickers = [h["ticker"] for h in holdings]
        start_date = date.today() - timedelta(days=365)
        assets = self.provider.get_multiple_assets(tickers, start_date=start_date)

        optimizer = PortfolioOptimizer(assets)

        # Get efficient frontier
        frontier = optimizer.efficient_frontier(num_portfolios=num_portfolios)

        # Get current portfolio position
        perf = PerformanceAnalytics(portfolio)
        current_return = perf.annualized_return()
        current_risk = perf.volatility(annualize=True)

        # Get optimal portfolios
        max_sharpe = optimizer.max_sharpe_ratio()
        min_volatility = optimizer.min_volatility()

        return {
            "frontier": frontier,
            "current_portfolio": {
                "return": current_return,
                "risk": current_risk,
                "sharpe": perf.sharpe_ratio(),
            },
            "max_sharpe_portfolio": max_sharpe,
            "min_volatility_portfolio": min_volatility,
        }

    def run_monte_carlo(
        self,
        holdings: List[Dict[str, Any]],
        scenarios: int = 1000,
        time_horizon: int = 252
    ) -> Dict[str, Any]:
        """Run Monte Carlo simulation"""
        portfolio = self.create_portfolio_from_holdings(holdings)
        perf = PerformanceAnalytics(portfolio)

        # Get portfolio metrics
        returns = portfolio.returns()
        mean_return = returns.mean()
        std_return = returns.std()

        # Run simulations
        simulations = []
        for _ in range(scenarios):
            # Generate random returns
            scenario_returns = np.random.normal(mean_return, std_return, time_horizon)
            cumulative_return = (1 + scenario_returns).prod() - 1
            simulations.append(cumulative_return)

        simulations = np.array(simulations)

        return {
            "scenarios": scenarios,
            "time_horizon_days": time_horizon,
            "mean_return": float(simulations.mean()),
            "median_return": float(np.median(simulations)),
            "std_return": float(simulations.std()),
            "percentile_5": float(np.percentile(simulations, 5)),
            "percentile_25": float(np.percentile(simulations, 25)),
            "percentile_75": float(np.percentile(simulations, 75)),
            "percentile_95": float(np.percentile(simulations, 95)),
            "worst_case": float(simulations.min()),
            "best_case": float(simulations.max()),
            "probability_positive": float((simulations > 0).sum() / len(simulations)),
        }

    def run_cppi_simulation(
        self,
        holdings: List[Dict[str, Any]],
        multiplier: float = 3.0,
        floor: float = 0.8,
        time_horizon: int = 252
    ) -> Dict[str, Any]:
        """Run CPPI (Constant Proportion Portfolio Insurance) simulation"""
        portfolio = self.create_portfolio_from_holdings(holdings)

        # Get portfolio returns
        returns = portfolio.returns()
        mean_return = returns.mean()
        std_return = returns.std()

        # Simulate CPPI strategy
        initial_value = 1.0
        floor_value = initial_value * floor
        cushion = initial_value - floor_value

        # Track portfolio value over time
        portfolio_values = [initial_value]
        current_value = initial_value

        for _ in range(time_horizon):
            cushion = current_value - floor_value
            exposure = min(cushion * multiplier, 1.0)  # Cap at 100% exposure

            # Simulate return
            period_return = np.random.normal(mean_return, std_return)

            # Calculate new value
            risky_return = period_return * exposure
            safe_return = 0.0001 * (1 - exposure)  # Assume small safe rate
            total_return = risky_return + safe_return

            current_value = current_value * (1 + total_return)
            portfolio_values.append(current_value)

        portfolio_values = np.array(portfolio_values)

        return {
            "multiplier": multiplier,
            "floor": floor,
            "time_horizon_days": time_horizon,
            "final_value": float(portfolio_values[-1]),
            "max_value": float(portfolio_values.max()),
            "min_value": float(portfolio_values.min()),
            "max_drawdown": float((portfolio_values.max() - portfolio_values.min()) / portfolio_values.max()),
            "floor_breached": bool(portfolio_values.min() < floor_value),
            "values": portfolio_values.tolist(),
        }
