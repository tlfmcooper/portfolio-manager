"""Shared historical dataset and pure, read-only allocation scenario calculations."""
import asyncio
import hashlib
import json
from datetime import date, timedelta

import numpy as np
import pandas as pd
from fastapi import HTTPException
from scipy.optimize import minimize

from app.core.redis_client import get_redis_client
from app.crud.portfolio import get_portfolio
from app.services.finance_service import FinanceService
from app.services.portfolio_snapshot import build_portfolio_snapshot
from portfolio_manager import YFinanceProvider
from portfolio_manager.analytics import annualize_rets, annualize_vol, run_cppi

RISK_FREE_RATE = 0.042
MIN_OBSERVATIONS = 50


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()[:24]


def price_series(points):
    series = pd.Series({str(day)[:10]: float(value) for day, value in points}, dtype=float)
    series.index = pd.to_datetime(series.index)
    return series.sort_index().replace([np.inf, -np.inf], np.nan).where(lambda s: s > 0).dropna()


async def historical_prices(ticker, asset_type):
    """Reuse the existing fund feed; Yahoo supplies adjusted stocks, crypto and FX."""
    cache = await get_redis_client()
    end = date.today()
    start = end - timedelta(days=730)
    key = f"market:scenario-history:v1:{ticker}:{asset_type}:{end}"

    async def load():
        try:
            if asset_type == "mutual_fund" or ticker.upper().endswith(".CF"):
                rows = await FinanceService._get_mutual_fund_history(ticker, start_date=start, end_date=end)
                points = [(row["raw"]["tradeTime"], row["raw"]["lastPrice"]) for row in (rows or [])]
                source, basis = "Barchart daily fund NAV", "price_only"
            else:
                symbol = ticker
                if asset_type in {"crypto", "cryptocurrency"} and "-" not in symbol:
                    symbol = f"{symbol.upper()}-USD"
                frame = await asyncio.to_thread(YFinanceProvider().get_price_data, symbol, start, end)
                points = [(str(day.date()), float(value)) for day, value in frame["Close"].items()]
                source, basis = "Yahoo adjusted close", "adjusted_close"
            clean = price_series(points)
            return {"points": [(str(day.date()), value) for day, value in clean.items()], "source": source, "basis": basis}
        except Exception:
            # Do not expose upstream errors or silently manufacture return history.
            return {"points": [], "source": "unavailable", "basis": "unavailable"}

    result = await cache.get_or_load(key, load, 21600)
    if not result["points"]:
        # A provider outage must recover before the six-hour successful-history TTL.
        await cache.set(key, result, ttl=60)
    return result


async def build_dataset(snapshot):
    semaphore = asyncio.Semaphore(4)
    histories = {}
    fx_pairs = {h["asset_currency"] for h in snapshot["holdings"] if h["asset_currency"] != snapshot["currency"]}

    async def history(ticker, kind):
        async with semaphore:
            return await historical_prices(ticker, kind)

    sources = [(h["ticker"], h["asset_type"]) for h in snapshot["holdings"]]
    sources += [(f"{source}{snapshot['currency']}=X", "fx") for source in sorted(fx_pairs)]
    fetched = await asyncio.gather(*(history(ticker, kind) for ticker, kind in sources))
    histories.update({ticker: payload for (ticker, _), payload in zip(sources, fetched)})
    prices_by_ticker, coverage = {}, []
    for holding in snapshot["holdings"]:
        ticker = holding["ticker"]
        payload = histories[ticker]
        prices = price_series(payload["points"])
        reason = None
        if holding["asset_currency"] != snapshot["currency"]:
            fx = price_series(histories[f"{holding['asset_currency']}{snapshot['currency']}=X"]["points"])
            # Only carry a known FX quote across at most five holidays/weekend days.
            if fx.empty:
                prices = prices.iloc[:0]
                reason = "Historical currency conversion unavailable"
            else:
                union = fx.index.union(prices.index).sort_values()
                converted = fx.reindex(union).ffill(limit=5).reindex(prices.index)
                prices = prices * converted
        # Crypto trades weekends; all assets are compared on a common weekday calendar.
        prices = prices.loc[prices.index.dayofweek < 5]
        values = prices.pct_change(fill_method=None).replace([np.inf, -np.inf], np.nan).dropna()
        available = len(values) >= MIN_OBSERVATIONS
        if available:
            prices_by_ticker[ticker] = prices
        coverage.append({"ticker": ticker, "available": available, "observations": len(values),
                         "source": payload["source"], "return_basis": payload["basis"],
                         "reason": None if available else reason or "Fewer than 50 valid historical returns"})
    # Align closes first: US/Canadian holidays must not pair a two-day stock
    # return with a one-day fund return in the same covariance observation.
    frame = pd.DataFrame(prices_by_ticker).dropna().pct_change(fill_method=None).dropna()
    if not prices_by_ticker:
        frame = pd.DataFrame(index=pd.bdate_range(end=date.today(), periods=252))
    return {"dates": [str(day.date()) for day in frame.index],
            "returns": {ticker: frame[ticker].tolist() for ticker in frame.columns}, "coverage": coverage}


def checked_msr(frame):
    """Reject failed, singular or invalid optimizations rather than using unchecked weights."""
    if frame.empty or len(frame) < MIN_OBSERVATIONS or not len(frame.columns):
        raise HTTPException(422, "MSR requires at least 50 common observations for eligible holdings")
    er = annualize_rets(frame, 252).to_numpy()
    cov = frame.cov().to_numpy() * 252
    if not np.isfinite(er).all() or not np.isfinite(cov).all():
        raise HTTPException(422, "Historical returns are not suitable for optimization")
    n = len(er)

    def objective(weights):
        volatility = np.sqrt(max(float(weights @ cov @ weights), 0))
        return -(float(weights @ er) - RISK_FREE_RATE) / max(volatility, 1e-12)

    result = minimize(objective, np.repeat(1 / n, n), method="SLSQP", bounds=[(0, 1)] * n,
                      constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1}], options={"maxiter": 500})
    if not result.success or not np.isfinite(result.x).all() or abs(result.x.sum() - 1) > 1e-6:
        raise HTTPException(422, "MSR optimization did not converge; current weights remain available")
    weights = np.clip(result.x, 0, 1)
    return dict(zip(frame.columns, (weights / weights.sum()).tolist()))


class PortfolioScenarioService:
    def __init__(self, portfolio_id, db, currency=None):
        self.portfolio_id, self.db, self.currency = portfolio_id, db, currency

    async def prepare(self, include_history=True):
        portfolio = await get_portfolio(self.db, self.portfolio_id)
        if portfolio is None:
            raise HTTPException(404, "Portfolio not found")
        try:
            self.snapshot = await build_portfolio_snapshot(portfolio, self.currency or portfolio.currency)
        except (ValueError, TimeoutError):
            raise HTTPException(503, "Currency conversion is temporarily unavailable")
        if self.snapshot["total_value"] <= 0 or self.snapshot["cash_balance"] < 0:
            raise HTTPException(422, "Analytics require positive portfolio value and nonnegative cash")
        revision = {"currency": self.snapshot["currency"], "cash": self.snapshot["cash_balance"],
                    "holdings": [(h["ticker"], h["market_value"], h["asset_type"], h["asset_currency"]) for h in self.snapshot["holdings"]],
                    "date": str(date.today())}
        self.revision = fingerprint(revision)
        cache = await get_redis_client()
        self.dataset = await cache.get_or_load(f"portfolio:{self.portfolio_id}:dataset:v3:{self.revision}",
                                              lambda: build_dataset(self.snapshot), 900) if include_history else {"returns": {}, "dates": [], "coverage": []}
        self.frame = pd.DataFrame(self.dataset["returns"], index=pd.to_datetime(self.dataset["dates"]))
        self.frame = self.frame.reindex(sorted(self.frame.columns), axis=1)
        self.actual = {h["ticker"]: h["market_value"] / self.snapshot["total_value"] for h in self.snapshot["holdings"]}
        self.actual["CASH"] = self.snapshot["cash_balance"] / self.snapshot["total_value"]
        return self

    def resolve_weights(self, preset, weights=None):
        if preset == "current":
            return dict(self.actual)
        if preset == "custom":
            if set(weights) - set(self.actual):
                raise HTTPException(422, "Targets contain holdings outside this portfolio")
            return {ticker: weights.get(ticker, 0) / 100 for ticker in self.actual}
        eligible = list(self.frame.columns)
        budget = sum(self.actual[ticker] for ticker in eligible)
        optimized = getattr(self, "optimized", None) or checked_msr(self.frame)
        return {ticker: optimized[ticker] * budget if ticker in optimized else value for ticker, value in self.actual.items()}

    def metadata(self, weights, preset):
        covered = sum(weights.get(ticker, 0) for ticker in self.frame.columns) + weights.get("CASH", 0)
        coverage = [{**row, "weight_percentage": weights.get(row["ticker"], 0) * 100} for row in self.dataset["coverage"]]
        return {"portfolio_id": self.portfolio_id, "preset": preset, "weights": {ticker: weight * 100 for ticker, weight in weights.items()},
                "actual_weights": {ticker: weight * 100 for ticker, weight in self.actual.items()},
                "currency": self.snapshot["currency"], "portfolio_total_value": self.snapshot["total_value"],
                "modeled_value": self.snapshot["total_value"] * covered, "coverage_percentage": covered * 100,
                "holdings": coverage, "observations": len(self.frame), "dataset_revision": self.revision,
                "history_start": self.dataset["dates"][0] if self.dataset["dates"] else None,
                "history_end": self.dataset["dates"][-1] if self.dataset["dates"] else None,
                "risk_free_rate": RISK_FREE_RATE,
                "notes": ["Constant-weight historical what-if; actual trades and account performance are unchanged.",
                          "Cash earns 0% in the allocation model. CPPI's separate safe asset uses the stated risk-free rate."]
                         + (["Fund NAV returns exclude distributions; these are price returns, not total returns."]
                            if any(row["return_basis"] == "price_only" and row["weight_percentage"] > 0 for row in coverage) else [])}

    def compute(self, kind, weights, preset, params):
        meta = self.metadata(weights, preset)
        if kind == "sector-allocation":
            allocation = {}
            for holding in self.snapshot["holdings"] + [{"ticker": "CASH", "sector": "Cash"}]:
                sector = holding["sector"]
                row = allocation.setdefault(sector, {"percentage": 0, "value": 0})
                row["percentage"] += weights[holding["ticker"]] * 100
                row["value"] += weights[holding["ticker"]] * self.snapshot["total_value"]
            return allocation
        if len(self.frame) < MIN_OBSERVATIONS or meta["coverage_percentage"] <= 0:
            raise HTTPException(422, "At least 50 common historical observations are required; see data coverage")
        covered = meta["coverage_percentage"] / 100
        risky = sum((self.frame[ticker] * weights.get(ticker, 0) for ticker in self.frame.columns),
                    pd.Series(0., index=self.frame.index)) / covered
        capital = meta["modeled_value"]
        if kind == "metrics":
            from app.services.portfolio_analysis import AdvancedPortfolioAnalytics
            engine = AdvancedPortfolioAnalytics(self.portfolio_id, self.db, self.currency)
            result = engine._compute_metrics_from_returns(risky, self.frame.to_dict("series"), weights, self.snapshot["total_value"])
        elif kind == "efficient-frontier":
            result = self.frontier(weights, covered)
        elif kind == "monte-carlo":
            horizon, scenarios = params.get("time_horizon", 252), params.get("scenarios", 1000)
            # Common random numbers make comparisons attributable to weight changes.
            rng = np.random.default_rng(42)
            log_returns = np.log1p(risky)
            daily_drift, daily_volatility = float(log_returns.mean()), float(log_returns.std())
            shocks = rng.standard_normal((horizon, scenarios))
            with np.errstate(over="ignore", invalid="ignore"):
                growth = np.exp(daily_drift + daily_volatility * shocks)
                paths = np.vstack([np.full(scenarios, capital), capital * np.cumprod(growth, axis=0)])
            if not np.isfinite(paths).all():
                raise HTTPException(422, "Simulation exceeds numeric limits; shorten its horizon")
            final = paths[-1]
            hist, edges = np.histogram(final, bins=20)
            result = {"scenarios": scenarios, "time_horizon": horizon, "seed": 42, "initial_value": capital,
                      "final_mean": float(final.mean()), "final_std": float(final.std()),
                      "percentile_5": float(np.percentile(final, 5)), "percentile_95": float(np.percentile(final, 95)),
                      "success_probability": float((final > capital).mean()),
                      "simulation_paths": [{"day": i, "mean_path": float(values.mean()),
                                            **{f"path_{j+1}": float(values[j]) for j in range(min(5, scenarios))}}
                                           for i, values in enumerate(paths)],
                      "final_distribution": [{"range": f"{edges[i]:.0f}-{edges[i+1]:.0f}", "count": int(count),
                                              "percentage": float(count) / scenarios * 100} for i, count in enumerate(hist)]}
        elif kind == "cppi":
            horizon = min(params.get("cppi_time_horizon") or params.get("time_horizon", 252), len(risky))
            multiplier, floor = params.get("multiplier", 3), params.get("floor", .8)
            sample = risky.tail(horizon).copy()
            safe = pd.Series((1 + RISK_FREE_RATE) ** (1 / 252) - 1, index=sample.index)
            simulation = run_cppi(sample, safe_r=safe, m=multiplier, start=capital, floor=floor, riskfree_rate=RISK_FREE_RATE)
            wealth, buyhold = simulation["Wealth"].iloc[:, 0], simulation["Risky Wealth"].iloc[:, 0]
            result = {"multiplier": multiplier, "floor": floor, "time_horizon": horizon, "initial_value": capital,
                      "final_cppi_value": float(wealth.iloc[-1]), "final_buyhold_value": float(buyhold.iloc[-1]),
                      "outperformance": float(wealth.iloc[-1] / buyhold.iloc[-1] - 1),
                      "performance_data": [{"day": i, "date": str(sample.index[i].date()), "cppi_wealth": float(wealth.iloc[i]),
                                            "buyhold_wealth": float(buyhold.iloc[i]), "floor_value": float(simulation["floor"].iloc[i, 0]),
                                            "risky_allocation": float(simulation["Risky Allocation"].iloc[i, 0]) * 100,
                                            "risk_budget": float(simulation["Risk Budget"].iloc[i, 0]) * 100} for i in range(horizon)],
                      "drawdown_data": [{"day": i, "cppi_drawdown": float((wealth / wealth.cummax() - 1).iloc[i]) * 100,
                                         "buyhold_drawdown": float((buyhold / buyhold.cummax() - 1).iloc[i]) * 100} for i in range(horizon)]}
        else:
            raise HTTPException(422, "Unknown analytics kind")
        return {**result, "analysis_context": meta}

    def frontier_basis(self):
        if not len(self.frame.columns):
            return None
        er = annualize_rets(self.frame, 252).to_numpy()
        cov = self.frame.cov().to_numpy() * 252
        symbols = list(self.frame.columns)
        msr = checked_msr(self.frame)
        def minimum_variance(target=None):
            n = len(symbols)
            constraints = [{"type": "eq", "fun": lambda vector: vector.sum() - 1}]
            if target is not None:
                constraints.append({"type": "eq", "fun": lambda vector: vector @ er - target})
            solution = minimize(lambda vector: vector @ cov @ vector, np.repeat(1 / n, n),
                                method="SLSQP", bounds=[(0, 1)] * n, constraints=constraints)
            if not solution.success or not np.isfinite(solution.x).all() or abs(solution.x.sum() - 1) > 1e-6:
                raise HTTPException(422, "Efficient-frontier optimization did not converge")
            return solution.x

        vectors = [minimum_variance(target) for target in np.linspace(er.min(), er.max(), 20)] if len(symbols) > 1 and np.ptp(er) > 1e-9 else [minimum_variance()]
        return {"vectors": [vector.tolist() for vector in vectors], "msr": [msr[ticker] for ticker in symbols],
                "gmv": minimum_variance().tolist()}

    def frontier(self, weights, covered):
        if not len(self.frame.columns):
            return {"frontier_points": [], "special_portfolios": {}}
        basis = getattr(self, "frontier_base", None) or self.frontier_basis()
        er = annualize_rets(self.frame, 252).to_numpy()
        cov = self.frame.cov().to_numpy() * 252
        symbols = list(self.frame.columns)
        budget = sum(weights[ticker] for ticker in symbols) / covered

        def point(vector, name):
            return {"name": name, "risk": float(np.sqrt(max(vector @ cov @ vector, 0))), "return": float(vector @ er)}

        actual_covered = sum(self.actual[ticker] for ticker in symbols) + self.actual["CASH"]
        actual = np.array([self.actual[ticker] / actual_covered for ticker in symbols]) if actual_covered else np.zeros(len(symbols))
        selected = np.array([weights[ticker] / covered for ticker in symbols])
        return {"frontier_points": [point(np.asarray(vector) * budget, "Efficient frontier") for vector in basis["vectors"]],
                "special_portfolios": {"current": point(actual, "Actual weights"), "selected": point(selected, "Selected weights"),
                                       "msr": point(np.array(basis["msr"]) * budget, "Max Sharpe Ratio"),
                                       "gmv": point(np.array(basis["gmv"]) * budget, "Global Minimum Volatility")}}

    async def analyze(self, kind, preset="current", weights=None, **params):
        await self.prepare(include_history=kind != "sector-allocation" or preset == "msr")
        if params.get("scenarios", 1000) * params.get("time_horizon", 252) > 2520000:
            raise HTTPException(422, "Use at most 2,520,000 Monte Carlo scenario-days per calculation")
        cache = await get_redis_client()
        history_id = fingerprint([self.dataset["dates"], self.dataset["returns"]])
        if preset == "msr":
            async def optimize():
                return await asyncio.to_thread(checked_msr, self.frame)
            self.optimized = await cache.get_or_load(f"market:scenario-msr:v1:{history_id}", optimize, 900)
        if kind in {"all", "efficient-frontier"} and len(self.frame) >= MIN_OBSERVATIONS:
            async def frontier_basis():
                return await asyncio.to_thread(self.frontier_basis)
            try:
                self.frontier_base = await cache.get_or_load(f"market:scenario-frontier:v1:{history_id}", frontier_basis, 900)
            except HTTPException:
                # Other analyses remain usable if one optimization is unavailable.
                if kind != "all":
                    raise
        resolved = await asyncio.to_thread(self.resolve_weights, preset, weights)
        key = f"portfolio:{self.portfolio_id}:scenario:v3:{fingerprint([self.revision, self.dataset, resolved, preset, kind, params])}"

        async def calculate():
            if kind == "all":
                def bundle():
                    outputs = {}
                    for item in ["metrics", "sector-allocation", "efficient-frontier", "monte-carlo", "cppi"]:
                        try:
                            outputs[item] = self.compute(item, resolved, preset, params)
                        except HTTPException as exc:
                            outputs[item] = {"error": exc.detail}
                    try:
                        baseline = self.compute("metrics", self.actual, "current", params)
                    except HTTPException as exc:
                        baseline = {"error": exc.detail}
                    return {"analysis_context": self.metadata(resolved, preset), "analytics": outputs, "baseline_metrics": baseline}
                return await asyncio.to_thread(bundle)
            return await asyncio.to_thread(self.compute, kind, resolved, preset, params)

        return await cache.get_or_load(key, calculate, 600)
