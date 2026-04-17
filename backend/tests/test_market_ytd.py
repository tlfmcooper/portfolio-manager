from types import SimpleNamespace

import pytest

from app.api.v1 import market


def test_is_mutual_fund_holding_detects_cf_tickers_without_asset_type() -> None:
    holding = SimpleNamespace(
        ticker="PHN9756.CF",
        asset=SimpleNamespace(asset_type=None),
    )

    assert market._is_mutual_fund_holding(holding) is True


@pytest.mark.asyncio
async def test_get_ytd_data_falls_back_to_mutual_fund_fetch_for_cf_tickers(monkeypatch) -> None:
    portfolio = SimpleNamespace(id=7, currency="USD")
    holding = SimpleNamespace(
        ticker="PHN9756.CF",
        asset=SimpleNamespace(asset_type=None),
    )

    class _FakeRedis:
        def __init__(self) -> None:
            self.saved = None

        async def get(self, _key):
            return None

        async def set(self, _key, value, ttl=None):
            self.saved = (value, ttl)

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
    assert fake_redis.saved is not None
    assert fake_redis.saved[1] == 86400


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
