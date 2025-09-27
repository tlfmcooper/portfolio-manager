"""
Portfolio analysis service.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.models.portfolio import Portfolio
from app.models.holding import Holding
from app.models.asset import Asset


class AdvancedPortfolioAnalytics:
    """Advanced analytics engine for portfolio management"""

    def __init__(self, portfolio_id: int, db: AsyncSession):
        self.portfolio_id = portfolio_id
        self.db = db
        self.risk_free_rate = 0.02  # 2% risk-free rate

    async def get_portfolio_data(self) -> Tuple[List[Holding], Dict[str, List[float]]]:
        """Get portfolio holdings and price history from the database."""
        # Get holdings
        result = await self.db.execute(
            select(Holding)
            .where(Holding.portfolio_id == self.portfolio_id)
            .options(selectinload(Holding.asset))
        )
        holdings = result.scalars().all()

        # Get price history (dummy data for now)
        price_history = {}
        for holding in holdings:
            prices = [holding.current_price]
            for _ in range(29):  # 29 more days
                change = np.random.normal(0, 0.02)  # 2% daily volatility
                new_price = prices[-1] * (1 + change)
                prices.append(max(new_price, 0.01))  # Ensure positive prices
            price_history[holding.asset.ticker] = prices

        return holdings, price_history

    async def calculate_portfolio_metrics(self) -> Dict:
        """Calculate comprehensive portfolio metrics"""
        holdings, price_history = await self.get_portfolio_data()

        if not holdings:
            return {}

        # Calculate portfolio weights
        total_value = sum(h.quantity * h.current_price for h in holdings)
        weights = [(h.quantity * h.current_price) / total_value for h in holdings]

        # Calculate returns for each position
        returns_data = self._calculate_returns(price_history)

        # Portfolio-level calculations
        portfolio_return = self._calculate_portfolio_return(weights, returns_data)
        portfolio_volatility = self._calculate_portfolio_volatility(weights, returns_data)
        sharpe_ratio = self._calculate_sharpe_ratio(portfolio_return, portfolio_volatility)
        sortino_ratio = self._calculate_sortino_ratio(portfolio_return, returns_data, weights)

        # Risk metrics
        var_95 = self._calculate_var(returns_data, weights, confidence_level=0.95)
        var_99 = self._calculate_var_99(returns_data, weights)
        cvar = self._calculate_cvar(returns_data, weights, confidence_level=0.95)
        semideviation = self._calculate_semideviation(returns_data, weights)
        max_drawdown = self._calculate_max_drawdown(price_history, weights)
        calmar_ratio = self._calculate_calmar_ratio(portfolio_return, max_drawdown)

        # Individual asset performance
        individual_performance = {}
        for holding in holdings:
            ticker = holding.asset.ticker
            if ticker in returns_data.columns:
                asset_returns = returns_data[ticker]
                individual_performance[ticker] = {
                    "return": asset_returns.mean() * 252,  # Annualized
                    "volatility": asset_returns.std() * np.sqrt(252),  # Annualized
                }

        return {
            "portfolio_return_annualized": portfolio_return * 252,  # Daily to annual
            "portfolio_volatility_annualized": portfolio_volatility * np.sqrt(252),
            "sharpe_ratio": sharpe_ratio,
            "sortino_ratio": sortino_ratio,
            "value_at_risk_95": var_95,
            "value_at_risk_99": var_99,
            "cvar": cvar,
            "semideviation": semideviation,
            "max_drawdown": max_drawdown,
            "calmar_ratio": calmar_ratio,
            "total_portfolio_value": total_value,
            "number_of_positions": len(holdings),
            "concentration_risk": max(weights),
            "individual_performance": individual_performance,
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

    def _calculate_sortino_ratio(self, portfolio_return: float, returns_data: pd.DataFrame, weights: List[float]) -> float:
        """Calculate Sortino ratio"""
        portfolio_returns = returns_data.dot(weights)
        downside_returns = portfolio_returns[portfolio_returns < 0]
        if downside_returns.empty:
            return 0
        downside_deviation = np.std(downside_returns)
        if downside_deviation == 0:
            return 0
        return (portfolio_return - self.risk_free_rate / 252) / downside_deviation

    def _calculate_calmar_ratio(self, portfolio_return: float, max_drawdown: float) -> float:
        """Calculate Calmar ratio"""
        if max_drawdown == 0:
            return 0
        return portfolio_return / max_drawdown

    def _calculate_var(self, returns_data: pd.DataFrame, weights: List[float], 
                      confidence_level: float = 0.95) -> float:
        """Calculate Value at Risk using historical simulation"""
        portfolio_returns = returns_data.dot(weights)
        var_value = np.percentile(portfolio_returns, (1 - confidence_level) * 100)
        return abs(var_value)

    def _calculate_var_99(self, returns_data: pd.DataFrame, weights: List[float]) -> float:
        """Calculate Value at Risk (99%) using historical simulation"""
        portfolio_returns = returns_data.dot(weights)
        var_value = np.percentile(portfolio_returns, 1)
        return abs(var_value)

    def _calculate_cvar(self, returns_data: pd.DataFrame, weights: List[float], 
                       confidence_level: float = 0.95) -> float:
        """Calculate Conditional Value at Risk (CVaR) using historical simulation"""
        portfolio_returns = returns_data.dot(weights)
        var_95 = np.percentile(portfolio_returns, (1 - confidence_level) * 100)
        cvar_value = portfolio_returns[portfolio_returns <= var_95].mean()
        return abs(cvar_value)

    def _calculate_semideviation(self, returns_data: pd.DataFrame, weights: List[float]) -> float:
        """Calculate semideviation (downside volatility)"""
        portfolio_returns = returns_data.dot(weights)
        downside_returns = portfolio_returns[portfolio_returns < 0]
        if downside_returns.empty:
            return 0
        return np.std(downside_returns)

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

    async def generate_efficient_frontier(self) -> Dict:
        """Generate the efficient frontier for the portfolio."""
        holdings, price_history = await self.get_portfolio_data()
        returns_data = self._calculate_returns(price_history)
        expected_returns = returns_data.mean()
        cov_matrix = returns_data.cov()

        frontier_points = []
        for risk_tolerance in np.linspace(0, 1, 20):
            optimization_result = self.optimize_portfolio(
                expected_returns,
                cov_matrix,
                risk_tolerance=risk_tolerance
            )
            if optimization_result["optimization_success"]:
                frontier_points.append({
                    "risk": optimization_result["expected_risk"],
                    "return": optimization_result["expected_return"],
                })

        # Get special portfolios
        current_weights = [(h.quantity * h.current_price) / sum(h.quantity * h.current_price for h in holdings) for h in holdings]
        current_return = self._calculate_portfolio_return(current_weights, returns_data)
        current_risk = self._calculate_portfolio_volatility(current_weights, returns_data)

        msr_portfolio = self.optimize_portfolio(expected_returns, cov_matrix, risk_tolerance=1.0)
        gmv_portfolio = self.optimize_portfolio(expected_returns, cov_matrix, risk_tolerance=0.0)

        special_portfolios = {
            "current": {"name": "Current Portfolio", "risk": current_risk, "return": current_return},
            "msr": {"name": "Max Sharpe Ratio", "risk": msr_portfolio["expected_risk"], "return": msr_portfolio["expected_return"]},
            "gmv": {"name": "Global Minimum Volatility", "risk": gmv_portfolio["expected_risk"], "return": gmv_portfolio["expected_return"]},
        }

        return {
            "frontier_points": frontier_points,
            "special_portfolios": special_portfolios,
        }

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

    async def run_monte_carlo_simulation(self, scenarios: int = 1000, time_horizon: int = 252) -> Dict:
        """Run a Monte Carlo simulation for the portfolio."""
        holdings, price_history = await self.get_portfolio_data()
        returns_data = self._calculate_returns(price_history)
        
        # Get portfolio statistics
        total_value = sum(h.quantity * h.current_price for h in holdings)
        weights = [(h.quantity * h.current_price) / total_value for h in holdings]
        portfolio_return = self._calculate_portfolio_return(weights, returns_data)
        portfolio_volatility = self._calculate_portfolio_volatility(weights, returns_data)

        # Run simulation
        final_values = []
        simulation_paths = []
        for _ in range(scenarios):
            path = [total_value]
            for _ in range(time_horizon):
                daily_return = np.random.normal(portfolio_return, portfolio_volatility)
                path.append(path[-1] * (1 + daily_return))
            final_values.append(path[-1])
            simulation_paths.append(path)

        # Get statistics from simulation
        final_mean = np.mean(final_values)
        final_std = np.std(final_values)
        percentile_5 = np.percentile(final_values, 5)
        percentile_95 = np.percentile(final_values, 95)
        success_probability = np.mean([1 if fv > total_value else 0 for fv in final_values])

        # Prepare data for charts
        path_data = []
        for i in range(time_horizon):
            day_data = {"day": i}
            for j in range(5):
                day_data[f"path_{j+1}"] = simulation_paths[j][i]
            day_data["mean_path"] = np.mean([p[i] for p in simulation_paths])
            path_data.append(day_data)

        hist, bin_edges = np.histogram(final_values, bins=20)
        distribution_data = []
        for i in range(len(hist)):
            distribution_data.append({
                "range": f"{int(bin_edges[i])}-{int(bin_edges[i+1])}",
                "count": int(hist[i]),
                "percentage": float(hist[i]) / scenarios * 100,
            })

        return {
            "scenarios": scenarios,
            "time_horizon": time_horizon,
            "initial_value": total_value,
            "final_mean": final_mean,
            "final_std": final_std,
            "percentile_5": percentile_5,
            "percentile_95": percentile_95,
            "success_probability": success_probability,
            "simulation_paths": path_data,
            "final_distribution": distribution_data,
        }

    async def run_cppi_simulation(self, multiplier: int = 3, floor: float = 0.8, time_horizon: int = 252) -> Dict:
        """Run a CPPI simulation for the portfolio."""
        holdings, price_history = await self.get_portfolio_data()
        returns_data = self._calculate_returns(price_history)
        
        # Get portfolio statistics
        total_value = sum(h.quantity * h.current_price for h in holdings)
        weights = [(h.quantity * h.current_price) / total_value for h in holdings]
        portfolio_return = self._calculate_portfolio_return(weights, returns_data)
        portfolio_volatility = self._calculate_portfolio_volatility(weights, returns_data)

        # Run simulation
        cppi_wealth = [total_value]
        buyhold_wealth = [total_value]
        floor_value = total_value * floor
        risky_allocation = []
        risk_budget = []

        for i in range(time_horizon):
            # CPPI strategy
            cushion = cppi_wealth[-1] - floor_value
            exposure = multiplier * cushion
            risky_alloc = min(1, exposure / cppi_wealth[-1])
            risky_allocation.append(risky_alloc * 100)
            risk_budget.append(cushion / cppi_wealth[-1] * 100)

            daily_return = np.random.normal(portfolio_return, portfolio_volatility)
            cppi_return = risky_alloc * daily_return + (1 - risky_alloc) * (self.risk_free_rate / 252)
            cppi_wealth.append(cppi_wealth[-1] * (1 + cppi_return))

            # Buy and hold strategy
            buyhold_wealth.append(buyhold_wealth[-1] * (1 + daily_return))

        # Performance data
        performance_data = []
        for i in range(time_horizon):
            performance_data.append({
                "day": i,
                "cppi_wealth": cppi_wealth[i],
                "buyhold_wealth": buyhold_wealth[i],
                "floor_value": floor_value,
                "risky_allocation": risky_allocation[i],
                "risk_budget": risk_budget[i],
            })

        # Drawdown data
        cppi_drawdown = (np.array(cppi_wealth) - np.maximum.accumulate(cppi_wealth)) / np.maximum.accumulate(cppi_wealth)
        buyhold_drawdown = (np.array(buyhold_wealth) - np.maximum.accumulate(buyhold_wealth)) / np.maximum.accumulate(buyhold_wealth)
        drawdown_data = []
        for i in range(time_horizon):
            drawdown_data.append({
                "day": i,
                "cppi_drawdown": cppi_drawdown[i] * 100,
                "buyhold_drawdown": buyhold_drawdown[i] * 100,
            })

        return {
            "multiplier": multiplier,
            "floor": floor,
            "initial_value": total_value,
            "final_cppi_value": cppi_wealth[-1],
            "final_buyhold_value": buyhold_wealth[-1],
            "outperformance": (cppi_wealth[-1] - buyhold_wealth[-1]) / buyhold_wealth[-1],
            "performance_data": performance_data,
            "drawdown_data": drawdown_data,
        }

    async def sector_analysis(self) -> Dict:
        """Analyze portfolio by sector"""
        holdings, _ = await self.get_portfolio_data()
        sector_data = {}
        total_value = sum(h.quantity * h.current_price for h in holdings)

        for holding in holdings:
            sector = holding.asset.sector
            if sector not in sector_data:
                sector_data[sector] = {
                    "value": 0,
                    "positions": 0,
                }
            
            sector_data[sector]["value"] += holding.quantity * holding.current_price
            sector_data[sector]["positions"] += 1
        
        # Calculate percentages
        for sector in sector_data:
            sector_data[sector]["percentage"] = (
                sector_data[sector]["value"] / total_value * 100
            )
        
        return sector_data