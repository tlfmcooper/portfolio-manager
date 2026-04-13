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
