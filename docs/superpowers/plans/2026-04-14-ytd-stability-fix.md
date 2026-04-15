# YTD Stability Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix YTD always showing N/A for `.CF` mutual funds and intermittently for all other tickers.

**Architecture:** Three independent fixes applied in sequence: (1) add `_extract_ytd_from_raw_data()` helper and extend `_get_mutual_fund_info()` to return `ytd_return` from the already-working Barchart quote page scrape; (2) update `calculate_ticker_performance()` to use quote-page YTD before falling back to the broken XSRF history API; (3) replace the monolithic `yf.download()` batch call in `get_ytd_data` with isolated per-ticker `Ticker.history(end=yesterday)` calls, and add a backup Redis key so a failed compute never evicts good cached data.

**Tech Stack:** Python 3.11, FastAPI, yfinance, BeautifulSoup4, Redis (via `app.core.redis_client`), pytest-asyncio

---

## File Structure

| File | Change |
|---|---|
| `backend/app/services/finance_service.py` | Add `_extract_ytd_from_raw_data()` static method; extend `_get_mutual_fund_info()` to return `ytd_return`; restructure mutual fund branch of `calculate_ticker_performance()` |
| `backend/app/api/v1/market.py` | Replace `yf.download()` batch block; add backup key logic; bump cache key `v2` → `v3` |
| `backend/tests/test_finance_service.py` | New tests for `_extract_ytd_from_raw_data()`, extended `_get_mutual_fund_info()`, and new MF `calculate_ticker_performance()` flow; patch existing test |
| `backend/tests/test_market_ytd.py` | New tests for per-ticker isolation and stale-cache backup; update existing `.CF` test for `v3` key |

---

## Task 1: Add `_extract_ytd_from_raw_data()` and extend `_get_mutual_fund_info()` to return `ytd_return`

**Files:**
- Modify: `backend/app/services/finance_service.py`
- Test: `backend/tests/test_finance_service.py`

The Barchart quote page JSON `raw` dict (already parsed successfully for `lastPrice`/`previousPrice`) likely contains YTD fields such as `ytdPercentChange` or `previousYearClose`. We extract them via a new helper, then expose the result as `ytd_return` in `_get_mutual_fund_info()`'s return dict.

- [ ] **Step 1: Write failing tests**

Add to `backend/tests/test_finance_service.py`:

```python
# ── _extract_ytd_from_raw_data ──────────────────────────────────────────

def test_extract_ytd_uses_ytd_percent_change_field():
    raw = {"lastPrice": 45.03, "ytdPercentChange": 5.25}
    result = FinanceService._extract_ytd_from_raw_data(raw, 45.03)
    assert result == 5.25


def test_extract_ytd_uses_previous_year_close_when_percent_absent():
    raw = {"lastPrice": 45.03, "previousYearClose": 42.0}
    result = FinanceService._extract_ytd_from_raw_data(raw, 45.03)
    assert result == round((45.03 - 42.0) / 42.0 * 100, 2)


def test_extract_ytd_returns_none_when_no_ytd_fields():
    raw = {"lastPrice": 45.03, "previousPrice": 44.80}
    result = FinanceService._extract_ytd_from_raw_data(raw, 45.03)
    assert result is None


# ── _get_mutual_fund_info with ytd_return ───────────────────────────────

def _make_barchart_quote_html(raw_fields: dict) -> str:
    """Build minimal Barchart quote HTML the existing parser can handle.

    The parser does:
      re.findall(r"{.*}", str(div))  →  ast.literal_eval  →  result[2]['raw']
    A single-line tuple expression satisfies all three steps.
    """
    raw_repr = repr(raw_fields)
    content = f"{{'meta': 'a'}}, {{'other': 'b'}}, {{'raw': {raw_repr}}}"
    return (
        '<html><body>'
        '<div class="bc-quote-overview row">'
        f'{content}'
        '</div></body></html>'
    )


@pytest.mark.asyncio
async def test_get_mutual_fund_info_returns_ytd_from_ytd_percent_change(monkeypatch):
    html = _make_barchart_quote_html(
        {"lastPrice": 45.03, "previousPrice": 44.80, "ytdPercentChange": 5.25}
    )

    class _Resp:
        text = html
        def raise_for_status(self): pass

    class _Sess:
        cookies = type("C", (), {"get": staticmethod(lambda k: None)})()
        def get(self, url, **kw): return _Resp()

    monkeypatch.setattr(finance_service, "session", _Sess())
    result = await FinanceService._get_mutual_fund_info("PHN9756.CF")

    assert result is not None
    assert result["current_price"] == 45.03
    assert result["ytd_return"] == 5.25


@pytest.mark.asyncio
async def test_get_mutual_fund_info_returns_ytd_from_previous_year_close(monkeypatch):
    html = _make_barchart_quote_html(
        {"lastPrice": 45.03, "previousPrice": 44.80, "previousYearClose": 42.0}
    )

    class _Resp:
        text = html
        def raise_for_status(self): pass

    class _Sess:
        cookies = type("C", (), {"get": staticmethod(lambda k: None)})()
        def get(self, url, **kw): return _Resp()

    monkeypatch.setattr(finance_service, "session", _Sess())
    result = await FinanceService._get_mutual_fund_info("PHN9756.CF")

    assert result is not None
    assert result["ytd_return"] == round((45.03 - 42.0) / 42.0 * 100, 2)


@pytest.mark.asyncio
async def test_get_mutual_fund_info_ytd_return_is_none_when_no_ytd_fields(monkeypatch):
    html = _make_barchart_quote_html(
        {"lastPrice": 45.03, "previousPrice": 44.80}
    )

    class _Resp:
        text = html
        def raise_for_status(self): pass

    class _Sess:
        cookies = type("C", (), {"get": staticmethod(lambda k: None)})()
        def get(self, url, **kw): return _Resp()

    monkeypatch.setattr(finance_service, "session", _Sess())
    result = await FinanceService._get_mutual_fund_info("PHN9756.CF")

    assert result is not None
    assert result.get("ytd_return") is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend
pytest tests/test_finance_service.py::test_extract_ytd_uses_ytd_percent_change_field \
       tests/test_finance_service.py::test_extract_ytd_uses_previous_year_close_when_percent_absent \
       tests/test_finance_service.py::test_extract_ytd_returns_none_when_no_ytd_fields \
       tests/test_finance_service.py::test_get_mutual_fund_info_returns_ytd_from_ytd_percent_change \
       tests/test_finance_service.py::test_get_mutual_fund_info_returns_ytd_from_previous_year_close \
       tests/test_finance_service.py::test_get_mutual_fund_info_ytd_return_is_none_when_no_ytd_fields \
       -v
```

Expected: all 6 FAIL with `AttributeError: type object 'FinanceService' has no attribute '_extract_ytd_from_raw_data'`

- [ ] **Step 3: Add `_extract_ytd_from_raw_data()` to `FinanceService`**

In `backend/app/services/finance_service.py`, add this static method directly before `_get_mutual_fund_info` (after the class-level constants `_BARCHART_USER_AGENT` and `_BARCHART_HISTORY_FIELDS`):

```python
    @staticmethod
    def _extract_ytd_from_raw_data(raw_data: dict, last_price: float) -> Optional[float]:
        """Extract YTD return % from a Barchart quote-page raw data dict.

        Tries direct YTD percentage fields first, then falls back to computing
        from a year-start price field. Returns None if neither is present.
        """
        for field in ("ytdPercentChange", "percentChangeYtd", "ytdReturn", "ytdChangePercent"):
            val = raw_data.get(field)
            if val is not None:
                try:
                    return round(float(val), 2)
                except (ValueError, TypeError):
                    pass

        for field in ("previousYearClose", "startOfYearPrice", "yearStartPrice", "prevYearClose"):
            val = raw_data.get(field)
            if val is not None:
                try:
                    year_start = float(val)
                    if year_start > 0:
                        return round((last_price - year_start) / year_start * 100, 2)
                except (ValueError, TypeError):
                    pass

        return None
```

- [ ] **Step 4: Extend `_get_mutual_fund_info()` to extract and return `ytd_return`**

In `_get_mutual_fund_info()`, after the `change_percent` / `change` computation block and before the `asset_data` dict literal, add:

```python
                ytd_return = None
                if last_price is not None:
                    ytd_return = FinanceService._extract_ytd_from_raw_data(
                        raw_data, float(last_price)
                    )
                logger.debug(
                    f"Barchart quote page raw keys for {ticker}: {sorted(raw_data.keys())}"
                )
```

Then in the `asset_data` dict, add `'ytd_return': ytd_return` as the last key:

```python
                asset_data = {
                    'ticker': ticker.upper(),
                    'name': ticker,
                    'asset_type': 'mutual_fund',
                    'currency': 'USD',
                    'current_price': float(last_price) if last_price else None,
                    'last_price_update': datetime.now(),
                    'change_percent': change_percent,
                    'change': change,
                    'previous_close': float(previous_price) if previous_price else None,
                    'ytd_return': ytd_return,
                }
```

- [ ] **Step 5: Run the 6 new tests**

```bash
cd backend
pytest tests/test_finance_service.py::test_extract_ytd_uses_ytd_percent_change_field \
       tests/test_finance_service.py::test_extract_ytd_uses_previous_year_close_when_percent_absent \
       tests/test_finance_service.py::test_extract_ytd_returns_none_when_no_ytd_fields \
       tests/test_finance_service.py::test_get_mutual_fund_info_returns_ytd_from_ytd_percent_change \
       tests/test_finance_service.py::test_get_mutual_fund_info_returns_ytd_from_previous_year_close \
       tests/test_finance_service.py::test_get_mutual_fund_info_ytd_return_is_none_when_no_ytd_fields \
       -v
```

Expected: all 6 PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/finance_service.py backend/tests/test_finance_service.py
git commit -m "feat: extract YTD return from Barchart quote page raw JSON"
```

---

## Task 2: Update `calculate_ticker_performance()` to use quote-page YTD first for mutual funds

**Files:**
- Modify: `backend/app/services/finance_service.py` (mutual fund branch ~lines 492–547)
- Test: `backend/tests/test_finance_service.py`

Restructure the mutual fund branch to call `_get_mutual_fund_info()` first (no XSRF needed). Only fall through to `_get_mutual_fund_history()` when the quote page didn't provide the needed period, or when 1m/3m/1y are requested.

- [ ] **Step 1: Write failing tests**

Add to `backend/tests/test_finance_service.py`:

```python
@pytest.mark.asyncio
async def test_calculate_ticker_performance_uses_quote_page_ytd_without_calling_history_api(
    monkeypatch,
):
    """When quote page returns ytd_return, history API must not be called."""
    history_calls = []

    async def fake_get_mutual_fund_info(ticker):
        return {"current_price": 45.03, "ytd_return": 5.25}

    async def fake_get_mutual_fund_history(ticker, limit=400):
        history_calls.append(ticker)
        return None

    monkeypatch.setattr(FinanceService, "_get_mutual_fund_info", fake_get_mutual_fund_info)
    monkeypatch.setattr(FinanceService, "_get_mutual_fund_history", fake_get_mutual_fund_history)

    result = await FinanceService.calculate_ticker_performance(
        "PHN9756.CF", asset_type="mutual_fund", periods=["ytd"]
    )

    assert result["ytd_return"] == 5.25
    assert result["current_price"] == 45.03
    assert result["historical_data_available"] is True
    assert history_calls == [], "history API must not be called when quote page has YTD"


@pytest.mark.asyncio
async def test_calculate_ticker_performance_falls_back_to_history_when_quote_page_lacks_ytd(
    monkeypatch,
):
    fixed_now = datetime(2026, 4, 5)

    class _FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now if tz is None else fixed_now.astimezone(tz)

    async def fake_get_mutual_fund_info(ticker):
        return {"current_price": None, "ytd_return": None}

    async def fake_get_mutual_fund_history(ticker, limit=400):
        return [
            {"raw": {"tradeTime": "2026-01-02", "lastPrice": 100.0}},
            {"raw": {"tradeTime": "2026-04-02", "lastPrice": 120.0}},
        ]

    monkeypatch.setattr(finance_service, "datetime", _FixedDatetime)
    monkeypatch.setattr(FinanceService, "_get_mutual_fund_info", fake_get_mutual_fund_info)
    monkeypatch.setattr(FinanceService, "_get_mutual_fund_history", fake_get_mutual_fund_history)

    result = await FinanceService.calculate_ticker_performance(
        "PHN9756.CF", asset_type="mutual_fund", periods=["ytd"]
    )

    assert result["ytd_return"] == 20.0
    assert result["current_price"] == 120.0


@pytest.mark.asyncio
async def test_calculate_ticker_performance_uses_history_for_non_ytd_periods_even_when_quote_has_ytd(
    monkeypatch,
):
    fixed_now = datetime(2026, 4, 5)

    class _FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now if tz is None else fixed_now.astimezone(tz)

    async def fake_get_mutual_fund_info(ticker):
        return {"current_price": 120.0, "ytd_return": 20.0}

    async def fake_get_mutual_fund_history(ticker, limit=400):
        return [
            {"raw": {"tradeTime": "2026-01-02", "lastPrice": 100.0}},
            {"raw": {"tradeTime": "2026-03-05", "lastPrice": 110.0}},
            {"raw": {"tradeTime": "2026-04-02", "lastPrice": 120.0}},
        ]

    monkeypatch.setattr(finance_service, "datetime", _FixedDatetime)
    monkeypatch.setattr(FinanceService, "_get_mutual_fund_info", fake_get_mutual_fund_info)
    monkeypatch.setattr(FinanceService, "_get_mutual_fund_history", fake_get_mutual_fund_history)

    result = await FinanceService.calculate_ticker_performance(
        "PHN9756.CF", asset_type="mutual_fund", periods=["ytd", "1m", "3m"]
    )

    assert result["ytd_return"] == 20.0          # from quote page
    assert result["one_month_return"] is not None  # from history
    assert result["three_month_return"] is not None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend
pytest tests/test_finance_service.py::test_calculate_ticker_performance_uses_quote_page_ytd_without_calling_history_api \
       tests/test_finance_service.py::test_calculate_ticker_performance_falls_back_to_history_when_quote_page_lacks_ytd \
       tests/test_finance_service.py::test_calculate_ticker_performance_uses_history_for_non_ytd_periods_even_when_quote_has_ytd \
       -v
```

Expected: FAIL

- [ ] **Step 3: Replace the mutual fund branch in `calculate_ticker_performance()`**

In `backend/app/services/finance_service.py`, replace the entire `if asset_type == "mutual_fund":` block (from that line through `return result`) with:

```python
        if asset_type == "mutual_fund":
            result["data_source"] = "barchart"

            # ── Primary: quote page (no XSRF needed) ────────────────────────
            try:
                mf_info = await FinanceService._get_mutual_fund_info(ticker)
                if mf_info:
                    if mf_info.get("current_price") is not None:
                        result["current_price"] = mf_info["current_price"]
                    if "ytd" in periods and mf_info.get("ytd_return") is not None:
                        result["ytd_return"] = mf_info["ytd_return"]
                        result["historical_data_available"] = True
            except Exception as e:
                logger.warning(f"Failed to get MF quote page info for {ticker}: {e}")

            # ── Fallback: history API for remaining periods or missing YTD ───
            needs_history = any(p in periods for p in ["1m", "3m", "1y"]) or (
                "ytd" in periods and result["ytd_return"] is None
            )
            if needs_history:
                try:
                    history = await FinanceService._get_mutual_fund_history(ticker)
                    if history:
                        if result["current_price"] is None:
                            for row in reversed(history):
                                raw = row.get("raw") or {}
                                price = raw.get("lastPrice")
                                if price is not None:
                                    result["current_price"] = float(price)
                                    break

                        result["historical_data_available"] = True
                        today = datetime.now().date()

                        if "ytd" in periods and result["ytd_return"] is None:
                            start_price = FinanceService._get_history_start_price(
                                history, date(today.year, 1, 1)
                            )
                            if start_price and result["current_price"]:
                                result["ytd_return"] = round(
                                    (result["current_price"] - start_price)
                                    / start_price
                                    * 100,
                                    2,
                                )

                        if "1m" in periods:
                            start_price = FinanceService._get_history_start_price(
                                history, today - timedelta(days=31)
                            )
                            if start_price and result["current_price"]:
                                result["one_month_return"] = round(
                                    (result["current_price"] - start_price)
                                    / start_price
                                    * 100,
                                    2,
                                )

                        if "3m" in periods:
                            start_price = FinanceService._get_history_start_price(
                                history, today - timedelta(days=90)
                            )
                            if start_price and result["current_price"]:
                                result["three_month_return"] = round(
                                    (result["current_price"] - start_price)
                                    / start_price
                                    * 100,
                                    2,
                                )

                        if "1y" in periods:
                            start_price = FinanceService._get_history_start_price(
                                history, today - timedelta(days=365)
                            )
                            if start_price and result["current_price"]:
                                result["one_year_return"] = round(
                                    (result["current_price"] - start_price)
                                    / start_price
                                    * 100,
                                    2,
                                )
                    else:
                        if result["ytd_return"] is None:
                            result["historical_data_available"] = False
                except Exception as e:
                    logger.warning(f"Failed to get mutual fund history for {ticker}: {e}")

            return result
```

- [ ] **Step 4: Patch the existing history-based test to mock `_get_mutual_fund_info`**

In `backend/tests/test_finance_service.py`, in `test_calculate_ticker_performance_uses_barchart_history_for_mutual_funds`, add a mock for `_get_mutual_fund_info` that returns no YTD (so the test still exercises the history path):

```python
    async def fake_get_mutual_fund_info(_ticker):
        return {"current_price": None, "ytd_return": None}

    monkeypatch.setattr(FinanceService, "_get_mutual_fund_info", fake_get_mutual_fund_info)
```

Add this before the existing `monkeypatch.setattr(FinanceService, "_get_mutual_fund_history", fake_history)` line.

- [ ] **Step 5: Run all finance_service tests**

```bash
cd backend
pytest tests/test_finance_service.py -v
```

Expected: all tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/finance_service.py backend/tests/test_finance_service.py
git commit -m "feat: use Barchart quote page for mutual fund YTD before falling back to history API"
```

---

## Task 3: Replace `yf.download()` batch with per-ticker parallel `history(end=yesterday)` in `get_ytd_data`

**Files:**
- Modify: `backend/app/api/v1/market.py` (the `# ── Stocks / ETFs / Crypto` block ~lines 436–491)
- Test: `backend/tests/test_market_ytd.py`

- [ ] **Step 1: Write a failing isolation test**

Add to `backend/tests/test_market_ytd.py`:

```python
@pytest.mark.asyncio
async def test_get_ytd_data_isolates_per_ticker_failure(monkeypatch) -> None:
    """One failing ticker must not nullify the others."""
    import pandas as pd

    portfolio = SimpleNamespace(id=8, currency="USD")
    holdings = [
        SimpleNamespace(ticker="AAPL", asset=SimpleNamespace(asset_type="stock")),
        SimpleNamespace(ticker="BROKEN", asset=SimpleNamespace(asset_type="stock")),
        SimpleNamespace(ticker="GOOG", asset=SimpleNamespace(asset_type="stock")),
    ]

    class _FakeRedis:
        async def get(self, _k): return None
        async def set(self, _k, v, ttl=None): pass

    async def fake_portfolio(_db, _uid): return portfolio
    async def fake_holdings(_db, _pid): return holdings
    async def fake_redis(): return _FakeRedis()

    class _FakeTicker:
        def __init__(self, symbol):
            self._symbol = symbol

        def history(self, **kwargs):
            if "BROKEN" in self._symbol:
                raise RuntimeError("simulated network failure")
            return pd.DataFrame({"Close": [100.0, 110.0]})

        @property
        def info(self):
            raise RuntimeError("no info in test")

    monkeypatch.setattr(market, "get_user_portfolio", fake_portfolio)
    monkeypatch.setattr(market, "get_portfolio_holdings", fake_holdings)
    monkeypatch.setattr(market, "get_redis_client", fake_redis)

    import yfinance as _yf
    monkeypatch.setattr(_yf, "Ticker", _FakeTicker)

    result = await market.get_ytd_data(
        currency=None,
        current_user=SimpleNamespace(id=1),
        db=object(),
    )

    ytd = {d["ticker"]: d["ytd_return"] for d in result["ytd_data"]}
    assert ytd["AAPL"] == round((110.0 - 100.0) / 100.0 * 100, 2)
    assert ytd["GOOG"] == round((110.0 - 100.0) / 100.0 * 100, 2)
    assert ytd["BROKEN"] is None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend
pytest tests/test_market_ytd.py::test_get_ytd_data_isolates_per_ticker_failure -v
```

Expected: FAIL (current batch path doesn't use `_FakeTicker.history`)

- [ ] **Step 3: Replace the batch download block in `get_ytd_data`**

In `backend/app/api/v1/market.py`, replace the entire `# ── Stocks / ETFs / Crypto: single batch yfinance download ──────────────` block with:

```python
    # ── Stocks / ETFs / Crypto: per-ticker parallel history(end=yesterday) ──
    if other_holdings:
        import yfinance as yf
        from datetime import datetime as _dt, date as _date, timedelta as _td

        year_start = _dt(_dt.now().year, 1, 1)
        yesterday = (_date.today() - _td(days=1)).strftime("%Y-%m-%d")

        def yf_symbol(holding):
            t = holding.ticker
            if holding.asset and holding.asset.asset_type == "crypto" and "-USD" not in t.upper():
                return f"{t.upper()}-USD"
            return t

        symbol_map = {yf_symbol(h): h.ticker for h in other_holdings}

        def _fetch_one_ytd(yf_sym: str) -> Optional[float]:
            """Fetch YTD return for one ticker. Runs in thread pool; catches all errors."""
            try:
                hist = yf.Ticker(yf_sym).history(start=year_start, end=yesterday)
                if hist.empty:
                    return None
                series = hist["Close"].dropna()
                if len(series) < 2:
                    return None
                return round(
                    (float(series.iloc[-1]) - float(series.iloc[0]))
                    / float(series.iloc[0])
                    * 100,
                    2,
                )
            except Exception as e:
                logger.warning(f"Per-ticker YTD fetch failed for {yf_sym}: {e}")
                return None

        async def _fetch_one_async(orig_ticker: str, yf_sym: str):
            val = await loop.run_in_executor(None, lambda: _fetch_one_ytd(yf_sym))
            return orig_ticker, val

        loop = asyncio.get_event_loop()
        pairs = await asyncio.gather(
            *[_fetch_one_async(orig, yf_sym) for yf_sym, orig in symbol_map.items()]
        )
        ytd_map.update(dict(pairs))
```

- [ ] **Step 4: Run the isolation test**

```bash
cd backend
pytest tests/test_market_ytd.py::test_get_ytd_data_isolates_per_ticker_failure -v
```

Expected: PASS

- [ ] **Step 5: Run all market YTD tests**

```bash
cd backend
pytest tests/test_market_ytd.py -v
```

Expected: all tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/v1/market.py backend/tests/test_market_ytd.py
git commit -m "feat: per-ticker parallel YTD with end=yesterday replaces yf.download batch"
```

---

## Task 4: Stale-cache backup key + bump cache key to `v3`

**Files:**
- Modify: `backend/app/api/v1/market.py` (cache key declaration and final write block in `get_ytd_data`)
- Test: `backend/tests/test_market_ytd.py`

- [ ] **Step 1: Write failing tests**

Add to `backend/tests/test_market_ytd.py`:

```python
@pytest.mark.asyncio
async def test_get_ytd_data_writes_backup_key_on_success(monkeypatch) -> None:
    import pandas as pd

    portfolio = SimpleNamespace(id=9, currency="USD")
    holding = SimpleNamespace(ticker="AAPL", asset=SimpleNamespace(asset_type="stock"))
    written: dict = {}

    class _FakeRedis:
        async def get(self, key): return None
        async def set(self, key, value, ttl=None): written[key] = (value, ttl)

    async def fake_portfolio(_db, _uid): return portfolio
    async def fake_holdings(_db, _pid): return [holding]
    async def fake_redis(): return _FakeRedis()

    class _FakeTicker:
        def __init__(self, sym): pass
        def history(self, **kw): return pd.DataFrame({"Close": [100.0, 110.0]})
        @property
        def info(self): raise RuntimeError("no info")

    monkeypatch.setattr(market, "get_user_portfolio", fake_portfolio)
    monkeypatch.setattr(market, "get_portfolio_holdings", fake_holdings)
    monkeypatch.setattr(market, "get_redis_client", fake_redis)
    import yfinance as _yf
    monkeypatch.setattr(_yf, "Ticker", _FakeTicker)

    await market.get_ytd_data(currency=None, current_user=SimpleNamespace(id=1), db=object())

    primary = f"portfolio:{portfolio.id}:ytd:v3"
    backup = f"portfolio:{portfolio.id}:ytd:v3:backup"
    assert primary in written, "primary v3 key must be written"
    assert backup in written, "backup key must be written on success"
    assert written[primary][1] == 86400
    assert written[backup][1] == 259200


@pytest.mark.asyncio
async def test_get_ytd_data_serves_backup_when_compute_yields_no_data(monkeypatch) -> None:
    portfolio = SimpleNamespace(id=10, currency="USD")
    holding = SimpleNamespace(ticker="FAIL", asset=SimpleNamespace(asset_type="stock"))
    backup_payload = {"ytd_data": [{"ticker": "FAIL", "ytd_return": 7.77}]}
    written: dict = {}

    class _FakeRedis:
        async def get(self, key):
            if "backup" in key:
                return backup_payload
            return None
        async def set(self, key, value, ttl=None):
            written[key] = (value, ttl)

    async def fake_portfolio(_db, _uid): return portfolio
    async def fake_holdings(_db, _pid): return [holding]
    async def fake_redis(): return _FakeRedis()

    class _FakeTicker:
        def __init__(self, sym): pass
        def history(self, **kw): raise RuntimeError("network down")
        @property
        def info(self): raise RuntimeError("no info")

    monkeypatch.setattr(market, "get_user_portfolio", fake_portfolio)
    monkeypatch.setattr(market, "get_portfolio_holdings", fake_holdings)
    monkeypatch.setattr(market, "get_redis_client", fake_redis)
    import yfinance as _yf
    monkeypatch.setattr(_yf, "Ticker", _FakeTicker)

    result = await market.get_ytd_data(
        currency=None, current_user=SimpleNamespace(id=1), db=object()
    )

    assert result == backup_payload
    primary = f"portfolio:{portfolio.id}:ytd:v3"
    assert written.get(primary, (None, None))[1] == 300  # 5-min retry TTL
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend
pytest tests/test_market_ytd.py::test_get_ytd_data_writes_backup_key_on_success \
       tests/test_market_ytd.py::test_get_ytd_data_serves_backup_when_compute_yields_no_data \
       -v
```

Expected: FAIL (`v3` key not found / backup key not found)

- [ ] **Step 3: Update cache key declaration in `get_ytd_data`**

In `backend/app/api/v1/market.py`, change:

```python
    cache_key = f"portfolio:{portfolio.id}:ytd:v2"
    redis_client = await get_redis_client()

    # Try cache first (24h TTL — YTD only changes meaningfully once a day)
    cached = await redis_client.get(cache_key)
    if cached:
        logger.info(f"Cache hit for portfolio {portfolio.id} YTD data")
        return cached
```

To:

```python
    cache_key = f"portfolio:{portfolio.id}:ytd:v3"
    backup_key = f"portfolio:{portfolio.id}:ytd:v3:backup"
    redis_client = await get_redis_client()

    # Try primary cache first (24h TTL)
    cached = await redis_client.get(cache_key)
    if cached:
        logger.info(f"Cache hit for portfolio {portfolio.id} YTD data")
        return cached
```

- [ ] **Step 4: Replace the final write block at the end of `get_ytd_data`**

Change:

```python
    ytd_data = [{"ticker": h.ticker, "ytd_return": ytd_map.get(h.ticker)} for h in valid_holdings]
    result = {"ytd_data": ytd_data}
    # Only use 24h TTL when we actually got data — a transient failure (e.g. network error
    # on first cold start) would otherwise poison the cache for a full day.
    has_data = any(d.get("ytd_return") is not None for d in ytd_data)
    await redis_client.set(cache_key, result, ttl=86400 if has_data else 60)
    return result
```

To:

```python
    ytd_data = [{"ticker": h.ticker, "ytd_return": ytd_map.get(h.ticker)} for h in valid_holdings]
    result = {"ytd_data": ytd_data}
    has_data = any(d.get("ytd_return") is not None for d in ytd_data)

    if has_data:
        await redis_client.set(cache_key, result, ttl=86400)    # 24 h primary
        await redis_client.set(backup_key, result, ttl=259200)  # 72 h backup
        return result

    # Compute yielded no data — return backup to avoid erasing good cached results
    backup = await redis_client.get(backup_key)
    if backup:
        logger.warning(
            f"YTD compute yielded no data for portfolio {portfolio.id}; serving backup cache"
        )
        await redis_client.set(cache_key, backup, ttl=300)  # 5-min retry window
        return backup

    logger.warning(
        f"YTD compute yielded no data for portfolio {portfolio.id}; no backup available"
    )
    await redis_client.set(cache_key, result, ttl=60)
    return result
```

- [ ] **Step 5: Update existing `.CF` test for `v3` key**

In `backend/tests/test_market_ytd.py`, in `test_get_ytd_data_falls_back_to_mutual_fund_fetch_for_cf_tickers`, the `_FakeRedis` class currently stores only the last `set` call in `self.saved`. Update it to collect all writes and update assertions:

Replace the `_FakeRedis` class in that test with:

```python
    class _FakeRedis:
        def __init__(self) -> None:
            self.writes: list = []

        async def get(self, _key):
            return None

        async def set(self, key, value, ttl=None):
            self.writes.append((key, value, ttl))
```

Replace the final assertions:

```python
    assert result["ytd_data"] == [{"ticker": "PHN9756.CF", "ytd_return": 12.34}]
    assert any(ttl == 86400 for _, _, ttl in fake_redis.writes), "primary key must use 24h TTL"
    assert any("backup" in key for key, _, _ in fake_redis.writes), "backup key must be written"
    assert any("v3" in key for key, _, _ in fake_redis.writes), "cache key must be v3"
```

- [ ] **Step 6: Run all market YTD tests**

```bash
cd backend
pytest tests/test_market_ytd.py -v
```

Expected: all tests PASS

- [ ] **Step 7: Run the full test suite**

```bash
cd backend
pytest tests/ -v
```

Expected: all tests PASS

- [ ] **Step 8: Commit**

```bash
git add backend/app/api/v1/market.py backend/tests/test_market_ytd.py
git commit -m "feat: stale-cache backup key and v3 cache key for YTD endpoint"
```
