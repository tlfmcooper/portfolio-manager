# Performance and validation evidence

Measured October 8, 2026. Build numbers are from Vite production output on the same machine and dependency lockfile. Browser timings are local fixture measurements, not production guarantees.

## Production build comparison

| Initial JavaScript chunk | Before (kB / gzip kB) | After (kB / gzip kB) |
| --- | --- | --- |
| Entry | 43.27 / 12.30 | 43.18 / 12.42 |
| React vendor | 340.85 / 106.59 | 140.15 / 45.24 |
| App vendor | 35.61 / 13.94 | 93.40 / 34.01 |
| **Total initial JS** | **419.73 / 132.83** | **276.73 / 91.67** |

Initial JavaScript is 34.1% smaller uncompressed and 31.0% smaller gzip-compressed. Charts and Markdown load with the sections that require them; the new planning workspace is also separate from the entry. CSS remains approximately 66.7 kB (11.8 kB gzip). The build completes successfully; the existing Browserslist database warning remains. Shared CommonJS helpers stay with React to avoid a circular import through the app vendor chunk. The build also imports the generated React vendor module graph and verifies React initialization, catching runtime failures that source-level unit tests miss. The production preview was verified to render the landing page and login form without console errors.

The deployed public landing page was also inspected before changes: observed TTFB 473 ms, DOMContentLoaded 1,026 ms, load 1,037 ms, with the old 106.6 kB compressed vendor chunk. These are a single remote sample and include network latency. Authenticated production performance was not measured.

## Authenticated local browser evidence

An isolated SQLite portfolio with two synthetic holdings and $200 cash was used. The fixture introduced a two-second historical metrics delay, a 300 ms quote delay, and deterministic FX. No production account or portfolio was modified.

On a cold overview navigation:

| Observation | Time from navigation / request duration |
| --- | --- |
| Portfolio requests start | 121.6 ms |
| Stored-price snapshot response | 7.5 ms, completes at 129.1 ms |
| Snapshot visible (DOM observer) | 130.2 ms |
| Summary response | 16.2 ms |
| Historical metrics response | 2,004.9 ms, completes at 2,126.5 ms |

The previous `Promise.all` flow would have withheld its metric display until the slower response completed. The new snapshot is independently usable while analytics run. This demonstrates removal of the dependency; it does not predict live Yahoo/Barchart/Finnhub latency.

A warm portfolio reload issued no snapshot, allocation, metrics or cash overview request when valid account-session data was available. Auth bootstrap still validates the session. Transaction history also uses the same short-lived session cache. A manual refresh kept the existing snapshot visible and issued a price update followed by one snapshot request (observed 3.7 ms). Historical metrics on the portfolio page remained unloaded until requested.

The browser also verified dark mode and that logout removed the account session cache. The browser verified saved 40% / 40% / 20% holding/cash targets after reload, contribution preview, concentration threshold, export actions, USD/CAD switching (USD 1,040 became CAD 1,456 at the fixture's 1.4 rate), and mobile layout. At a 375 px viewport the document had no horizontal overflow, numeric target inputs were 96 px wide, and the table scrolled within its own region. Quote timestamps were corrected to include UTC offsets before local display.

## Automated checks

- Backend: **74 tests pass** across the full backend suite. Coverage includes authenticated snapshots, currency conversion and unavailable FX, saved targets/invalid plans, ownership, exports including 105 transactions, formula escaping, quote timestamp selection, fallback-cache TTL/bounds/coalescing, invalidation during loading, Redis recovery and nonblocking Yahoo work.
- Frontend: **39 frontend tests pass** in the full suite. All focused planning, cache and snapshot synchronization checks pass. Coverage includes stable cache effects, session persistence/account and currency isolation, failed requests and invalidation races, contribution/cash math, target rounding and validation, concentration coverage, target-saving UI, refresh errors/retry, progressive overview loading, invalidation and immediate snapshot refresh after live quotes or summary completion, Live Market shell and existing auth/buy/chat tool behavior.
- Production build and `git diff --check` pass. The normal lint command cannot run because the repository has no ESLint configuration; an explicit React hook lint check passes for the new cache, snapshot and planning files.
- The baseline complete frontend suite had 12 failures across five landing-page test files with outdated content assertions. Those same 12 failures remain; no new functional regression was observed in the focused checks.

Commands:

```sh
PYTHONPATH=backend:. .venv/bin/python -m pytest backend/tests -q
cd frontend
npm run build
npm test -- --run tests/unit/PortfolioWorkspace.test.jsx tests/unit/DataCacheContext.test.jsx tests/unit/dataCache.test.js tests/unit/portfolioPlanning.test.js tests/unit/usePortfolioSnapshot.test.jsx tests/unit/OverviewSection.test.jsx tests/unit/LiveMarketShell.test.jsx tests/unit/AuthContext.test.jsx tests/unit/BuyAssetForm.test.jsx tests/unit/agentTools.test.js
```

## Real-session navigation follow-up

The original synthetic snapshot test did not establish that page-to-page navigation was fast. A follow-up used the signed-in local browser and the real cluster database through its loopback port-forward.

The PostgreSQL engine used `NullPool`, opening and authenticating a new connection for each API request. Four read-only connection/query/release samples took 4,094, 2,787, 2,603 and 2,564 ms. The application now reuses a bounded pool (five connections plus five overflow connections), validates connections and recycles them. With the actual application configuration, samples were 2,531 ms for the first connection, then 1,134, 1,125 and 1,143 ms. These are database diagnostics, not whole-page timings. `DATABASE_USE_NULL_POOL=true` retains the old connection behavior if an environment specifically requires it. Joining assets into the holdings load also removes one query round trip.

Risk, efficient frontier, Monte Carlo and CPPI now share account-scoped frontend results, including the same metrics key used by Overview. Currency and simulation parameters separate calculations. Pending requests survive a page departure and are reused on return. Previously loaded values remain visible while expired results refresh; analytics indicate that refresh is running. Portfolio mutations invalidate these calculations.

Overview, allocation, cash and transaction sections initialize from their previous account-session data instead of starting empty on every visit. Live Market retains its timestamped quotes and YTD rows during refresh, seeds chart data from known quotes, and warms the snapshot after quote updates. The layout derives its analytics view from the URL before rendering, avoiding a transient mount of the previous view. Charts render without the default entry animations that delayed visible chart data.

| Tested transition | Click to first accessibility observation | Data present in that observation |
| --- | --- | --- |
| Risk to Overview | 652 ms | Snapshot, performance metrics and distribution chart; refresh status visible |
| Overview to Risk | 673 ms | Risk metrics and distribution chart; refresh status visible |
| Settings to Portfolio | 871 ms | Snapshot, planning, cash, sector breakdown and transactions |
| Portfolio to Live Market | 618 ms | Last-loaded quotes and holdings, with their original update timestamp |

These measurements include browser-control overhead and are not precise paint timings or cold-start guarantees. The user had already visited the pages, and some cached values had expired. Browser logs also showed warm live-market requests around 1.67–1.81 seconds, while cold external quote refreshes still took 6.34–6.96 seconds. Keeping previously loaded data visible does not make those external requests instantaneous; quote and snapshot timestamps remain visible while fresh values arrive.

Regression checks cover immediate reuse of Overview metrics in Risk, a pending calculation reused after leaving and returning, currency/parameter isolation, visible stale analytics during refresh, and Overview retaining metrics during revalidation. The backend suite still passes all 74 tests. All 39 passing frontend tests include the new navigation checks; the same 12 baseline landing-page assertion failures remain. Production builds verify the generated React vendor module graph as well as compiling the source.

## Deployment limits

These measurements describe local pre-release validation. Repeat cold/warm timings with a real mixed-asset portfolio after deployment. Redis is the distributed cache; fallback caches are bounded per process, so separate workers do not share fallback invalidation during a Redis outage. Recovery replays this worker's missed invalidations. External price refresh can still take time, but it no longer prevents the snapshot from being displayed. The default API timeout for long simulations is unchanged.
