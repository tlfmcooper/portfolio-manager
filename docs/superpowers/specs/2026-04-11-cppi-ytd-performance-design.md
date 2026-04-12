# Design: CPPI Fix, YTD Column, Performance Improvements

**Date:** 2026-04-11
**Branch:** claude/hardcore-nobel
**Scope:** Three targeted improvements to the portfolio dashboard

---

## Context

Three issues were identified in the live portfolio dashboard:

1. **CPPI strategy page shows empty charts** — the backend silently returns `{}` on failure, causing the frontend to fall back to hardcoded JS defaults (`$1,180`, `$1,125`, `+4.9%`) that look like real data. Charts are empty because `performance_data` and `drawdown_data` default to `[]`.
2. **Live market table lacks a YTD column** — users can see day change and total return, but not year-to-date return per holding.
3. **Pages load slowly** — all analytics API calls fire simultaneously on page load regardless of active tab; Redis TTLs are short; analytics data is rebuilt from scratch (2yr yfinance fetch) on every page visit.

---

## 1. CPPI Bug Fix

### Root Cause

`run_cppi_simulation()` in `backend/app/services/portfolio_analysis.py` catches all exceptions and returns `{}`. The likely crash is:

```python
"floor_value": cppi_results["floor"].iloc[i, 0],  # fails if "floor" is a Series
```

The frontend (`frontend/src/components/CPPISection.jsx`) then destructures `{}` with hardcoded defaults, making the UI appear to show valid data when it doesn't.

### Backend Changes (`portfolio_analysis.py`)

- Defensive `floor` access: check `isinstance(cppi_results["floor"], pd.Series)` and use `.iloc[i]` vs `.iloc[i, 0]` accordingly
- Replace all `return {}` failure paths with a structured error dict:
  ```python
  return {"error": True, "reason": "Insufficient historical data (N days)", "multiplier": multiplier, "floor": floor}
  ```
- Preserve existing print/log statements; add the reason string for frontend consumption

### Backend Changes (`backend/app/api/v1/analysis.py`)

- No HTTP status change needed — return the structured error dict as HTTP 200; frontend interprets `error: true`

### Frontend Changes (`CPPISection.jsx`)

- Remove hardcoded defaults: `final_cppi_value = null`, `final_buyhold_value = null`, `outperformance = null`, `performance_data = []`, `drawdown_data = []`
- After loading: if `data.error === true` OR `performance_data.length === 0`, render an error card:
  > "CPPI simulation could not be calculated. [reason from backend]"
  > Show multiplier and floor params so the user knows what was attempted
- Metrics cards: show `N/A` for null values instead of the hardcoded numbers

---

## 2. YTD Column in Live Market Table

### Backend — New Endpoint (`backend/app/api/v1/market.py`)

```
GET /market/ytd?currency=USD
```

- For each holding, call existing `FinanceService.calculate_ticker_performance(ticker, asset_type, ["ytd"])`
- Returns: `{ "ytd_data": [{ "ticker": "AAPL", "ytd_return": 4.2 }, ...] }`
- Redis cache key: `portfolio:{id}:ytd:{currency}`, TTL: **86400s (24h)**
- Tickers with no historical data return `ytd_return: null`

### Frontend (`frontend/src/pages/LiveMarket.jsx`)

- Fire `/market/ytd` in parallel with the existing `/market/live` call in the same `useEffect`
- Build a ticker → ytd map and merge into holdings: `{ ...holding, ytd_return: ytdMap[holding.ticker] ?? null }`
- Add `YTD` column header after `DAY CHANGE`, with sort support (`handleSort('ytd')`)
- Row rendering: color-coded (green/red), `N/A` for null — same pattern as `Return %`
- Mobile card view: add YTD line alongside day change

---

## 3. Performance Improvements

### A) Lazy-load Analytics Tabs (`frontend/src/pages/Analysis.jsx`)

- Introduce a `fetchedTabs` Set in component state (initially empty)
- On tab click: if tab not in `fetchedTabs`, fire the fetch and add it to the set
- Active tab on mount (e.g. Overview) still fetches immediately — no regression
- Eliminates ~5 concurrent heavy API calls (Monte Carlo, CPPI, Efficient Frontier, etc.) that fire even when user never visits those tabs

### B) Skeleton Loading States

- Replace spinner-or-nothing with per-section skeleton screens (pulsing placeholder blocks)
- Analytics cards: 4 placeholder boxes matching the metric card layout
- Chart areas: a grey pulsing rectangle at the chart's expected height
- Apply to: Analytics page tabs, Live Market table, Dashboard summary cards

### C) Extended Redis TTLs

| Cache Key | Current TTL | New TTL | Rationale |
|-----------|-------------|---------|-----------|
| `stock:quote:{symbol}` | 5 min | 15 min | Market quotes change slowly enough |
| `portfolio:{id}:holdings:{currency}` | 5 min | 10 min | Holdings rarely change mid-session |
| `portfolio:{id}:cppi:*` | none (memory only) | 10 min Redis | 2yr yfinance fetch is expensive |
| `portfolio:{id}:monte_carlo:*` | none (memory only) | 10 min Redis | Same reason |
| `portfolio:{id}:efficient_frontier:*` | none (memory only) | 10 min Redis | Same reason |
| `portfolio:{id}:ytd:{currency}` | new | 24h | YTD is a daily metric |

### D) Cross-request Analytics Cache

`_build_portfolio()` currently caches in-memory per request only — every new browser tab or page refresh rebuilds from scratch (fetches 2yr yfinance price history per holding).

- After building, serialize and store the portfolio returns DataFrame to Redis as JSON with a 10-min TTL: `portfolio:{id}:returns_cache`
- On next call within TTL, deserialize from Redis and skip yfinance fetches
- Invalidate on any holding create/update/sell operation

---

## Files to Modify

| File | Change |
|------|--------|
| `backend/app/services/portfolio_analysis.py` | Fix floor Series/DataFrame access, structured error returns, Redis returns cache |
| `backend/app/api/v1/analysis.py` | No changes needed (errors pass through as HTTP 200) |
| `backend/app/api/v1/market.py` | Add `/market/ytd` endpoint |
| `backend/app/core/redis_client.py` | No changes (reuse existing client) |
| `frontend/src/components/CPPISection.jsx` | Remove hardcoded defaults, add error state |
| `frontend/src/pages/Analysis.jsx` | Lazy-load tabs + skeleton loaders |
| `frontend/src/pages/LiveMarket.jsx` | YTD column + parallel fetch + skeleton loaders |

---

## Verification

1. **CPPI fix**: Navigate to Analytics → CPPI Strategy. Should show a clear error message (not empty charts with fake numbers). Check backend logs for the specific failure reason.
2. **YTD column**: Navigate to Live Market. Table should show a `YTD` column next to `Day Change`. Sortable. `N/A` for tickers without historical data (e.g. MAU.TO).
3. **Lazy tabs**: Open Analytics page in Network tab — confirm only the Overview API call fires on load. Click CPPI tab — confirm CPPI API call fires only then.
4. **Skeleton loaders**: Throttle network to Slow 3G — confirm skeleton placeholders show before data arrives.
5. **Cache**: Load Analytics page, reload — confirm second load is significantly faster (Redis cache hit). Check Redis: `redis-cli keys "portfolio:*"` on the VPS to verify cache keys are being set.
