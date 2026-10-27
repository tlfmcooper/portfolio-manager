"""Portfolio analytics using the shared, currency-aware historical dataset."""
import numpy as np
import pandas as pd
from typing import Dict
from portfolio_manager.analytics import annualize_rets, annualize_vol, sharpe_ratio, semideviation, var_historic, cvar_historic


class AdvancedPortfolioAnalytics:
    def __init__(self, portfolio_id, db, display_currency=None):
        self.portfolio_id = portfolio_id
        self.db = db
        self.display_currency = display_currency
        self.risk_free_rate = 0.042

    def _service(self):
        from app.services.portfolio_scenarios import PortfolioScenarioService
        return PortfolioScenarioService(self.portfolio_id, self.db, self.display_currency)

    async def calculate_portfolio_metrics(self):
        return await self._service().analyze("metrics")

    async def generate_efficient_frontier(self):
        return await self._service().analyze("efficient-frontier")

    async def run_monte_carlo_simulation(self, scenarios=1000, time_horizon=252):
        return await self._service().analyze("monte-carlo", scenarios=scenarios, time_horizon=time_horizon)

    async def run_cppi_simulation(self, multiplier=3, floor=0.8, time_horizon=252):
        return await self._service().analyze("cppi", multiplier=multiplier, floor=floor, time_horizon=time_horizon)

    async def sector_analysis(self, display_currency=None):
        from app.services.portfolio_scenarios import PortfolioScenarioService
        return await PortfolioScenarioService(self.portfolio_id, self.db, display_currency or self.display_currency).analyze("sector-allocation")

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
            # Target semideviation includes zero shortfalls on days above target.
            # Standard deviation of losing days incorrectly treats equal losses as no risk.
            shortfalls = (portfolio_returns - daily_rf).clip(upper=0)
            downside_std = float(np.sqrt((shortfalls ** 2).mean() * 252))
            sortino = (annual_return - self.risk_free_rate) / downside_std if downside_std > 0 else np.inf

            # Max drawdown + Calmar
            wealth = (1 + portfolio_returns).cumprod()
            # Starting capital is a peak even if the first observed return is negative.
            peaks = wealth.cummax().clip(lower=1.0)
            max_dd_val = float((wealth / peaks - 1).min())
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

            concentration_risk = max((weight for ticker, weight in weights.items() if ticker != "CASH"), default=0.0)

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
