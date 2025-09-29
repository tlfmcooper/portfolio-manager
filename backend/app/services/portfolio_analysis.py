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
        self._cached_portfolio = None
        self._cached_portfolio_value = None  # Store the actual market value

    async def _build_portfolio(self) -> Optional[Portfolio]:
        """
        Builds a portfolio_manager.Portfolio object from database data.
        Weights are calculated dynamically as: weight = (quantity × current_price) / total_portfolio_value
        """
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

        # Step 1: Fetch price data and calculate market values for each holding
        assets_data = {}
        total_portfolio_value = 0.0
        
        for holding in holdings:
            asset_model = holding.asset
            try:
                price_data = self.provider.get_price_data(
                    asset_model.ticker, start_date, end_date
                )
                if not price_data.empty and len(price_data) > 100:  # Ensure sufficient data
                    # Get current market price (most recent closing price)
                    current_price = float(price_data['Close'].iloc[-1])
                    
                    # Calculate market value: quantity × current_price
                    market_value = holding.quantity * current_price
                    
                    asset = Asset(
                        symbol=asset_model.ticker,
                        name=asset_model.name or asset_model.ticker,
                        asset_type=AssetType.STOCK,
                    )
                    
                    assets_data[asset_model.ticker] = {
                        'asset': asset,
                        'price_data': price_data,
                        'market_value': market_value,
                        'quantity': holding.quantity,
                        'current_price': current_price
                    }
                    total_portfolio_value += market_value
                    
                    print(f"Asset {asset_model.ticker}: qty={holding.quantity}, price=${current_price:.2f}, value=${market_value:.2f}")

            except Exception as e:
                print(f"[ERROR] Could not fetch data for {asset_model.ticker}: {e}")
        
        if not assets_data or total_portfolio_value == 0:
            print("[ERROR] No valid assets or zero portfolio value")
            return None
        
        print(f"Total portfolio value: ${total_portfolio_value:.2f}")
        
        # Step 2: Calculate dynamic weights and add assets to portfolio
        # Weight = market_value / total_portfolio_value (ensures sum = 1.0 or 100%)
        total_weight = 0.0
        
        for ticker, data in assets_data.items():
            # Dynamic weight calculation based on current market value
            weight = data['market_value'] / total_portfolio_value
            total_weight += weight
            
            portfolio.add_asset(
                symbol=data['asset'].symbol,
                asset=data['asset'],
                weight=weight,
                price_data=data['price_data']
            )
            
            print(f"Added {ticker}: weight={weight:.4f} ({weight*100:.2f}%)")
        
        # Validation: ensure weights sum to 1.0 (100%)
        print(f"Total weight: {total_weight:.6f} (should be 1.0)")
        if abs(total_weight - 1.0) > 0.01:  # Allow small floating point errors
            print(f"[WARNING] Weights don't sum to 1.0: {total_weight}")
        
        # Store the actual portfolio market value for use in simulations
        self._cached_portfolio_value = total_portfolio_value
        print(f"[INFO] Cached portfolio value: ${total_portfolio_value:.2f}")
        
        return portfolio if portfolio.assets else None

    async def get_current_portfolio_value(self) -> float:
        """Get the current market value of the portfolio."""
        if self._cached_portfolio_value is None:
            await self._build_portfolio()
        return self._cached_portfolio_value or 0.0

    async def calculate_portfolio_metrics(self) -> Dict:
        """Calculate comprehensive portfolio metrics using the portfolio_manager package."""
        portfolio = await self._build_portfolio()
        if not portfolio or not portfolio.assets:
            return {}

        perf_analytics = PerformanceAnalytics(portfolio)
        risk_analytics = RiskAnalytics(portfolio)

        portfolio_returns = portfolio.get_portfolio_returns()
        
        print(f"Metrics: portfolio_returns shape: {portfolio_returns.shape}")
        print(f"Metrics: portfolio_returns has NaN before cleaning: {portfolio_returns.isnull().any()}")

        if portfolio_returns.empty:
            print("[ERROR] Metrics: Portfolio returns are empty")
            return {}
        
        # Clean the returns data - remove NaN values (like in the demo)
        initial_length = len(portfolio_returns)
        portfolio_returns = portfolio_returns.dropna()
        final_length = len(portfolio_returns)
        
        if initial_length != final_length:
            print(f"[WARNING] Metrics: Dropped {initial_length - final_length} NaN values from returns")
        
        if len(portfolio_returns) < 50:
            print(f"[ERROR] Metrics: Insufficient clean data ({len(portfolio_returns)} days)")
            return {}
        
        print(f"Metrics: Clean returns count: {len(portfolio_returns)}")

        try:
            # Using portfolio_manager functions
            annual_return = perf_analytics.annualized_return()
            annual_vol = perf_analytics.volatility()
            sharpe = perf_analytics.sharpe_ratio(risk_free_rate=self.risk_free_rate)
            sortino = perf_analytics.sortino_ratio(risk_free_rate=self.risk_free_rate)
            max_dd_info = perf_analytics.max_drawdown()
            calmar = perf_analytics.calmar_ratio()
            
            # Use clean portfolio_returns for VaR calculations
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
                print("[WARNING] Metrics: No asset returns available")
            else:
                returns_df = pd.DataFrame(asset_returns).dropna()  # Clean asset returns too
                
                if not returns_df.empty:
                    for symbol in returns_df.columns:
                        if symbol in portfolio.assets:
                            asset_return_series = returns_df[symbol]
                            if not asset_return_series.empty:
                                individual_performance[symbol] = {
                                    "return": annualize_rets(asset_return_series, 252),
                                    "volatility": annualize_vol(asset_return_series, 252),
                                }

            total_value = self._cached_portfolio_value or portfolio.get_total_value()
            print(f"[INFO] Using portfolio value: ${total_value:.2f}")

            # Handle potential NaN or inf values before returning
            def clean_value(value):
                if isinstance(value, (float, np.float64)):
                    if np.isnan(value) or np.isinf(value):
                        return None
                return value

            result = {
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
            
            print(f"[SUCCESS] Metrics calculated: Return={annual_return:.2%}, Sharpe={sharpe:.3f}, VaR95={hist_var_95:.2%}")
            return result
            
        except Exception as e:
            print(f"[ERROR] Metrics calculation failed: {e}")
            import traceback
            traceback.print_exc()
            return {}

    async def generate_efficient_frontier(self) -> Dict:
        """Generate the efficient frontier for the portfolio."""
        portfolio = await self._build_portfolio()
        if not portfolio or len(portfolio.assets) < 2:
            print(f"[ERROR] Efficient Frontier: Need at least 2 assets, have {len(portfolio.assets) if portfolio else 0}")
            return {}

        # Collect asset returns
        asset_returns = {}
        for symbol, asset in portfolio.assets.items():
            try:
                returns = asset.get_returns()
                if not returns.empty:
                    asset_returns[symbol] = returns
            except Exception as e:
                print(f"[WARNING] Efficient Frontier: Could not get returns for {symbol}: {e}")
                continue
                
        if len(asset_returns) < 2:
            print(f"[ERROR] Efficient Frontier: Need at least 2 assets with returns, have {len(asset_returns)}")
            return {}
            
        # Clean returns data (like in the demo)
        returns_df = pd.DataFrame(asset_returns).dropna()
        
        if returns_df.empty or len(returns_df) < 50:
            print(f"[ERROR] Efficient Frontier: Insufficient clean data ({len(returns_df)} days)")
            return {}
        
        print(f"Efficient Frontier: Using {len(returns_df)} days of clean returns for {len(returns_df.columns)} assets")

        try:
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

            result = {
                "frontier_points": frontier_points,
                "special_portfolios": special_portfolios,
            }
            
            print(f"[SUCCESS] Efficient frontier generated with {len(frontier_points)} points")
            return result
            
        except Exception as e:
            print(f"[ERROR] Efficient frontier generation failed: {e}")
            import traceback
            traceback.print_exc()
            return {}

    async def run_monte_carlo_simulation(self, scenarios: int = 1000, time_horizon: int = 252) -> Dict:
        """Run a Monte Carlo simulation for the portfolio."""
        portfolio = await self._build_portfolio()
        if not portfolio or not portfolio.assets:
            print("[ERROR] Monte Carlo: No portfolio or assets")
            return {}

        portfolio_returns = portfolio.get_portfolio_returns()
        
        if portfolio_returns.empty:
            print("[ERROR] Monte Carlo: Portfolio returns are empty")
            return {}
        
        # Clean the returns data - remove NaN values (like in the demo)
        initial_length = len(portfolio_returns)
        portfolio_returns = portfolio_returns.dropna()
        final_length = len(portfolio_returns)
        
        if initial_length != final_length:
            print(f"[WARNING] Monte Carlo: Dropped {initial_length - final_length} NaN values from returns")
        
        if len(portfolio_returns) < 50:
            print(f"[ERROR] Monte Carlo: Insufficient clean data ({len(portfolio_returns)} days)")
            return {}
        
        print(f"Monte Carlo: Clean returns count: {len(portfolio_returns)}")

        try:
            annual_ret = annualize_rets(portfolio_returns, 252)
            annual_vol_sim = annualize_vol(portfolio_returns, 252)
            
            # Use the actual calculated portfolio value, not portfolio.get_total_value()
            total_value = self._cached_portfolio_value or portfolio.get_total_value()
            print(f"[INFO] Monte Carlo using portfolio value: ${total_value:.2f}")

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

            result = {
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
            
            print(f"[SUCCESS] Monte Carlo completed: mean=${final_mean:.2f}, 5th%=${percentile_5:.2f}, 95th%=${percentile_95:.2f}")
            return result
            
        except Exception as e:
            print(f"[ERROR] Monte Carlo simulation failed: {e}")
            import traceback
            traceback.print_exc()
            return {}

    async def run_cppi_simulation(self, multiplier: int = 3, floor: float = 0.8, time_horizon: int = 252) -> Dict:
        """Run a CPPI simulation for the portfolio."""
        portfolio = await self._build_portfolio()
        if not portfolio or not portfolio.assets:
            print("[ERROR] CPPI: No portfolio or assets")
            return {}

        portfolio_returns = portfolio.get_portfolio_returns()
        print(f"CPPI: portfolio_returns shape: {portfolio_returns.shape}")
        print(f"CPPI: portfolio_returns empty: {portfolio_returns.empty}")
        print(f"CPPI: portfolio_returns has NaN: {portfolio_returns.isnull().any()}")
        
        if portfolio_returns.empty:
            print("[ERROR] CPPI: Portfolio returns are empty")
            return {}
        
        # Clean the returns data - remove NaN values like in the demo
        initial_length = len(portfolio_returns)
        portfolio_returns = portfolio_returns.dropna()
        final_length = len(portfolio_returns)
        
        if initial_length != final_length:
            print(f"[WARNING] CPPI: Dropped {initial_length - final_length} NaN values from returns")
        
        if len(portfolio_returns) < 50:  # Need minimum data for meaningful CPPI
            print(f"[ERROR] CPPI: Insufficient clean data ({len(portfolio_returns)} days)")
            return {}
        
        print(f"CPPI: Clean returns count: {len(portfolio_returns)}")
        print(f"CPPI: Returns sample (first 5): {portfolio_returns.head()}")
        
        # Use the actual calculated portfolio value, not portfolio.get_total_value()
        total_value = self._cached_portfolio_value or portfolio.get_total_value()
        print(f"CPPI: Using actual portfolio value: ${total_value:.2f}")

        try:
            cppi_results = run_cppi(
                risky_r=portfolio_returns,
                m=multiplier,
                start=total_value,
                floor=floor,
                riskfree_rate=self.risk_free_rate,
            )
            print(f"CPPI: cppi_results keys: {cppi_results.keys()}")
            print(f"CPPI: cppi_results Wealth shape: {cppi_results['Wealth'].shape}")
            print(f"CPPI: cppi_results Wealth head:\n{cppi_results['Wealth'].head()}")
            
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

            result = {
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
            
            print(f"[SUCCESS] CPPI simulation completed: final CPPI=${final_cppi_wealth:.2f}, Buy&Hold=${final_buyhold_wealth:.2f}")
            return result
            
        except Exception as e:
            print(f"[ERROR] CPPI simulation failed: {e}")
            import traceback
            traceback.print_exc()
            return {}

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