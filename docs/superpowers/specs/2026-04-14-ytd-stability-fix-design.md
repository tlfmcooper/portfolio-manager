# YTD Stability Fix Design

**Date:** 2026-04-14  
**Status:** Approved

## Problem

Two distinct YTD failures on the Live Market page:

1. **Mutual funds (`.CF` tickers)** — always show N/A. `_get_mutual_fund_history()` relies on a Barchart XSRF token obtained via a two-step HTTP dance. That XSRF approach is currently broken (token extraction failing), so `ytd_return` is always `None` for `.CF` holdings.

2. **Stocks / ETFs / crypto** — intermittently show N/A (all-or-nothing flicker on page refresh). Root cause: a single `yf.download(symbols, ...)` batch call fails transiently (rate limit, network hiccup), setting every ticker's `ytd_return` to `None`. This triggers the 60-second cache TTL, causing rapid re-fetch cycles that keep hitting the failing path.

Both issues are backend-only. No frontend, schema, or database changes are required.

## Scope

Changes confined to two files:

- `backend/app/services/finance_service.py`
- `backend/app/api/v1/market.py`

## Fix 1 — Mutual fund YTD via Barchart quote page

### Current behaviour

`calculate_ticker_performance()` for `mutual_fund` calls `_get_mutual_fund_history()`, which:
1. GETs the Barchart price-history page to obtain an XSRF cookie
2. GETs the Barchart proxied core API with that token
3. Iterates historical rows to find Jan-1 price and latest EOD price
4. Computes `(current - start) / start * 100`

Step 1/2 is failing, so the entire path returns `None`.

### Fix

Extend `_get_mutual_fund_info()` (the quote page scrape that already works for current price) to also attempt to extract YTD data from the same embedded JSON blob. Barchart quote pages embed a large `raw` dict in the HTML; it commonly contains fields beyond `lastPrice` / `previousPrice`.

**Extraction priority** (try in order, stop at first hit):

1. `ytdPercentChange` — use directly as the return percentage
2. `previousYearClose` or `startOfYearPrice` — compute `(lastPrice - yearStart) / yearStart * 100`
3. Neither found — fall back to the existing `_get_mutual_fund_history()` XSRF path

`calculate_ticker_performance()` for `mutual_fund` is updated to call `_get_mutual_fund_info()` first and use the YTD value from it before attempting the history API.

### Price used for YTD

When `ytdPercentChange` is extracted directly, no price arithmetic is needed — it is already the correct return. When computing from `previousYearClose` / `startOfYearPrice`, both values come from the same quote page JSON, so they are always the previous trading day's settled EOD prices. Barchart NAV is only published at 4 pm market close, so the result is always based on the previous day's close — consistent with the requirement.

## Fix 2 — Stocks/ETFs/crypto YTD via per-ticker parallel calls

### Current behaviour

```python
hist = await loop.run_in_executor(
    None,
    lambda: yf.download(symbols, start=year_start, progress=False, auto_adjust=True, threads=True)
)
```

One batch call for all non-MF tickers. If it fails, all entries in `ytd_map` stay `None`.

### Fix

Replace with parallel per-ticker calls:

```python
yesterday = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")

async def fetch_one(orig_ticker, yf_symbol):
    def _sync():
        hist = yf.Ticker(yf_symbol).history(start=year_start, end=yesterday)
        if hist.empty or len(hist) < 2:
            return None
        series = hist["Close"].dropna()
        if len(series) < 2:
            return None
        return round(
            (float(series.iloc[-1]) - float(series.iloc[0])) / float(series.iloc[0]) * 100, 2
        )
    return orig_ticker, await loop.run_in_executor(None, _sync)

pairs = await asyncio.gather(*[fetch_one(orig, yf_sym) for yf_sym, orig in symbol_map.items()])
ytd_map.update(dict(pairs))
```

Key points:
- `end=yesterday` — only settled closing prices; no intraday data; consistent with mutual fund behaviour
- Per-ticker isolation — one bad symbol doesn't cascade to others
- Thread pool parallelism — same as the old batch approach in terms of non-blocking
- `fetch_one` catches all exceptions internally and returns `(ticker, None)` on failure, so `asyncio.gather` never propagates individual errors
- The existing per-ticker fallback loop (`missing_holdings`) is kept as a safety net

## Fix 3 — Stale-cache guard

### Current behaviour

```python
has_data = any(d.get("ytd_return") is not None for d in ytd_data)
await redis_client.set(cache_key, result, ttl=86400 if has_data else 60)
```

A single failed compute overwrites good cached data with a 60-second TTL, causing rapid re-fetch cycles.

### Fix

Introduce a backup cache key alongside the primary:

| Key | TTL when written | Written when |
|---|---|---|
| `portfolio:{id}:ytd:v3` | 24 h | `has_data` is True |
| `portfolio:{id}:ytd:v3:backup` | 72 h | `has_data` is True |

On compute failure (`has_data` is False):

1. Read the backup key.
2. If backup exists: write it to the primary key with a 5-minute TTL (users see last-known-good; system retries every ~5 min), return backup.
3. If no backup: write primary with 60-second TTL as before.

Cache key is bumped from `v2` to `v3` to force-invalidate any stale null-poisoned entries from the old code.

### Effect

A transient yfinance failure never evicts 24 hours of good data. 72+ consecutive hours of complete failure are required before users see N/A.

## Testing

- Unit test: `_get_mutual_fund_info()` returns `ytd_return` when quote page JSON contains `ytdPercentChange`
- Unit test: `_get_mutual_fund_info()` returns `ytd_return` computed from `previousYearClose` when `ytdPercentChange` absent
- Unit test: `get_ytd_data` per-ticker path — one ticker's executor raising does not nullify others
- Unit test: stale-cache guard — failed compute returns backup data instead of null result
- Existing test `test_get_ytd_data_falls_back_to_mutual_fund_fetch_for_cf_tickers` updated for `v3` cache key

## Out of scope

- Frontend changes
- Database / schema changes
- Real-time (intraday) YTD — all YTD uses previous-day close
- Background scheduler for precomputing YTD (future improvement)
