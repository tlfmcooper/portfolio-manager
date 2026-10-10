# Allocation scenarios

The analytics toolbar on Overview, Portfolio, and the analytics tabs switches between **Use current weights**, **Use MSR weights**, and custom target weights. **Reset all analytics** restores actual portfolio weights and the default simulation settings. What-if scenarios do not change holdings, cash, transactions, or saved allocation targets.

On Portfolio, edit target percentages including CASH. Once valid targets total 100%, they apply after a 500 ms pause. Risk metrics, sector allocation, the selected efficient-frontier marker, Monte Carlo, and CPPI use the same scenario. Invalid drafts retain the last valid calculation. **Use saved targets** loads an existing plan; **Save targets** remains an explicit, separate database operation. Planned contributions affect the rebalancing preview only.

MSR is a long-only maximum-Sharpe allocation over holdings with sufficient common history. It preserves current cash and any holdings lacking history. All analytics disclose coverage and the common observation window. Missing holdings are not silently assigned invented returns: simulations model only the covered capital. Fund NAV data is price history and excludes distributions; it is labeled separately from Yahoo adjusted closes. Historical FX conversion is applied before combining mixed-currency returns. Cash earns zero in the allocation model; CPPI uses a separate safe asset at the existing 4.2% annual risk-free assumption, converted to a daily rate.

Scenario weights remain active across dashboard navigation. Reload, logout, account changes, or holdings updates restore actual weights. Account balances and transaction-based YTD always represent actual activity. Monte Carlo uses common seeded draws for consistent comparisons, and CPPI respects its selected historical horizon.

Portfolio Pilot can read allocation context, propose an editable comparison card, switch weights, and reset the scenario. The MCP `analytics_preview_scenario` tool returns the same calculations with native app UI metadata. Trusted, initialized host tool results can display a proposal in the app; applying a proposal updates what-if state only. These use the existing React/FastAPI integrations without adding another agent runtime. Portfolio Pilot completes up to four structured function-call rounds and preserves call IDs. Its model can be overridden with `VITE_GEMINI_MODEL`; the default is `gemini-3.8-flash`, listed in the [Google model catalog](https://ai.google.dev/gemini-api/docs/models).

## API

`POST /api/v1/analysis/portfolios/{portfolio_id}/scenario` requires portfolio ownership. It accepts `preset` (`current`, `msr`, `custom`), the selected USD/CAD `currency`, `kind` (an existing analysis kind or `all`), and simulation parameters. Custom percentages are supplied as `"weights": {"weights": {"AAPL": 80, "CASH": 20}}`; they must be finite, long-only, sum to 100%, and use owned holding tickers. `cppi_time_horizon` allows combined results to keep CPPI's horizon independent of Monte Carlo. Maximum Monte Carlo work is 2,520,000 scenario-days.

Single analyses preserve existing response fields and add `analysis_context` (except the sector dictionary, whose existing shape remains unchanged). Combined responses include `analysis_context`, `analytics`, and `baseline_metrics`; unavailable calculations have a per-analysis error. Context includes resolved and actual percentages, coverage, historical sources, currency, portfolio and modeled values, and dataset revision. Existing GET endpoints use the same engine for actual weights.

## Validation

- Isolated database/API tests cover recalculation, cash and currency handling, ownership, invalid input, deterministic comparisons, missing history, and daily CPPI rates.
- Frontend tests cover debouncing, cache separation, reset, discarded late MSR responses, account changes, agent cards, and the trusted MCP bridge.
- Live read-only cluster validation on October 10, 2026: all 16 holdings covered, 490 common observations, no analysis errors. PHN9756.CF, PHN9757.CF, and RBF274.CF each supplied 505 daily NAV closes; BTC supplied 730 daily closes.
- A local process against cluster PostgreSQL took 4.165 seconds for a cold complete calculation, 0.937 seconds for first MSR, and about 0.73 seconds for repeated complete current/MSR requests. These are backend timings, not browser navigation timings.
- Historical datasets, optimizer bases, and scenario results are cached and requests are coalesced. Frontend what-if variants are bounded in memory and excluded from session-storage serialization. The cache schema advances to v2 so old analytics are not reused.
