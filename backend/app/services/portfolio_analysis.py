"""
Portfolio analysis service - Production implementation using real market data.
"""

import numpy as np
import pandas as pd
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from concurrent.futures import ThreadPoolExecutor

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
from app.models.portfolio import Portfolio as DBPortfolio
from app.services.exchange_rate_service import get_exchange_rate_service


def map_asset_type(asset_type_str: Optional[str]) -> AssetType:
    """
    Map database asset_type string to portfolio_manager AssetType enum.

    Args:
        asset_type_str: Asset type string from database (e.g., 'stock', 'mutual_fund', 'crypto')

    Returns:
        AssetType enum value
    """
    if not asset_type_str:
        return AssetType.STOCK  # Default

    asset_type_lower = asset_type_str.lower().replace(' ', '_')

    type_mapping = {
        'stock': AssetType.STOCK,
        'mutual_fund': AssetType.MUTUAL_FUND,
        'mutualfund': AssetType.MUTUAL_FUND,
        'crypto': AssetType.CRYPTOCURRENCY,
        'cryptocurrency': AssetType.CRYPTOCURRENCY,
        'etf': AssetType.ETF,
        'bond': AssetType.BOND,
        'cash': AssetType.CASH,
        'commodity': AssetType.COMMODITY,
    }

    return type_mapping.get(asset_type_lower, AssetType.OTHER)


class AdvancedPortfolioAnalytics:
    """Advanced analytics engine for portfolio management - Production version"""

    def __init__(self, portfolio_id: int, db: AsyncSession, display_currency: Optional[str] = None):
        self.portfolio_id = portfolio_id
        self.db = db
        self.display_currency = display_currency
        self.risk_free_rate = 0.042  # 4.2% risk-free rate
        self.provider = YFinanceProvider()
        self._cached_portfolio = None
        self._cached_portfolio_value = None  # Store the actual market value
        self._building_portfolio = False  # Prevent concurrent builds

    async def _build_portfolio(self) -> Optional[Portfolio]:
        """
        Builds a portfolio_manager.Portfolio object from database data.
        Weights are calculated dynamically as: weight = (quantity × current_price) / total_portfolio_value
        Currency conversion is applied if display_currency is specified.
        Returns cached portfolio if already built to avoid redundant yfinance calls.
        """
        # Return cached portfolio if already built
        if self._cached_portfolio is not None:
            print(f"[INFO] Returning cached portfolio (value: ${self._cached_portfolio_value:.2f})")
            return self._cached_portfolio

        result = await self.db.execute(
            select(Holding)
            .where(Holding.portfolio_id == self.portfolio_id)
            .where(Holding.quantity > 0)
            .options(selectinload(Holding.asset))
        )
        holdings = result.scalars().all()

        if not holdings:
            return None

        # Get portfolio currency
        portfolio_result = await self.db.execute(
            select(DBPortfolio).where(DBPortfolio.id == self.portfolio_id)
        )
        db_portfolio = portfolio_result.scalar_one_or_none()

        # Use display currency or portfolio's base currency
        display_currency = self.display_currency or (db_portfolio.currency if db_portfolio else "USD")
        exchange_service = get_exchange_rate_service()

        # Pre-fetch all needed exchange rates to avoid repeated API calls
        exchange_rates = {}
        currencies_needed = set()
        for holding in holdings:
            if holding.asset:
                currencies_needed.add(holding.asset.currency)

        # Fetch all needed exchange rates upfront
        for currency in currencies_needed:
            if currency != display_currency:
                rate = await exchange_service.get_exchange_rate(currency, display_currency)
                exchange_rates[currency] = rate
                print(f"[INFO] Pre-fetched exchange rate: {currency}/{display_currency} = {rate}")

        portfolio = Portfolio(name="User Portfolio")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=2 * 365)  # 2 years of data

        # Step 1: Fetch price data and calculate market values for each holding
        assets_data = {}
        total_portfolio_value = 0.0
        total_portfolio_value_realtime = 0.0  # CRITICAL FIX: Track real-time value from DB

        # PERFORMANCE FIX: Fetch yfinance data in parallel
        async def fetch_holding_data(holding):
            """Fetch price data for a single holding in parallel."""
            nonlocal total_portfolio_value_realtime

            asset_model = holding.asset
            asset_currency = asset_model.currency if asset_model else "USD"

            result = {
                'realtime_value': 0,
                'asset_data': None
            }

            # CRITICAL FIX: Always calculate real-time portfolio value
            realtime_price = holding.current_price or holding.average_cost
            if realtime_price and realtime_price > 0:
                realtime_market_value = holding.quantity * realtime_price

                # Convert to display currency if needed using pre-fetched rate
                if asset_currency != display_currency and asset_currency in exchange_rates:
                    rate = exchange_rates[asset_currency]
                    realtime_market_value = realtime_market_value * rate

                result['realtime_value'] = realtime_market_value
                print(f"Adding {asset_model.ticker} to real-time total: qty={holding.quantity}, price=${realtime_price:.2f}, value=${realtime_market_value:.2f} {display_currency}")

            # CRITICAL FIX: Skip yfinance for crypto and mutual_fund
            if asset_model.asset_type in ['crypto', 'mutual_fund']:
                print(f"[INFO] Skipping yfinance for {asset_model.ticker} (asset_type={asset_model.asset_type}), using DB price only")
                return result

            # Fetch yfinance data in thread pool (yfinance is blocking/sync)
            try:
                loop = asyncio.get_event_loop()
                price_data = await loop.run_in_executor(
                    None,  # Use default thread pool
                    self.provider.get_price_data,
                    asset_model.ticker,
                    start_date,
                    end_date
                )

                if not price_data.empty and len(price_data) > 100:
                    yfinance_price = float(price_data['Close'].iloc[-1])
                    market_value = holding.quantity * yfinance_price

                    # Convert to display currency if needed
                    if asset_currency != display_currency and asset_currency in exchange_rates:
                        rate = exchange_rates[asset_currency]
                        market_value = market_value * rate

                    mapped_asset_type = map_asset_type(asset_model.asset_type)
                    asset = Asset(
                        symbol=asset_model.ticker,
                        name=asset_model.name or asset_model.ticker,
                        asset_type=mapped_asset_type,
                    )

                    result['asset_data'] = {
                        'ticker': asset_model.ticker,
                        'asset': asset,
                        'price_data': price_data,
                        'market_value': market_value,
                        'quantity': holding.quantity,
                        'current_price': yfinance_price
                    }

                    print(f"Asset {asset_model.ticker}: qty={holding.quantity}, yfinance=${yfinance_price:.2f}, value=${market_value:.2f} {display_currency}")

            except Exception as e:
                print(f"[ERROR] Could not fetch data for {asset_model.ticker}: {e}")

            return result

        # Fetch all holdings data in parallel
        print(f"[INFO] Fetching yfinance data for {len(holdings)} holdings in parallel...")
        fetch_tasks = [fetch_holding_data(holding) for holding in holdings]
        results = await asyncio.gather(*fetch_tasks)

        # Process results
        for result in results:
            total_portfolio_value_realtime += result['realtime_value']
            if result['asset_data']:
                ticker = result['asset_data']['ticker']
                assets_data[ticker] = result['asset_data']
                total_portfolio_value += result['asset_data']['market_value']
        
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

        # CRITICAL FIX: Store the REAL-TIME portfolio market value for use in simulations
        # Use real-time prices from database instead of stale yfinance closing prices
        self._cached_portfolio_value = total_portfolio_value_realtime if total_portfolio_value_realtime > 0 else total_portfolio_value
        print(f"[INFO] Cached portfolio value (real-time): ${self._cached_portfolio_value:.2f}")
        print(f"[INFO] Portfolio value (yfinance closing): ${total_portfolio_value:.2f}")
        print(f"[INFO] Price difference: ${abs(self._cached_portfolio_value - total_portfolio_value):.2f}")

        # Cache the built portfolio to avoid redundant yfinance calls
        self._cached_portfolio = portfolio if portfolio.assets else None

        # Pre-populate analytics cache so all tabs share one yfinance build
        if self._cached_portfolio:
            try:
                raw_returns = portfolio.get_portfolio_returns()
                clean_returns = raw_returns.dropna().copy()
                if not clean_returns.empty:
                    # Collect per-asset returns
                    asset_returns_map: Dict[str, pd.Series] = {}
                    for sym, asset_obj in portfolio.assets.items():
                        try:
                            ar = asset_obj.get_returns()
                            if not ar.empty:
                                asset_returns_map[sym] = ar
                        except Exception:
                            pass
                    await self._cache_returns(clean_returns, self._cached_portfolio_value)
                    await self._set_analytics_cache(
                        clean_returns,
                        asset_returns_map,
                        dict(portfolio.weights),
                        self._cached_portfolio_value,
                    )
            except Exception as e:
                print(f"[WARN] Failed to pre-populate analytics cache: {e}")

        return self._cached_portfolio

    async def _get_cached_returns(self):
        """
        Retrieve cached (returns, total_value) from Redis.
        Returns (pd.Series, float) on hit, (None, None) on miss.
        """
        from app.core.redis_client import get_redis_client
        cache_key = f"portfolio:{self.portfolio_id}:returns_cache"
        redis_client = await get_redis_client()
        cached = await redis_client.get(cache_key)
        if cached is None:
            return None, None
        try:
            index = pd.to_datetime(cached["index"]) if "index" in cached else None
            returns = pd.Series(cached["values"], index=index, dtype=float)
            total_value = float(cached["total_value"])
            print(f"[INFO] Returns cache hit: {len(returns)} days, value=${total_value:.2f}")
            return returns, total_value
        except Exception as e:
            print(f"[WARN] Failed to deserialize returns cache: {e}")
            return None, None

    async def _cache_returns(self, returns: pd.Series, total_value: float) -> None:
        """Store portfolio returns + value in Redis for 15 minutes."""
        from app.core.redis_client import get_redis_client
        cache_key = f"portfolio:{self.portfolio_id}:returns_cache"
        redis_client = await get_redis_client()
        try:
            await redis_client.set(
                cache_key,
                {
                    "values": returns.tolist(),
                    "index": [str(i) for i in returns.index],
                    "total_value": total_value,
                },
                ttl=900
            )
            print(f"[INFO] Cached {len(returns)} days of returns to Redis")
        except Exception as e:
            print(f"[WARN] Failed to cache returns: {e}")

    async def _get_analytics_cache(self):
        """
        Retrieve full analytics cache: (portfolio_returns, asset_returns_dict, weights, total_value).
        Returns a 4-tuple on hit, None on miss.
        """
        from app.core.redis_client import get_redis_client
        cache_key = f"portfolio:{self.portfolio_id}:analytics_cache"
        redis_client = await get_redis_client()
        cached = await redis_client.get(cache_key)
        if cached is None:
            return None
        try:
            idx = pd.to_datetime(cached["portfolio_returns"]["index"])
            portfolio_returns = pd.Series(cached["portfolio_returns"]["values"], index=idx, dtype=float)

            asset_returns: Dict[str, pd.Series] = {}
            for ticker, data in cached.get("asset_returns", {}).items():
                a_idx = pd.to_datetime(data["index"])
                asset_returns[ticker] = pd.Series(data["values"], index=a_idx, dtype=float)

            weights = cached.get("weights", {})
            total_value = float(cached["total_value"])
            print(f"[INFO] Analytics cache hit: {len(asset_returns)} assets, value=${total_value:.2f}")
            return portfolio_returns, asset_returns, weights, total_value
        except Exception as e:
            print(f"[WARN] Failed to deserialize analytics cache: {e}")
            return None

    async def _set_analytics_cache(
        self,
        portfolio_returns: pd.Series,
        asset_returns: Dict[str, pd.Series],
        weights: Dict[str, float],
        total_value: float,
    ) -> None:
        """Store full analytics dataset in Redis for 15 minutes."""
        from app.core.redis_client import get_redis_client
        cache_key = f"portfolio:{self.portfolio_id}:analytics_cache"
        redis_client = await get_redis_client()
        try:
            payload = {
                "portfolio_returns": {
                    "values": portfolio_returns.tolist(),
                    "index": [str(i) for i in portfolio_returns.index],
                },
                "asset_returns": {
                    ticker: {
                        "values": series.tolist(),
                        "index": [str(i) for i in series.index],
                    }
                    for ticker, series in asset_returns.items()
                },
                "weights": weights,
                "total_value": total_value,
            }
            await redis_client.set(cache_key, payload, ttl=900)
            print(f"[INFO] Analytics cache populated: {len(asset_returns)} assets")
        except Exception as e:
            print(f"[WARN] Failed to set analytics cache: {e}")

    async def get_current_portfolio_value(self) -> float:
        """Get the current market value of the portfolio."""
        if self._cached_portfolio_value is None:
            await self._build_portfolio()
        return self._cached_portfolio_value or 0.0

    def _compute_metrics_from_returns(
        self,
        portfolio_returns: pd.Series,
        asset_returns_dict: Dict[str, pd.Series],
        weights: Dict[str, float],
        total_value: float,
    ) -> Dict:
        """Compute all portfolio metrics from pre-built returns data (no Portfolio object needed)."""
        def clean_value(value):
            if isinstance(value, (float, np.float64)):
                if np.isnan(value) or np.isinf(value):
                    return None
            return value

        try:
            # Portfolio-level metrics (all use portfolio_returns directly)
            annual_return = float(annualize_rets(portfolio_returns, 252))
            annual_vol = float(annualize_vol(portfolio_returns, 252))
            sharp = float(sharpe_ratio(portfolio_returns, self.risk_free_rate, 252))

            # Sortino ratio
            daily_rf = (1 + self.risk_free_rate) ** (1 / 252) - 1
            downside_returns = portfolio_returns[portfolio_returns < daily_rf]
            if len(downside_returns) > 0:
                downside_std = float(downside_returns.std() * np.sqrt(252))
                sortino = (annual_return - self.risk_free_rate) / downside_std if downside_std > 0 else np.inf
            else:
                sortino = np.inf if annual_return > self.risk_free_rate else 0.0

            # Max drawdown + Calmar
            dd_df = drawdown(portfolio_returns)
            max_dd_val = float(dd_df["Drawdown"].min())
            calmar = annual_return / abs(max_dd_val) if abs(max_dd_val) > 1e-9 else np.inf

            # Risk metrics
            hist_var_95 = float(var_historic(portfolio_returns, level=5))
            hist_var_99 = float(var_historic(portfolio_returns, level=1))
            hist_cvar_95 = float(cvar_historic(portfolio_returns, level=5))
            semi_dev = float(semideviation(portfolio_returns))

            # Individual asset performance
            individual_performance = {}
            if asset_returns_dict:
                returns_df = pd.DataFrame(asset_returns_dict).dropna()
                if not returns_df.empty:
                    for symbol in returns_df.columns:
                        s = returns_df[symbol]
                        if not s.empty:
                            individual_performance[symbol] = {
                                "return": float(annualize_rets(s, 252)),
                                "volatility": float(annualize_vol(s, 252)),
                            }

            concentration_risk = max(weights.values()) if weights else 0.0

            result = {
                "portfolio_return_annualized": clean_value(annual_return),
                "portfolio_volatility_annualized": clean_value(annual_vol),
                "sharpe_ratio": clean_value(sharp),
                "sortino_ratio": clean_value(sortino),
                "value_at_risk_95": clean_value(hist_var_95),
                "value_at_risk_99": clean_value(hist_var_99),
                "cvar": clean_value(hist_cvar_95),
                "semideviation": clean_value(semi_dev),
                "max_drawdown": clean_value(max_dd_val),
                "calmar_ratio": clean_value(calmar),
                "total_portfolio_value": clean_value(total_value),
                "number_of_positions": len(asset_returns_dict),
                "concentration_risk": clean_value(concentration_risk),
                "individual_performance": {
                    sym: {k: clean_value(v) for k, v in m.items()}
                    for sym, m in individual_performance.items()
                },
            }
            print(f"[SUCCESS] Metrics: Return={annual_return:.2%}, Sharpe={sharp:.3f}, VaR95={hist_var_95:.2%}")
            return result
        except Exception as e:
            print(f"[ERROR] Metrics computation failed: {e}")
            import traceback
            traceback.print_exc()
            return {}

    async def calculate_portfolio_metrics(self) -> Dict:
        """Calculate comprehensive portfolio metrics, using analytics cache when available."""
        # Fast path: use analytics cache (populated by any prior analytics call this session)
        cache_result = await self._get_analytics_cache()
        if cache_result is not None:
            portfolio_returns, asset_returns_dict, weights, total_value = cache_result
            portfolio_returns = portfolio_returns.dropna().copy()
            if len(portfolio_returns) >= 50:
                print(f"[INFO] Metrics: using analytics cache ({len(portfolio_returns)} days)")
                return self._compute_metrics_from_returns(
                    portfolio_returns, asset_returns_dict, weights, total_value
                )

        # Slow path: build portfolio from yfinance (populates cache as side effect)
        portfolio = await self._build_portfolio()
        if not portfolio or not portfolio.assets:
            return {}

        portfolio_returns = portfolio.get_portfolio_returns()
        print(f"Metrics: portfolio_returns shape: {portfolio_returns.shape}")

        if portfolio_returns.empty:
            return {}

        portfolio_returns = portfolio_returns.dropna().copy()
        if len(portfolio_returns) < 50:
            print(f"[ERROR] Metrics: insufficient data ({len(portfolio_returns)} days)")
            return {}

        asset_returns_dict = {}
        for symbol, asset in portfolio.assets.items():
            try:
                r = asset.get_returns()
                if not r.empty:
                    asset_returns_dict[symbol] = r
            except Exception:
                pass

        total_value = self._cached_portfolio_value or portfolio.get_total_value()
        weights = dict(portfolio.weights)
        return self._compute_metrics_from_returns(portfolio_returns, asset_returns_dict, weights, total_value)

    async def _compute_efficient_frontier(
        self,
        asset_returns_dict: Dict[str, pd.Series],
        weights_map: Dict[str, float],
    ) -> Dict:
        """Compute efficient frontier from per-asset returns (no Portfolio object needed)."""
        if len(asset_returns_dict) < 2:
            print(f"[ERROR] Efficient Frontier: Need at least 2 assets, have {len(asset_returns_dict)}")
            return {}

        returns_df = pd.DataFrame(asset_returns_dict).dropna()
        if returns_df.empty or len(returns_df) < 50:
            print(f"[ERROR] Efficient Frontier: Insufficient data ({len(returns_df)} days)")
            return {}

        print(f"Efficient Frontier: {len(returns_df)} days, {len(returns_df.columns)} assets")
        try:
            expected_returns = annualize_rets(returns_df, 252)
            cov_matrix = returns_df.cov() * 252

            n_points = 20
            weights_list = optimal_weights(n_points, expected_returns.values, cov_matrix.values)

            frontier_points = []
            for w in weights_list:
                frontier_points.append({
                    "risk": portfolio_vol(w, cov_matrix.values),
                    "return": portfolio_return(w, expected_returns.values),
                })

            msr_w = msr(self.risk_free_rate, expected_returns.values, cov_matrix.values)
            gmv_w = gmv(cov_matrix.values)

            # Current portfolio point — use only assets present in the frontier
            ef_symbols = list(returns_df.columns)
            if weights_map and all(s in weights_map for s in ef_symbols):
                total_w = sum(weights_map[s] for s in ef_symbols)
                cur_weights = np.array([weights_map[s] / total_w for s in ef_symbols])
            else:
                cur_weights = np.ones(len(ef_symbols)) / len(ef_symbols)

            special_portfolios = {
                "current": {
                    "name": "Current Portfolio",
                    "risk": portfolio_vol(cur_weights, cov_matrix.values),
                    "return": portfolio_return(cur_weights, expected_returns.values),
                },
                "msr": {
                    "name": "Max Sharpe Ratio",
                    "risk": portfolio_vol(msr_w, cov_matrix.values),
                    "return": portfolio_return(msr_w, expected_returns.values),
                },
                "gmv": {
                    "name": "Global Minimum Volatility",
                    "risk": portfolio_vol(gmv_w, cov_matrix.values),
                    "return": portfolio_return(gmv_w, expected_returns.values),
                },
            }

            print(f"[SUCCESS] Efficient frontier: {len(frontier_points)} points")
            return {"frontier_points": frontier_points, "special_portfolios": special_portfolios}

        except Exception as e:
            print(f"[ERROR] Efficient frontier failed: {e}")
            import traceback; traceback.print_exc()
            return {}

    async def generate_efficient_frontier(self) -> Dict:
        """Generate the efficient frontier, using analytics cache when available."""
        # Fast path: use analytics cache
        cache_result = await self._get_analytics_cache()
        if cache_result is not None:
            _, asset_returns_dict, weights, _ = cache_result
            if len(asset_returns_dict) >= 2:
                print("[INFO] Efficient Frontier: using analytics cache")
                return await self._compute_efficient_frontier(asset_returns_dict, weights)

        # Slow path: build portfolio
        portfolio = await self._build_portfolio()
        if not portfolio or len(portfolio.assets) < 2:
            print(f"[ERROR] Efficient Frontier: Need at least 2 assets")
            return {}

        asset_returns_dict = {}
        for symbol, asset in portfolio.assets.items():
            try:
                r = asset.get_returns()
                if not r.empty:
                    asset_returns_dict[symbol] = r
            except Exception as e:
                print(f"[WARNING] Efficient Frontier: no returns for {symbol}: {e}")

        return await self._compute_efficient_frontier(asset_returns_dict, dict(portfolio.weights))

    async def run_monte_carlo_simulation(self, scenarios: int = 1000, time_horizon: int = 252) -> Dict:
        """Run a Monte Carlo simulation for the portfolio."""
        # Try cached returns first
        portfolio_returns, total_value = await self._get_cached_returns()

        if portfolio_returns is None:
            portfolio = await self._build_portfolio()
            if not portfolio or not portfolio.assets:
                return {}
            portfolio_returns = portfolio.get_portfolio_returns()
            total_value = self._cached_portfolio_value or portfolio.get_total_value()
            await self._cache_returns(portfolio_returns, total_value)
        else:
            print(f"[INFO] Monte Carlo: Using cached returns ({len(portfolio_returns)} days)")

        if portfolio_returns.empty:
            print("[ERROR] Monte Carlo: Portfolio returns are empty")
            return {}
        
        # Clean the returns data - remove NaN values (like in the demo)
        # .copy() prevents "assignment destination is read-only" in downstream numpy ops.
        initial_length = len(portfolio_returns)
        portfolio_returns = portfolio_returns.dropna().copy()
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
        # Try cached returns to skip expensive yfinance re-fetch
        portfolio_returns, total_value = await self._get_cached_returns()

        if portfolio_returns is None:
            portfolio = await self._build_portfolio()
            if not portfolio or not portfolio.assets:
                print("[ERROR] CPPI: No portfolio or assets")
                return {"error": True, "reason": "No holdings found in portfolio", "multiplier": multiplier, "floor": floor}
            portfolio_returns = portfolio.get_portfolio_returns()
            total_value = self._cached_portfolio_value or portfolio.get_total_value()
            await self._cache_returns(portfolio_returns, total_value)
        else:
            print(f"[INFO] CPPI: Using cached returns ({len(portfolio_returns)} days)")
        print(f"CPPI: portfolio_returns shape: {portfolio_returns.shape}")
        print(f"CPPI: portfolio_returns empty: {portfolio_returns.empty}")
        print(f"CPPI: portfolio_returns has NaN: {portfolio_returns.isnull().any()}")
        
        if portfolio_returns.empty:
            print("[ERROR] CPPI: Portfolio returns are empty")
            return {"error": True, "reason": "No historical price data available for your holdings", "multiplier": multiplier, "floor": floor}
        
        # Clean the returns data - remove NaN values like in the demo
        # .copy() is required: dropna() can return a read-only numpy view which
        # causes "assignment destination is read-only" inside run_cppi().
        initial_length = len(portfolio_returns)
        portfolio_returns = portfolio_returns.dropna().copy()
        final_length = len(portfolio_returns)

        if initial_length != final_length:
            print(f"[WARNING] CPPI: Dropped {initial_length - final_length} NaN values from returns")

        if len(portfolio_returns) < 50:  # Need minimum data for meaningful CPPI
            print(f"[ERROR] CPPI: Insufficient clean data ({len(portfolio_returns)} days)")
            return {"error": True, "reason": f"Insufficient data: only {len(portfolio_returns)} trading days available (need 50+)", "multiplier": multiplier, "floor": floor}
        
        print(f"CPPI: Clean returns count: {len(portfolio_returns)}")
        print(f"CPPI: Returns sample (first 5): {portfolio_returns.head()}")
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
                floor_val = float(cppi_results["floor"].iloc[i].squeeze())
                performance_data.append({
                    "day": i,
                    "cppi_wealth": float(cppi_results["Wealth"].iloc[i, 0]),
                    "buyhold_wealth": float(cppi_results["Risky Wealth"].iloc[i, 0]),
                    "floor_value": float(floor_val),
                    "risky_allocation": float(cppi_results["Risky Allocation"].iloc[i, 0]) * 100,
                    "risk_budget": float(cppi_results["Risk Budget"].iloc[i, 0]) * 100,
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
            return {"error": True, "reason": f"Simulation error: {str(e)}", "multiplier": multiplier, "floor": floor}

    async def sector_analysis(self, display_currency: Optional[str] = None) -> Dict:
        """Analyze portfolio by sector with currency conversion, including cash balance."""
        import logging
        logger = logging.getLogger(__name__)
        from app.services.exchange_rate_service import get_exchange_rate_service
        from app.models.portfolio import Portfolio as PortfolioModel

        result = await self.db.execute(
            select(Holding)
            .where(Holding.portfolio_id == self.portfolio_id)
            .where(Holding.quantity > 0)
            .options(selectinload(Holding.asset))
        )
        holdings = result.scalars().all()

        # Get portfolio to determine base currency and cash balance
        portfolio_result = await self.db.execute(
            select(PortfolioModel).where(PortfolioModel.id == self.portfolio_id)
        )
        portfolio_obj = portfolio_result.scalar_one_or_none()
        
        if not portfolio_obj:
            return {}
            
        if not display_currency:
            display_currency = portfolio_obj.currency

        display_currency = (display_currency or "USD").upper()
        exchange_service = get_exchange_rate_service()

        logger.info(f"[SECTOR_ANALYSIS] Processing {len(holdings)} holdings, display_currency={display_currency}")

        # Pre-fetch exchange rates
        exchange_rates = {}
        currencies_needed = set()
        for holding in holdings:
            if holding.asset:
                currencies_needed.add(holding.asset.currency)
        # Also need portfolio currency for cash balance conversion
        currencies_needed.add(portfolio_obj.currency)

        for currency in currencies_needed:
            if currency != display_currency:
                rate = await exchange_service.get_exchange_rate(currency, display_currency)
                exchange_rates[currency] = rate
                logger.info(f"[SECTOR_ANALYSIS] Exchange rate {currency} -> {display_currency}: {rate}")

        sector_data = {}
        total_value = 0

        # We need to fetch current prices to get market values
        portfolio = await self._build_portfolio()

        for holding in holdings:
            asset_symbol = holding.asset.ticker
            asset_currency = holding.asset.currency
            print(f"[SECTOR_ANALYSIS] Processing {asset_symbol}, asset_type={holding.asset.asset_type}, currency={asset_currency}")

            # Check if asset exists in portfolio (stocks with historical data)
            # For mutual funds and crypto, use holding's current_price from database
            if portfolio and asset_symbol in portfolio.assets:
                asset_obj = portfolio.assets[asset_symbol]
                current_price = asset_obj.get_current_price()
                if current_price is None:
                    continue
            else:
                # For assets not in portfolio (mutual funds, crypto), use database price
                current_price = holding.current_price or holding.average_cost
                if current_price is None:
                    continue

            market_value = holding.quantity * current_price

            # Convert to display currency if different
            if asset_currency != display_currency and asset_currency in exchange_rates:
                rate = exchange_rates[asset_currency]
                original_value = market_value
                market_value = market_value * rate
                logger.info(f"[SECTOR_ANALYSIS] {asset_symbol}: {original_value:.2f} {asset_currency} -> {market_value:.2f} {display_currency} (rate: {rate})")

            # Assign sector based on asset type if not available
            if holding.asset.sector:
                sector = holding.asset.sector
            elif holding.asset.asset_type == 'mutual_fund':
                sector = "Mutual Funds"
            elif holding.asset.asset_type == 'crypto':
                sector = "Cryptocurrency"
            elif holding.asset.asset_type == 'etf':
                sector = "ETF"
            else:
                sector = "Other"

            logger.info(f"[SECTOR_ANALYSIS] {asset_symbol}: qty={holding.quantity}, price={current_price}, market_value={market_value}, sector={sector}")

            if sector not in sector_data:
                sector_data[sector] = {
                    "value": 0,
                    "positions": 0,
                }

            sector_data[sector]["value"] += market_value
            sector_data[sector]["positions"] += 1
            total_value += market_value

        # Add cash balance as a separate "sector"
        cash_balance = portfolio_obj.cash_balance or 0.0
        if cash_balance > 0:
            # Convert cash to display currency if needed
            if portfolio_obj.currency != display_currency and portfolio_obj.currency in exchange_rates:
                rate = exchange_rates[portfolio_obj.currency]
                cash_balance = cash_balance * rate
                logger.info(f"[SECTOR_ANALYSIS] Cash: converted to {cash_balance:.2f} {display_currency} (rate: {rate})")
            
            sector_data["Cash"] = {
                "value": cash_balance,
                "positions": 1,
            }
            total_value += cash_balance
            logger.info(f"[SECTOR_ANALYSIS] Added Cash: {cash_balance:.2f} {display_currency}")

        if total_value > 0:
            for sector in sector_data:
                sector_data[sector]["percentage"] = (
                    sector_data[sector]["value"] / total_value * 100
                )

        logger.info(f"[SECTOR_ANALYSIS] Final result in {display_currency}: total_value={total_value:.2f}")
        return sector_data