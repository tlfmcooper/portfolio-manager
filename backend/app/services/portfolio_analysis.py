"""
Portfolio analysis service - Production implementation using real market data.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

# Core imports from portfolio_manager
from portfolio_manager import Portfolio, Asset, YFinanceProvider
from portfolio_manager.core.asset import AssetType
from portfolio_manager.analytics.performance import PerformanceAnalytics
from portfolio_manager.analytics.risk import RiskAnalytics
from portfolio_manager.analytics import (
    annualize_rets,
    annualize_vol,
    sharpe_ratio,
    drawdown,
    semideviation,
    var_historic,
    cvar_historic,
    portfolio_return,
    portfolio_vol,
    msr,
    gmv,
    optimal_weights,
    run_cppi,
    gbm,
)

from app.models.holding import Holding


class AdvancedPortfolioAnalytics:
    """Advanced analytics engine for portfolio management - Production version"""

    def __init__(self, portfolio_id: int, db: AsyncSession):
        self.portfolio_id = portfolio_id
        self.db = db
        self.risk_free_rate = 0.042  # 4.2% risk-free rate
        self.provider = YFinanceProvider()

    async def _build_portfolio(self) -> Optional[Portfolio]:
        """Builds a portfolio_manager.Portfolio object from database data."""
        result = await self.db.execute(
            select(Holding)
            .where(Holding.portfolio_id == self.portfolio_id)
            .options(selectinload(Holding.asset))
        )
        holdings = result.scalars().all()

        if not holdings:
            return None

        portfolio = Portfolio(name="User Portfolio")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=2 * 365)  # 2 years of data

        total_portfolio_value = 0
        # First pass: add assets and get their market value
        for holding in holdings:
            asset_model = holding.asset
            try:
                price_data = self.provider.get_price_data(
                    asset_model.ticker, start_date, end_date
                )
                if not price_data.empty:
                    asset = Asset(
                        symbol=asset_model.ticker,
                        name=asset_model.name or asset_model.ticker,
                        asset_type=AssetType.STOCK,  # Assuming stocks for now
                    )
                    portfolio.add_asset(symbol=asset.symbol, asset=asset, weight=0, price_data=price_data) # Add asset with 0 weight initially
                    latest_price = price_data['Close'].iloc[-1]
                    total_portfolio_value += holding.quantity * latest_price

            except Exception as e:
                print(f"Could not fetch data for {asset_model.ticker}: {e}")
        
        # Second pass: calculate and set weights
        if total_portfolio_value > 0:
            for holding in holdings:
                 if holding.asset.ticker in portfolio.assets:
                    latest_price = portfolio.assets[holding.asset.ticker].price_data['Close'].iloc[-1]
                    market_value = holding.quantity * latest_price
                    weight = market_value / total_portfolio_value
                    portfolio.weights[holding.asset.ticker] = weight
        
        return portfolio

    async def calculate_portfolio_metrics(self) -> Dict:
        """Calculate comprehensive portfolio metrics using the portfolio_manager package."""
        portfolio = await self._build_portfolio()
        if not portfolio or not portfolio.assets:
            return {}

        perf_analytics = PerformanceAnalytics(portfolio)
        risk_analytics = RiskAnalytics(portfolio)

        portfolio_returns = portfolio.get_portfolio_returns()

        if portfolio_returns.empty:
            return {}

        # Using portfolio_manager functions
        annual_return = perf_analytics.annualized_return()
        annual_vol = perf_analytics.volatility()
        sharpe = perf_analytics.sharpe_ratio(risk_free_rate=self.risk_free_rate)
        sortino = perf_analytics.sortino_ratio(risk_free_rate=self.risk_free_rate)
        max_dd_info = perf_analytics.max_drawdown()
        calmar = perf_analytics.calmar_ratio()
        
        hist_var_95 = var_historic(portfolio_returns, level=5)
        hist_var_99 = var_historic(portfolio_returns, level=1)
        hist_cvar_95 = cvar_historic(portfolio_returns, level=5)
        semi_dev = semideviation(portfolio_returns)

        # Individual asset performance
        individual_performance = {}
        asset_returns = {}
        for symbol, asset in portfolio.assets.items():
            try:
                returns = asset.get_returns()
                if not returns.empty:
                    asset_returns[symbol] = returns
            except Exception as e:
                continue
        if not asset_returns:
            return {}
        returns_df = pd.DataFrame(asset_returns).dropna()
        if not returns_df.empty:
            for symbol, asset in portfolio.assets.items():
                asset_returns = returns_df[symbol]
                if not asset_returns.empty:
                    individual_performance[symbol] = {
                        "return": annualize_rets(asset_returns, 252),
                        "volatility": annualize_vol(asset_returns, 252),
                                        }

        total_value = portfolio.get_total_value()

        # Handle potential NaN or inf values before returning
        def clean_value(value):
            if isinstance(value, (float, np.float64)):
                if np.isnan(value) or np.isinf(value):
                    return None
            return value

        return {
            "portfolio_return_annualized": clean_value(annual_return),
            "portfolio_volatility_annualized": clean_value(annual_vol),
            "sharpe_ratio": clean_value(sharpe),
            "sortino_ratio": clean_value(sortino),
            "value_at_risk_95": clean_value(hist_var_95),
            "value_at_risk_99": clean_value(hist_var_99),
            "cvar": clean_value(hist_cvar_95),
            "semideviation": clean_value(semi_dev),
            "max_drawdown": clean_value(max_dd_info['max_drawdown']),
            "calmar_ratio": clean_value(calmar),
            "total_portfolio_value": clean_value(total_value),
            "number_of_positions": len(portfolio.assets),
            "concentration_risk": clean_value(max(portfolio.weights.values()) if portfolio.weights else 0),
            "individual_performance": {
                symbol: {k: clean_value(v) for k, v in metrics.items()}
                for symbol, metrics in individual_performance.items()
            },
        }

    async def generate_efficient_frontier(self) -> Dict:
        """Generate the efficient frontier for the portfolio."""
        portfolio = await self._build_portfolio()
        if not portfolio or len(portfolio.assets) < 2:
            return {}

        asset_returns = {}
        for symbol, asset in portfolio.assets.items():
            try:
                returns = asset.get_returns()
                if not returns.empty:
                    asset_returns[symbol] = returns
            except Exception as e:
                continue
        if not asset_returns:
            return {}
        returns_df = pd.DataFrame(asset_returns).dropna()
        if returns_df.empty:
            return {}

        expected_returns = annualize_rets(returns_df, 252)
        cov_matrix = returns_df.cov() * 252

        n_points = 20
        weights_list = optimal_weights(n_points, expected_returns.values, cov_matrix.values)

        frontier_points = []
        for weights in weights_list:
            port_ret = portfolio_return(weights, expected_returns.values)
            port_vol = portfolio_vol(weights, cov_matrix.values)
            frontier_points.append({"risk": port_vol, "return": port_ret})

        # Get special portfolios
        msr_weights = msr(self.risk_free_rate, expected_returns.values, cov_matrix.values)
        gmv_weights = gmv(cov_matrix.values)

        msr_return = portfolio_return(msr_weights, expected_returns.values)
        msr_vol = portfolio_vol(msr_weights, cov_matrix.values)

        gmv_return = portfolio_return(gmv_weights, expected_returns.values)
        gmv_vol = portfolio_vol(gmv_weights, cov_matrix.values)
        
        current_weights = np.array(list(portfolio.weights.values()))
        current_return = portfolio_return(current_weights, expected_returns.values)
        current_risk = portfolio_vol(current_weights, cov_matrix.values)

        special_portfolios = {
            "current": {"name": "Current Portfolio", "risk": current_risk, "return": current_return},
            "msr": {"name": "Max Sharpe Ratio", "risk": msr_vol, "return": msr_return},
            "gmv": {"name": "Global Minimum Volatility", "risk": gmv_vol, "return": gmv_return},
        }

        return {
            "frontier_points": frontier_points,
            "special_portfolios": special_portfolios,
        }

    async def run_monte_carlo_simulation(self, scenarios: int = 1000, time_horizon: int = 252) -> Dict:
        """Run a Monte Carlo simulation for the portfolio."""
        portfolio = await self._build_portfolio()
        if not portfolio or not portfolio.assets:
            return {}

        portfolio_returns = portfolio.get_portfolio_returns()
        if portfolio_returns.empty:
            return {}

        annual_ret = annualize_rets(portfolio_returns, 252)
        annual_vol_sim = annualize_vol(portfolio_returns, 252)
        total_value = portfolio.get_total_value()

        mc_results = gbm(
            n_years=time_horizon / 252,
            n_scenarios=scenarios,
            mu=annual_ret,
            sigma=annual_vol_sim,
            steps_per_year=252,
            s_0=total_value,
            prices=True,
        )
        # Ensure mc_results is a numpy array before indexing
        if isinstance(mc_results, pd.DataFrame):
            mc_results = mc_results.values
        elif isinstance(mc_results, pd.Series):
            mc_results = mc_results.values

        print(f"Type of mc_results after conversion: {type(mc_results)}")
        print(f"Shape of mc_results after conversion: {mc_results.shape}")

        final_values = mc_results[-1, :]

        final_mean = np.mean(final_values)
        final_std = np.std(final_values)
        percentile_5 = np.percentile(final_values, 5)
        percentile_95 = np.percentile(final_values, 95)
        success_probability = np.mean([1 if fv > total_value else 0 for fv in final_values])

        # Data for charts
        path_data = []
        for i in range(time_horizon):
            day_data = {"day": i}
            for j in range(min(5, scenarios)):
                day_data[f"path_{j+1}"] = mc_results[i, j]
            day_data["mean_path"] = np.mean(mc_results[i, :])
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
        portfolio = await self._build_portfolio()
        if not portfolio or not portfolio.assets:
            return {}

        portfolio_returns = portfolio.get_portfolio_returns()
        if portfolio_returns.empty:
            return {}
        
        total_value = portfolio.get_total_value()

        cppi_results = run_cppi(
            risky_r=portfolio_returns,
            m=multiplier,
            start=total_value,
            floor=floor,
            riskfree_rate=self.risk_free_rate,
        )

        final_cppi_wealth = cppi_results["Wealth"].iloc[-1].iloc[0]
        final_buyhold_wealth = cppi_results["Risky Wealth"].iloc[-1].iloc[0]
        outperformance = (final_cppi_wealth - final_buyhold_wealth) / final_buyhold_wealth

        # Data for charts
        performance_data = []
        for i in range(len(cppi_results["Wealth"])):
            performance_data.append({
                "day": i,
                "cppi_wealth": cppi_results["Wealth"].iloc[i, 0],
                "buyhold_wealth": cppi_results["Risky Wealth"].iloc[i, 0],
                "floor_value": cppi_results["floor"].iloc[i, 0],
                "risky_allocation": cppi_results["Risky Allocation"].iloc[i, 0] * 100,
                "risk_budget": cppi_results["Risk Budget"].iloc[i, 0] * 100,
            })

        drawdown_cppi = drawdown(cppi_results["Wealth"].iloc[:, 0])
        drawdown_risky = drawdown(cppi_results["Risky Wealth"].iloc[:, 0])
        drawdown_data = []
        for i in range(len(drawdown_cppi)):
            drawdown_data.append({
                "day": i,
                "cppi_drawdown": drawdown_cppi['Drawdown'].iloc[i] * 100,
                "buyhold_drawdown": drawdown_risky['Drawdown'].iloc[i] * 100,
            })

        # Handle potential NaN or inf values before returning
        def clean_value(value):
            if isinstance(value, (float, np.float64)):
                if np.isnan(value) or np.isinf(value):
                    return None
            return value

        return {
            "multiplier": multiplier,
            "floor": floor,
            "initial_value": clean_value(total_value),
            "final_cppi_value": clean_value(final_cppi_wealth),
            "final_buyhold_value": clean_value(final_buyhold_wealth),
            "outperformance": clean_value(outperformance),
            "performance_data": [
                {k: clean_value(v) for k, v in item.items()} for item in performance_data
            ],
            "drawdown_data": [
                {k: clean_value(v) for k, v in item.items()} for item in drawdown_data
            ],
        }

    async def sector_analysis(self) -> Dict:
        """Analyze portfolio by sector."""
        result = await self.db.execute(
            select(Holding)
            .where(Holding.portfolio_id == self.portfolio_id)
            .options(selectinload(Holding.asset))
        )
        holdings = result.scalars().all()

        if not holdings:
            return {}

        sector_data = {}
        total_value = 0

        # We need to fetch current prices to get market values
        portfolio = await self._build_portfolio()
        if not portfolio:
            return {}

        for holding in holdings:
            asset_symbol = holding.asset.ticker
            asset_obj = portfolio.assets[asset_symbol]
            if not asset_obj:
                continue
            
            current_price = asset_obj.get_current_price()
            if current_price is None:
                continue

            market_value = holding.quantity * current_price
            sector = holding.asset.sector or "Unknown"

            if sector not in sector_data:
                sector_data[sector] = {
                    "value": 0,
                    "positions": 0,
                }
            
            sector_data[sector]["value"] += market_value
            sector_data[sector]["positions"] += 1
            total_value += market_value
        
        if total_value > 0:
            for sector in sector_data:
                sector_data[sector]["percentage"] = (
                    sector_data[sector]["value"] / total_value * 100
                )
        
        return sector_data