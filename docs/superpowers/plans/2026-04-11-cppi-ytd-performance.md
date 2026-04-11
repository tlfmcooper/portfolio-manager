# CPPI Fix, YTD Column & Performance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix CPPI empty charts, add YTD column to Live Market table, and improve app performance via caching and reduced cold-start time.

**Architecture:** Three independent fixes in the same codebase — backend error handling + new endpoint, frontend column addition + error state, and Redis TTL tuning with a shared portfolio-returns cache to cut analytics cold-start from ~10s to <1s on repeat visits.

**Tech Stack:** FastAPI + Python 3.11, React 18 + Vite, Redis (via `app.core.redis_client.RedisClient`), `FinanceService.calculate_ticker_performance()` (already exists in `finance_service.py:457`), `Skeleton`/`MiniCardSkeleton`/`ChartSkeleton` (already exist in `frontend/src/components/ui/Skeleton.jsx`).

---

## File Map

| File | Action | What changes |
|------|--------|-------------|
| `backend/app/services/portfolio_analysis.py` | Modify | Fix floor Series/DataFrame, structured errors, returns Redis cache |
| `backend/app/api/v1/market.py` | Modify | Add `/market/ytd` route; extend quote TTL 300→900 |
| `backend/app/api/v1/holdings.py` | Modify | Extend holdings cache TTL 300→600 |
| `frontend/src/components/CPPISection.jsx` | Modify | Remove hardcoded defaults, add error + skeleton state |
| `frontend/src/pages/LiveMarket.jsx` | Modify | YTD parallel fetch, YTD column + sort, mobile card row |

> Note: `Analytics.jsx` already uses `React.lazy()` + conditional rendering `{activeTab === 'cppi' && <CPPISection />}` — analytics tabs are already lazy-loaded. No change needed.

---

## Task 1: Fix CPPI Backend — Structured Errors + Floor Access

**Files:**
- Modify: `backend/app/services/portfolio_analysis.py:563-665`

- [ ] **Step 1.1: Fix the `floor` Series/DataFrame access (line ~621)**

  The crash occurs because `cppi_results["floor"]` may be a pandas `Series` (1D) when accessed with `.iloc[i, 0]`, which requires a 2D DataFrame. Replace the performance_data loop body:

  ```python
  # In run_cppi_simulation(), replace the performance_data loop (lines ~616-624):
  performance_data = []
  for i in range(len(cppi_results["Wealth"])):
      floor_series = cppi_results["floor"]
      floor_val = floor_series.iloc[i] if isinstance(floor_series, pd.Series) else floor_series.iloc[i, 0]
      performance_data.append({
          "day": i,
          "cppi_wealth": float(cppi_results["Wealth"].iloc[i, 0]),
          "buyhold_wealth": float(cppi_results["Risky Wealth"].iloc[i, 0]),
          "floor_value": float(floor_val),
          "risky_allocation": float(cppi_results["Risky Allocation"].iloc[i, 0]) * 100,
          "risk_budget": float(cppi_results["Risk Budget"].iloc[i, 0]) * 100,
      })
  ```

- [ ] **Step 1.2: Replace all `return {}` paths with structured error dicts**

  There are 4 early-return sites (lines ~568, ~577, ~589, ~665). Replace each:

  ```python
  # Line ~568 — no portfolio/assets
  if not portfolio or not portfolio.assets:
      print("[ERROR] CPPI: No portfolio or assets")
      return {"error": True, "reason": "No holdings found in portfolio", "multiplier": multiplier, "floor": floor}

  # Line ~577 — empty returns
  if portfolio_returns.empty:
      print("[ERROR] CPPI: Portfolio returns are empty")
      return {"error": True, "reason": "No historical price data available for your holdings", "multiplier": multiplier, "floor": floor}

  # Line ~589 — insufficient data
  if len(portfolio_returns) < 50:
      print(f"[ERROR] CPPI: Insufficient clean data ({len(portfolio_returns)} days)")
      return {"error": True, "reason": f"Insufficient data: only {len(portfolio_returns)} trading days available (need 50+)", "multiplier": multiplier, "floor": floor}

  # Line ~665 — exception catch
  except Exception as e:
      print(f"[ERROR] CPPI simulation failed: {e}")
      import traceback
      traceback.print_exc()
      return {"error": True, "reason": f"Simulation error: {str(e)}", "multiplier": multiplier, "floor": floor}
  ```

- [ ] **Step 1.3: Commit**

  ```bash
  git add backend/app/services/portfolio_analysis.py
  git commit -m "fix: structured CPPI errors and floor Series/DataFrame access"
  ```

---

## Task 2: Fix CPPI Frontend — Remove Hardcoded Defaults, Add Error + Skeleton State

**Files:**
- Modify: `frontend/src/components/CPPISection.jsx`

- [ ] **Step 2.1: Add skeleton import and update the loading state**

  At the top of `CPPISection.jsx`, add the import:
  ```jsx
  import { Skeleton, MiniCardSkeleton, ChartSkeleton } from './ui/Skeleton'
  ```

  Replace the loading return (line 47):
  ```jsx
  if (loading) return (
    <div className="space-y-8">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {[1,2,3,4].map(i => <MiniCardSkeleton key={i} />)}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {[1,2,3,4].map(i => <ChartSkeleton key={i} height={320} />)}
      </div>
    </div>
  )
  ```

- [ ] **Step 2.2: Remove hardcoded defaults and add error check**

  Replace lines 51-61 (the destructuring with hardcoded defaults):
  ```jsx
  const cppiAnalysis = data || {}

  // Check for backend error or empty data
  const hasError = cppiAnalysis.error === true ||
    (!cppiAnalysis.performance_data || cppiAnalysis.performance_data.length === 0)

  const {
    multiplier = 3,
    floor = 0.8,
    initial_value = null,
    final_cppi_value = null,
    final_buyhold_value = null,
    outperformance = null,
    performance_data = [],
    drawdown_data = [],
    reason = null,
  } = cppiAnalysis
  ```

- [ ] **Step 2.3: Add error state render (after the destructuring, before `const formatCurrency`)**

  ```jsx
  if (hasError) {
    return (
      <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-6">
        <div className="flex items-start">
          <Info className="h-6 w-6 text-yellow-600 dark:text-yellow-400 mt-1 mr-3 flex-shrink-0" />
          <div>
            <h4 className="text-lg font-semibold text-yellow-900 dark:text-yellow-100 mb-2">
              CPPI Simulation Unavailable
            </h4>
            <p className="text-yellow-800 dark:text-yellow-200 mb-3">
              {reason || "Could not calculate CPPI strategy for your portfolio."}
            </p>
            <p className="text-sm text-yellow-700 dark:text-yellow-300">
              Strategy parameters: Multiplier {multiplier}x · Floor {(floor * 100).toFixed(0)}%
            </p>
          </div>
        </div>
      </div>
    )
  }
  ```

- [ ] **Step 2.4: Update metric card values to show N/A for null**

  In the `strategyMetrics` array, update the value fields:
  ```jsx
  const strategyMetrics = [
    {
      label: 'CPPI Final Value',
      value: final_cppi_value != null ? formatCurrency(final_cppi_value) : 'N/A',
      description: 'Dynamic Strategy',
      type: 'positive'
    },
    {
      label: 'Buy & Hold Value',
      value: final_buyhold_value != null ? formatCurrency(final_buyhold_value) : 'N/A',
      description: 'Static Strategy',
      type: 'neutral'
    },
    {
      label: 'Outperformance',
      value: outperformance != null ? formatPercentage(outperformance) : 'N/A',
      description: 'CPPI Advantage',
      type: outperformance != null && outperformance > 0 ? 'positive' : 'negative'
    },
    {
      label: 'Multiplier',
      value: `${multiplier}.0x`,
      description: 'Risk Leverage',
      type: 'neutral'
    }
  ]
  ```

- [ ] **Step 2.5: Commit**

  ```bash
  git add frontend/src/components/CPPISection.jsx
  git commit -m "fix: CPPI frontend error state and remove hardcoded defaults"
  ```

---

## Task 3: Add YTD Backend Endpoint

**Files:**
- Modify: `backend/app/api/v1/market.py`

- [ ] **Step 3.1: Add YTD route to `market.py`**

  After the `get_live_market_data` function and before the WebSocket route (around line 341), add:

  ```python
  @router.get("/ytd")
  async def get_ytd_data(
      currency: Optional[str] = Query(None, description="Currency for display (USD or CAD)"),
      current_user: User = Depends(get_current_active_user),
      db: AsyncSession = Depends(get_db)
  ) -> Any:
      """
      Get YTD return for each holding. Cached for 24h since YTD is a daily metric.
      """
      portfolio = await get_user_portfolio(db, current_user.id)
      if not portfolio:
          raise HTTPException(
              status_code=status.HTTP_404_NOT_FOUND,
              detail="Portfolio not found"
          )

      display_currency = (currency or portfolio.currency or "USD").upper()
      cache_key = f"portfolio:{portfolio.id}:ytd:{display_currency}"
      redis_client = await get_redis_client()

      # Try cache first (24h TTL — YTD only changes meaningfully once a day)
      cached = await redis_client.get(cache_key)
      if cached:
          logger.info(f"Cache hit for portfolio {portfolio.id} YTD data")
          return cached

      holdings = await get_portfolio_holdings(db, portfolio.id)

      ytd_data = []
      for holding in holdings:
          if not holding.ticker:
              continue
          asset_type = holding.asset.asset_type if holding.asset else "stock"
          try:
              perf = await FinanceService.calculate_ticker_performance(
                  holding.ticker, asset_type, ["ytd"]
              )
              ytd_data.append({
                  "ticker": holding.ticker,
                  "ytd_return": perf.get("ytd_return"),
              })
          except Exception as e:
              logger.warning(f"YTD fetch failed for {holding.ticker}: {e}")
              ytd_data.append({"ticker": holding.ticker, "ytd_return": None})

      result = {"ytd_data": ytd_data}
      await redis_client.set(cache_key, result, ttl=86400)
      return result
  ```

- [ ] **Step 3.2: Verify `FinanceService` is already imported in `market.py`**

  It is — line 16: `from app.services.finance_service import FinanceService`. No import change needed.

- [ ] **Step 3.3: Commit**

  ```bash
  git add backend/app/api/v1/market.py
  git commit -m "feat: add /market/ytd endpoint with 24h Redis cache"
  ```

---

## Task 4: Add YTD Column to Live Market Table

**Files:**
- Modify: `frontend/src/pages/LiveMarket.jsx`

- [ ] **Step 4.1: Replace spinner with `TableSkeleton` during loading**

  At the top of the file, add to the existing import on line 8:
  ```jsx
  import { ChartSkeleton, TableSkeleton } from '../components/ui/Skeleton'
  ```
  *(Remove the existing `ChartSkeleton` import since it's now combined.)*

  Replace the loading block (lines 366-372):
  ```jsx
  if (loading) {
    return (
      <div className="space-y-6">
        <TableSkeleton rows={8} columns={8} />
      </div>
    )
  }
  ```

- [ ] **Step 4.3: Add `ytdMap` state and parallel fetch**

  After the existing state declarations (around line 26), add:
  ```jsx
  const [ytdMap, setYtdMap] = useState({}) // ticker -> ytd_return (number|null)
  ```

  In `fetchLiveMarketData` (around line 175, after `setHoldings(holdingsData)`), add a parallel YTD fetch that does NOT block the main loading:
  ```jsx
  // Fire YTD fetch in parallel — don't await, don't block UI
  api.get('/market/ytd', { params: { currency } })
    .then(res => {
      const map = {}
      ;(res.data.ytd_data || []).forEach(({ ticker, ytd_return }) => {
        map[ticker] = ytd_return
      })
      setYtdMap(map)
    })
    .catch(err => {
      console.warn('YTD fetch failed:', err)
      // Non-fatal — table shows N/A for all
    })
  ```

- [ ] **Step 4.4: Add `ytd` sort case to the `sortedHoldings` useMemo**

  In the switch block (around line 312), add after the `'return'` case:
  ```jsx
  case 'ytd':
    aVal = ytdMap[a.ticker] ?? -Infinity
    bVal = ytdMap[b.ticker] ?? -Infinity
    break;
  ```

- [ ] **Step 4.5: Add YTD column header in the desktop table**

  After the Day Change `<th>` block (after line 617), add:
  ```jsx
  <th
    className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider cursor-pointer hover:bg-gray-700"
    style={{ color: 'var(--color-text-secondary)' }}
    onClick={() => handleSort('ytd')}
  >
    <div className="flex items-center justify-end">
      YTD
      {sortConfig.key === 'ytd' && (
        <span className="ml-1">{sortConfig.direction === 'asc' ? '↑' : '↓'}</span>
      )}
    </div>
  </th>
  ```

- [ ] **Step 4.6: Add YTD cell in the desktop table row**

  After the Day Change `<td>` (line ~668), add:
  ```jsx
  {(() => {
    const ytd = ytdMap[holding.ticker]
    if (ytd == null) return (
      <td className="px-6 py-4 whitespace-nowrap text-right text-sm" style={{ color: 'var(--color-text-secondary)' }}>
        N/A
      </td>
    )
    return (
      <td className={`px-6 py-4 whitespace-nowrap text-right text-sm font-medium ${getColorClass(ytd)}`}>
        {formatPercentage(ytd)}
      </td>
    )
  })()}
  ```

- [ ] **Step 4.7: Add YTD cell to the Total row**

  After the portfolioDailyReturn `<td>` in the Total row (line ~691), add an empty `<td>` to keep column alignment:
  ```jsx
  <td className="px-6 py-4 whitespace-nowrap text-right text-sm" style={{ color: 'var(--color-text-secondary)' }}>
    —
  </td>
  ```

- [ ] **Step 4.8: Add YTD row to mobile card view**

  Inside the mobile `.grid.grid-cols-2` div (around line 735, after the Day row), add:
  ```jsx
  <div className="flex justify-between">
    <span style={{ color: 'var(--color-text-secondary)' }}>YTD:</span>
    {(() => {
      const ytd = ytdMap[holding.ticker]
      return ytd != null
        ? <span className={getColorClass(ytd)}>{formatPercentage(ytd)}</span>
        : <span style={{ color: 'var(--color-text-secondary)' }}>N/A</span>
    })()}
  </div>
  ```

- [ ] **Step 4.9: Commit**

  ```bash
  git add frontend/src/pages/LiveMarket.jsx
  git commit -m "feat: add YTD column to live market holdings table with skeleton loader"
  ```

---

## Task 5: Extend Redis Cache TTLs

**Files:**
- Modify: `backend/app/api/v1/market.py:271`
- Modify: `backend/app/api/v1/holdings.py:136`

- [ ] **Step 5.1: Extend quote cache TTL in `market.py`**

  Find line 271:
  ```python
  await redis_client.set(cache_key, quote, ttl=300)  # 5 minute cache
  ```
  Change to:
  ```python
  await redis_client.set(cache_key, quote, ttl=900)  # 15 minute cache
  ```

- [ ] **Step 5.2: Extend holdings cache TTL in `holdings.py`**

  Find line 136 in `holdings.py`:
  ```python
  await redis_client.set(cache_key, json.dumps(response), ttl=300)
  ```
  Change to:
  ```python
  await redis_client.set(cache_key, json.dumps(response), ttl=600)
  ```

- [ ] **Step 5.3: Commit**

  ```bash
  git add backend/app/api/v1/market.py backend/app/api/v1/holdings.py
  git commit -m "perf: extend Redis TTL for quotes (5→15 min) and holdings (5→10 min)"
  ```

---

## Task 6: Cache Portfolio Returns in Redis (Analytics Cold-Start Fix)

**Files:**
- Modify: `backend/app/services/portfolio_analysis.py`

The core bottleneck: every analytics page visit triggers `_build_portfolio()` which fetches 2 years of yfinance data per holding. The in-memory cache (`self._cached_portfolio`) only persists within a single request. Between page visits, the data is fetched from scratch.

Fix: after computing `portfolio_returns` in `run_cppi_simulation()` and `run_monte_carlo_simulation()`, cache the returns DataFrame in Redis. On next call, bypass `_build_portfolio()` entirely for the returns computation.

- [ ] **Step 6.1: Add `_get_cached_returns` and `_cache_returns` helpers to `AdvancedPortfolioAnalytics`**

  Add these two methods after `_build_portfolio` (around line 265). Store returns as a plain list (avoids pandas datetime-index serialization issues) plus the portfolio value.

  ```python
  async def _get_cached_returns(self):
      """
      Retrieve cached (returns_list, total_value) from Redis.
      Returns (pd.Series, float) on hit, (None, None) on miss.
      """
      from app.core.redis_client import get_redis_client
      cache_key = f"portfolio:{self.portfolio_id}:returns_cache"
      redis_client = await get_redis_client()
      cached = await redis_client.get(cache_key)
      if cached is None:
          return None, None
      try:
          returns = pd.Series(cached["values"], dtype=float)
          total_value = float(cached["total_value"])
          print(f"[INFO] Returns cache hit: {len(returns)} days, value=${total_value:.2f}")
          return returns, total_value
      except Exception as e:
          print(f"[WARN] Failed to deserialize returns cache: {e}")
          return None, None

  async def _cache_returns(self, returns: pd.Series, total_value: float) -> None:
      """Store portfolio returns + value in Redis for 10 minutes."""
      from app.core.redis_client import get_redis_client
      cache_key = f"portfolio:{self.portfolio_id}:returns_cache"
      redis_client = await get_redis_client()
      try:
          await redis_client.set(
              cache_key,
              {"values": returns.tolist(), "total_value": total_value},
              ttl=600
          )
          print(f"[INFO] Cached {len(returns)} days of returns to Redis")
      except Exception as e:
          print(f"[WARN] Failed to cache returns: {e}")
  ```

- [ ] **Step 6.2: Use cache in `run_cppi_simulation`**

  Replace the opening of `run_cppi_simulation` (lines ~563-570):

  ```python
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
  ```

  Then remove the existing duplicate `total_value` line further down (line ~595):
  ```python
  # DELETE this line:
  total_value = self._cached_portfolio_value or portfolio.get_total_value()
  ```

- [ ] **Step 6.3: Use cache in `run_monte_carlo_simulation`**

  At `run_monte_carlo_simulation` (around line 467), replace the build+returns block:

  ```python
  async def run_monte_carlo_simulation(self, scenarios: int = 1000, time_horizon: int = 252) -> Dict:
      """Run Monte Carlo simulation for the portfolio."""
      # Try cached returns first
      portfolio_returns, _total_value = await self._get_cached_returns()

      if portfolio_returns is None:
          portfolio = await self._build_portfolio()
          if not portfolio or not portfolio.assets:
              return {}
          portfolio_returns = portfolio.get_portfolio_returns()
          total_value = self._cached_portfolio_value or portfolio.get_total_value()
          await self._cache_returns(portfolio_returns, total_value)
  ```

  Then use `portfolio_returns` directly in the rest of the method instead of calling `portfolio.get_portfolio_returns()` again.

- [ ] **Step 6.4: Commit**

  ```bash
  git add backend/app/services/portfolio_analysis.py
  git commit -m "perf: cache portfolio returns in Redis to skip yfinance re-fetch on analytics"
  ```

---

## Task 7: Deploy and Verify

- [ ] **Step 7.1: Push branch and deploy**

  ```bash
  git push origin claude/hardcore-nobel
  ```

  Then update the GitOps image tag in `../gitops-alikone` (charts/portfolio) and wait for Argo CD to sync, or trigger a rollout via:
  ```bash
  # On VPS:
  ssh ali@204.168.190.84
  kubectl rollout restart deployment/portfolio-backend -n portfolio
  kubectl rollout restart deployment/portfolio-frontend -n portfolio
  ```

- [ ] **Step 7.2: Verify CPPI fix**

  Open `https://portfolio.alikone.dev` → Analytics → CPPI Strategy.
  - If backend data is available: charts should render with real data.
  - If data unavailable: should show the yellow error card with a specific reason (not empty charts with `$1,180` default).
  - Check backend logs: `kubectl logs -n portfolio deployment/portfolio-backend --tail=50 | grep CPPI`

- [ ] **Step 7.3: Verify YTD column**

  Open Live Market page.
  - Table should have a `YTD` column after `Day Change`.
  - Click YTD header — rows should sort.
  - MAU.TO should show `N/A` (no live data).
  - Check Redis cache: `ssh ali@204.168.190.84 "redis-cli keys 'portfolio:*:ytd:*'"`

- [ ] **Step 7.4: Verify performance improvement**

  Open Analytics → CPPI Strategy. Note load time.
  Reload the page. The second load should be significantly faster (Redis returns cache hit).
  Check logs: `kubectl logs -n portfolio deployment/portfolio-backend --tail=20 | grep "cached portfolio returns"`

- [ ] **Step 7.5: Verify Redis TTL extensions**

  ```bash
  ssh ali@204.168.190.84 "redis-cli ttl 'stock:quote:AAPL'"
  # Should return ~900 (15 min)
  ```
