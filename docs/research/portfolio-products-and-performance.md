# Portfolio product research and performance improvements

Research date: October 8, 2026. Sources were read in gstack browse. This is a comparison of published product capabilities, not a hands-on test of competitors' paid accounts. The application's source, baseline production build, existing tests and public deployed landing page were also inspected. Authenticated production timings were not available; local authenticated verification uses an isolated test account and deterministic market providers.

## Comparison of comparable products

| Product and primary source | Relevant published capabilities | Implication for this app |
| --- | --- | --- |
| [Sharesight](https://www.sharesight.com/ca/portfolio-tracker/) | Performance and tax reporting, broker/spreadsheet ingestion, dividends and corporate actions, benchmarks, currency impacts, Canadian mutual funds | Accurate returns require income and corporate-action records. CSV onboarding already exists here, but complete export was missing. |
| [Portfolio Performance](https://www.portfolio-performance.info/en/) | Time-weighted return and IRR, transaction history including fees/taxes, configurable allocation, rebalancing, CSV/JSON export | This app has advanced simulations but lacks an actionable, saved target allocation workflow. |
| [Portfolio Performance rebalancing manual](https://help.portfolio-performance.info/en/getting-started/rebalancing/) | Target allocations, differences in monetary amounts and shares, explicit fractional-share limitations | Add amount and approximate-unit previews, with cash and rounding accounted for. |
| [Ghostfolio official repository](https://github.com/ghostfolio/ghostfolio) | Multi-account tracking, static portfolio risk analysis, transaction import/export, return periods, dividends, mobile PWA | Add concentration review and portable transaction data before expanding speculative analytics. |
| [Snowball Analytics](https://snowball-analytics.com/) | Rebalancing, benchmarks, dividend calendar/forecasts, fund look-through diversification, broker integrations | Drift visibility is immediately useful; fund overlap and dividend forecasts need additional reliable datasets. |
| [Kubera](https://www.kubera.com/) | Broad wealth aggregation, cash management, daily snapshots, currencies, scenarios and sharing | Make a usable valuation available immediately, and disclose freshness separately from page refresh time. |

Delta was also attempted, but its site returned a Cloudflare 403, so its features were excluded from conclusions. No competitor code was copied.

## Existing capabilities and missing features

The app already supports holdings CSV onboarding, manual buy/sell/cash transactions, USD/CAD display, sector allocation, risk ratios, efficient frontier, Monte Carlo, CPPI, AI chat, MCP and a PWA. Reimplementing these would not add useful scope. The Holding model already contains `target_allocation`, but no complete saved-target/rebalancing interface existed.

| Gap | Value / implementation cost | Decision |
| --- | --- | --- |
| Saved allocation and cash targets | High / medium | Implemented using existing holding fields; no schema migration. |
| Rebalancing with planned new cash | High / medium | Implemented as a preview with buy/sell amounts, approximate units and configurable drift band. No orders are executed. |
| Concentration review | High / low | Implemented configurable holding threshold and missing-sector disclosure. Does not claim fund look-through coverage. |
| Complete holdings and transaction CSV export | High / low | Implemented authenticated export including cash, currencies, timestamps and formula-safe text; transactions are not limited to the UI's first page. |
| Fast valuation and clear freshness | High / medium | Implemented stored-price snapshot, quote timestamps, explicit cost-based estimates, retry and refresh. |
| Dividends, fees, taxes and corporate actions | High / high | Follow-on: the transaction enum currently contains only BUY, SELL, DEPOSIT and WITHDRAWAL. Add ledger events and migrations before claiming total returns or tax correctness. |
| Cash-flow-correct benchmarks / period chart | High / high | Follow-on: use the existing period-input service, persist dated FX and complete income events, disclose history coverage, then compare matching dates/currencies and return methods. Current analytics omit unsupported history for some crypto/funds. |
| Multiple accounts and broker synchronization | High / high | Follow-on: requires changing the one-portfolio-per-user constraint, connector contracts, duplicate detection and import reconciliation. |
| Fund overlap and look-through exposure | Medium / high | Follow-on: acquire constituent data with coverage dates before measuring combined exposures. |
| Price/dividend notifications and watchlists | Medium / medium | Follow-on: requires user preferences and reliable background quote polling. Avoid adding foreground polling to every page. |
| Tax lots / jurisdiction-specific reporting | Medium / high | Follow-on after a complete ledger; Canadian and US rules need dedicated designs and validation. |

Priority is inferred from repeated competitor capabilities and the source audit, not from user interviews. The implemented scope improves daily portfolio decisions without depending on additional subscriptions or unrecorded financial events.

## Performance diagnosis and changes

1. **Unstable frontend cache callbacks.** Cache was React state, so each write changed `getFromCache` and `fetchWithCache`, retriggering dependent loading effects. It is now a stable, account-scoped cache with request coalescing, explicit invalidation and rejection handling. Session storage permits warm browser refreshes; logout clears it and late requests cannot restore invalidated entries.
2. **Overview blocked by the slower of summary/history.** `Promise.all` withheld every metric until both responses completed. They now render independently; a fast stored-price snapshot appears separately. Historical metrics on the portfolio page load only when requested.
3. **Blocking Yahoo work on the event loop.** Several async service methods still executed synchronous `Ticker.info` / `history` directly, preventing unrelated requests from progressing. Those operations now run in worker threads, including ticker-performance history.
4. **Redis outage erased the caching layer.** Added bounded, per-process fallback caching with expiry and same-key request coalescing. Redis remains the distributed cache when available. Connection and command timeouts are bounded. The fallback is per worker and is not cross-instance invalidation.
5. **Incorrect cache scope and mutation invalidation.** Analytics/returns now include display currency. Holdings, asset trades and cash changes invalidate all portfolio cache variants. Analytics HTTP routes check account ownership before consulting cached data. Summary/YTD results use a short full-response cache.
6. **Refresh could reread the same quote response.** Explicit price refresh invalidates current quote and portfolio response caches. Finnhub quote caching is 60 seconds instead of 15 minutes, and refreshed stock prices are persisted for snapshots. Live Market polling skips hidden tabs and pending requests, cancels obsolete requests, and uses the account-scoped cache.
7. **Initial bundle included unrelated libraries.** `id.includes('react')` matched `recharts`, `react-markdown` and `lucide-react`, grouping them into the initial vendor chunk. Exact React package matching separates chart and Markdown dependencies. This follows [Chrome's guidance on React code splitting](https://web.dev/articles/code-splitting-suspense).

## Financial behavior and limits

- Valuation uses active positive-quantity holdings plus portfolio cash. Missing prices use cost basis and are disclosed. Snapshot generation time is distinct from quote age.
- Mixed-currency snapshots require a valid FX rate and fail explicitly when it is unavailable; they never invent parity. Cold FX calls have a four-second budget.
- Targets include cash and total 100%. Unknown holdings, negative percentages and nonfinite targets are rejected. Targets belong to the signed-in account.
- Planned contributions change the preview denominator and available cash only. They do not create deposits. Sales can fund purchases. Preview units assume fractional trading; costs and trading restrictions are excluded.
- Rebalancing is per holding. Fund constituents, leverage, derivatives, tax lots and order execution are outside this scope.
- Stored and cached data accelerate rendering; they do not establish that prices are real time.
- The application's pre-existing landing-page tests contain outdated copy expectations; baseline failures are recorded separately from the new regression checks.

## Verification and measurements

Results are recorded in [performance-validation.md](performance-validation.md). Suggested deployment checks: inspect Redis health, repeat authenticated navigation with a real mixed-asset portfolio, measure cold and warm API timings separately, and check that an actual trade updates valuation and currency-specific analytics.
