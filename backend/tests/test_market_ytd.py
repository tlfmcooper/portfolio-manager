from datetime import datetime
from types import SimpleNamespace

import pytest

from app.api.v1 import market
from app.services.finance_service import FinanceService


def test_is_mutual_fund_holding_detects_cf_tickers_without_asset_type() -> None:
    holding = SimpleNamespace(
        ticker="PHN9756.CF",
        asset=SimpleNamespace(asset_type=None),
    )

    assert market._is_mutual_fund_holding(holding) is True


def test_tsx_tickers_use_yahoo_quote_path() -> None:
    assert market._uses_yahoo_quote("CCO.TO") is True
    assert market._uses_yahoo_quote("MAU.TO") is True
    assert market._uses_yahoo_quote("AAPL") is False


@pytest.mark.asyncio
async def test_get_ohlc_data_prefers_yahoo_live_price_for_daily_change(monkeypatch) -> None:
    import pandas as pd
    import yfinance as _yf

    class _FakeTicker:
        fast_info = {
            "last_price": 106.25,
            "previous_close": 104.98,
        }

        def __init__(self, _symbol):
            pass

        def history(self, **_kwargs):
            return pd.DataFrame(
                {
                    "Open": [103.0, 105.0],
                    "High": [106.0, 106.5],
                    "Low": [102.5, 104.0],
                    "Close": [104.98, 104.98],
                }
            )

        @property
        def info(self):
            return {}

    monkeypatch.setattr(_yf, "Ticker", _FakeTicker)

    data = await FinanceService.get_ohlc_data("CCO.TO")

    assert data["current_price"] == 106.25
    assert data["previous_close"] == 104.98
    assert data["change"] == pytest.approx(1.27)
    assert data["change_percent"] == pytest.approx(1.209754238902648)


@pytest.mark.asyncio
async def test_get_live_market_data_routes_tsx_holdings_through_yahoo(monkeypatch) -> None:
    portfolio = SimpleNamespace(id=77, currency="CAD", cash_balance=0)
    holding = SimpleNamespace(
        id=1,
        ticker="CCO.TO",
        quantity=2.0,
        average_cost=100.0,
        current_price=104.98,
        asset=SimpleNamespace(
            name="Cameco Corporation",
            ticker="CCO.TO",
            asset_type="stock",
            currency="CAD",
            current_price=104.98,
            last_price_update=None,
        ),
    )
    writes = {}

    class _FakeRedis:
        async def get(self, _key):
            return None

        async def set(self, key, value, ttl=None):
            writes[key] = (value, ttl)

    class _FakeDb:
        async def commit(self):
            pass

    class _ExchangeService:
        async def get_exchange_rate(self, _from, _to):
            return 1

    class _Finnhub:
        async def get_multiple_quotes_async(self, symbols):
            raise AssertionError(f"TSX symbols should not use Finnhub: {symbols}")

    async def fake_portfolio(_db, _uid):
        return portfolio

    async def fake_holdings(_db, _pid):
        return [holding]

    async def fake_redis():
        return _FakeRedis()

    async def fake_ohlc(ticker):
        assert ticker == "CCO.TO"
        return {
            "current_price": 106.25,
            "change_percent": 1.21,
            "change": 1.27,
        }

    monkeypatch.setattr(market, "get_user_portfolio", fake_portfolio)
    monkeypatch.setattr(market, "get_portfolio_holdings", fake_holdings)
    monkeypatch.setattr(market, "get_redis_client", fake_redis)
    monkeypatch.setattr(market, "get_exchange_rate_service", lambda: _ExchangeService())
    monkeypatch.setattr(market, "get_finnhub_service", lambda: _Finnhub())
    monkeypatch.setattr(market.FinanceService, "get_ohlc_data", fake_ohlc)

    result = await market.get_live_market_data(
        currency="CAD",
        current_user=SimpleNamespace(id=1),
        db=_FakeDb(),
    )

    live_holding = result["holdings"][0]
    assert live_holding["ticker"] == "CCO.TO"
    assert live_holding["current_price"] == 106.25
    assert live_holding["change_percent"] == 1.21
    assert live_holding["change"] == 1.27
    assert live_holding["market_value"] == 212.5
    assert result["market_data"] == {}
    assert writes["portfolio:77:live_market:v3:CAD"][1] == 60


@pytest.mark.asyncio
async def test_get_ytd_data_falls_back_to_mutual_fund_fetch_for_cf_tickers(monkeypatch) -> None:
    portfolio = SimpleNamespace(id=7, currency="USD")
    holding = SimpleNamespace(
        ticker="PHN9756.CF",
        asset=SimpleNamespace(asset_type=None),
    )

    class _FakeRedis:
        def __init__(self) -> None:
            self.writes: list = []

        async def get(self, _key):
            return None

        async def set(self, key, value, ttl=None):
            self.writes.append((key, value, ttl))

    fake_redis = _FakeRedis()

    async def fake_get_user_portfolio(_db, _user_id):
        return portfolio

    async def fake_get_portfolio_holdings(_db, _portfolio_id):
        return [holding]

    async def fake_get_redis_client():
        return fake_redis

    async def fake_calculate_ticker_performance(ticker, asset_type=None, periods=None):
        assert ticker == "PHN9756.CF"
        assert asset_type == "mutual_fund"
        assert periods == ["ytd"]
        return {"ytd_return": 12.34}

    monkeypatch.setattr(market, "get_user_portfolio", fake_get_user_portfolio)
    monkeypatch.setattr(market, "get_portfolio_holdings", fake_get_portfolio_holdings)
    monkeypatch.setattr(market, "get_redis_client", fake_get_redis_client)
    monkeypatch.setattr(market.FinanceService, "calculate_ticker_performance", fake_calculate_ticker_performance)

    result = await market.get_ytd_data(
        currency=None,
        current_user=SimpleNamespace(id=99),
        db=object(),
    )

    assert result["ytd_data"] == [{"ticker": "PHN9756.CF", "ytd_return": 12.34}]
    assert any(ttl == 300 for _, _, ttl in fake_redis.writes), "primary key must use 5m TTL"
    assert any("backup" in key for key, _, _ in fake_redis.writes), "backup key must be written"
    assert any("v7" in key for key, _, _ in fake_redis.writes), "cache key must be v7"


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

    primary = f"portfolio:{portfolio.id}:ytd:v7"
    backup = f"portfolio:{portfolio.id}:ytd:v7:backup"
    assert primary in written, "primary v7 key must be written"
    assert backup in written, "backup key must be written on success"
    assert written[primary][1] == 300
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
    primary = f"portfolio:{portfolio.id}:ytd:v7"
    assert written.get(primary, (None, None))[1] == 300


@pytest.mark.asyncio
async def test_get_ytd_data_uses_cost_basis_for_position_first_bought_this_year(monkeypatch) -> None:
    portfolio = SimpleNamespace(id=11, currency="USD")
    holding = SimpleNamespace(
        ticker="BE",
        asset_id=101,
        quantity=10,
        average_cost=100.0,
        current_price=120.0,
        asset=SimpleNamespace(asset_type="stock"),
    )

    class _FakeRedis:
        async def get(self, _k): return None
        async def set(self, _k, _v, ttl=None): pass

    class _FakeResult:
        def all(self):
            return [(101, datetime(2026, 2, 1))]

    class _FakeDb:
        async def execute(self, _stmt):
            return _FakeResult()

    async def fake_portfolio(_db, _uid): return portfolio
    async def fake_holdings(_db, _pid): return [holding]
    async def fake_redis(): return _FakeRedis()

    monkeypatch.setattr(market, "get_user_portfolio", fake_portfolio)
    monkeypatch.setattr(market, "get_portfolio_holdings", fake_holdings)
    monkeypatch.setattr(market, "get_redis_client", fake_redis)

    result = await market.get_ytd_data(
        currency=None,
        current_user=SimpleNamespace(id=1),
        db=_FakeDb(),
    )

    assert result["ytd_data"] == [{"ticker": "BE", "ytd_return": 20.0}]


@pytest.mark.asyncio
async def test_get_ytd_data_prefers_live_market_values_for_same_year_positions(monkeypatch) -> None:
    portfolio = SimpleNamespace(id=14, currency="USD")
    holding = SimpleNamespace(
        ticker="BE",
        asset_id=104,
        quantity=10,
        average_cost=100.0,
        current_price=110.0,
        asset=SimpleNamespace(asset_type="stock"),
    )

    class _FakeRedis:
        async def get(self, key):
            if "live_market" in key:
                return {"holdings": [{"ticker": "BE", "cost_basis": 1000.0, "market_value": 1250.0}]}
            return None
        async def set(self, _k, _v, ttl=None): pass

    class _FakeResult:
        def all(self):
            return [(104, datetime(2026, 3, 1))]

    class _FakeDb:
        async def execute(self, _stmt):
            return _FakeResult()

    async def fake_portfolio(_db, _uid): return portfolio
    async def fake_holdings(_db, _pid): return [holding]
    async def fake_redis(): return _FakeRedis()

    monkeypatch.setattr(market, "get_user_portfolio", fake_portfolio)
    monkeypatch.setattr(market, "get_portfolio_holdings", fake_holdings)
    monkeypatch.setattr(market, "get_redis_client", fake_redis)

    result = await market.get_ytd_data(
        currency=None,
        current_user=SimpleNamespace(id=1),
        db=_FakeDb(),
    )

    assert result["ytd_data"] == [{"ticker": "BE", "ytd_return": 25.0}]


@pytest.mark.asyncio
async def test_get_ytd_data_uses_weighted_cost_basis_for_multiple_same_year_buys(monkeypatch) -> None:
    portfolio = SimpleNamespace(id=12, currency="USD")
    holding = SimpleNamespace(
        ticker="BE",
        asset_id=102,
        quantity=8,
        average_cost=125.0,
        current_price=150.0,
        asset=SimpleNamespace(asset_type="stock"),
    )

    class _FakeRedis:
        async def get(self, _k): return None
        async def set(self, _k, _v, ttl=None): pass

    class _FakeResult:
        def all(self):
            return [(102, datetime(2026, 1, 20))]

    class _FakeDb:
        async def execute(self, _stmt):
            return _FakeResult()

    async def fake_portfolio(_db, _uid): return portfolio
    async def fake_holdings(_db, _pid): return [holding]
    async def fake_redis(): return _FakeRedis()

    monkeypatch.setattr(market, "get_user_portfolio", fake_portfolio)
    monkeypatch.setattr(market, "get_portfolio_holdings", fake_holdings)
    monkeypatch.setattr(market, "get_redis_client", fake_redis)

    result = await market.get_ytd_data(
        currency=None,
        current_user=SimpleNamespace(id=1),
        db=_FakeDb(),
    )

    assert result["ytd_data"] == [{"ticker": "BE", "ytd_return": 20.0}]


@pytest.mark.asyncio
async def test_get_ytd_data_keeps_history_path_for_positions_bought_before_this_year(monkeypatch) -> None:
    import pandas as pd

    portfolio = SimpleNamespace(id=13, currency="USD")
    holding = SimpleNamespace(
        ticker="AAPL",
        asset_id=103,
        quantity=10,
        average_cost=100.0,
        current_price=120.0,
        asset=SimpleNamespace(asset_type="stock"),
    )

    class _FakeRedis:
        async def get(self, _k): return None
        async def set(self, _k, _v, ttl=None): pass

    class _FakeResult:
        def all(self):
            return [(103, datetime(2025, 12, 15))]

    class _FakeDb:
        async def execute(self, _stmt):
            return _FakeResult()

    class _FakeTicker:
        def __init__(self, _sym): pass
        def history(self, **_kw): return pd.DataFrame({"Close": [100.0, 110.0]})
        @property
        def info(self): raise RuntimeError("no info")

    async def fake_portfolio(_db, _uid): return portfolio
    async def fake_holdings(_db, _pid): return [holding]
    async def fake_redis(): return _FakeRedis()

    monkeypatch.setattr(market, "get_user_portfolio", fake_portfolio)
    monkeypatch.setattr(market, "get_portfolio_holdings", fake_holdings)
    monkeypatch.setattr(market, "get_redis_client", fake_redis)
    import yfinance as _yf
    monkeypatch.setattr(_yf, "Ticker", _FakeTicker)

    result = await market.get_ytd_data(
        currency=None,
        current_user=SimpleNamespace(id=1),
        db=_FakeDb(),
    )

    assert result["ytd_data"] == [{"ticker": "AAPL", "ytd_return": 10.0}]


def test_calculate_ytd_from_history_uses_previous_close_for_new_position() -> None:
    import pandas as pd
    from datetime import date

    hist = pd.DataFrame(
        {
            "Open": [280.0, 286.16],
            "Close": [283.36, 290.52],
        },
        index=pd.to_datetime(["2026-04-30", "2026-05-01"]),
    )

    assert market._calculate_ytd_from_history(hist, baseline_date=date(2026, 5, 1)) == 2.53


def test_calculate_ytd_from_history_prefers_live_price_when_available() -> None:
    import pandas as pd

    hist = pd.DataFrame(
        {
            "Open": [100.0, 110.0],
            "Close": [100.0, 110.0],
        },
        index=pd.to_datetime(["2026-01-02", "2026-05-01"]),
    )

    assert market._calculate_ytd_from_history(hist, end_price_override=115.0) == 15.0


def test_calculate_ytd_from_history_uses_buy_day_open_when_previous_close_missing() -> None:
    import pandas as pd
    from datetime import date

    hist = pd.DataFrame(
        {
            "Open": [286.16],
            "Close": [290.52],
        },
        index=pd.to_datetime(["2026-05-01"]),
    )

    assert market._calculate_ytd_from_history(hist, baseline_date=date(2026, 5, 1)) == 1.52
