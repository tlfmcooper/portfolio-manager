from datetime import date
import pandas as pd
import pytest
from app.services.account_performance import account_returns, IncompleteAccountHistory

START = date(2025, 12, 31)
END = date(2026, 1, 6)

def series(points):
    return pd.Series([p[1] for p in points], index=pd.to_datetime([p[0] for p in points]), dtype=float)

def history(points, currency='USD'):
    return {'prices': series(points), 'currency': currency}

def calculate(quantities, cash=0, events=None, prices=None, fx=None, end=END):
    return account_returns(quantities=quantities, cash=cash, transactions=events or [],
        prices=prices or {}, fx=fx or {}, portfolio_currency='USD', display_currency='USD', start=START, end=end)

def test_newly_purchased_asset_does_not_truncate_account_history():
    prices = {'OLD': history([('2025-12-31', 100), ('2026-01-02', 110), ('2026-01-05', 110), ('2026-01-06', 110)]),
        'IPO': history([('2026-01-05', 50), ('2026-01-06', 55)])}
    events = [{'date': date(2026, 1, 5), 'kind': 'BUY', 'ticker': 'IPO', 'quantity': 1, 'amount': 50, 'currency': 'USD'}]
    returns, facts = calculate({'OLD': 1, 'IPO': 1}, prices=prices, events=events)
    assert str(returns.index[0].date()) == '2026-01-02'
    assert returns.tolist() == pytest.approx([10 / 150, 0, 5 / 160])
    assert facts['opening_value'] == 150
    assert facts['closing_value'] == 165

def test_contributions_and_withdrawals_are_not_investment_returns():
    prices = {'AAA': history([('2025-12-31', 100), ('2026-01-02', 100), ('2026-01-05', 100), ('2026-01-06', 100)])}
    events = [{'date': date(2026, 1, 2), 'kind': 'DEPOSIT', 'amount': 200, 'currency': 'USD'},
              {'date': date(2026, 1, 3), 'kind': 'WITHDRAWAL', 'amount': 100, 'currency': 'USD'}]
    returns, facts = calculate({'AAA': 1}, cash=100, events=events, prices=prices)
    assert returns.tolist() == pytest.approx([0, 0, 0])
    assert facts['net_external_flows'] == 100

def test_fully_sold_asset_contributes_until_sale_and_later_trades_are_rewound():
    prices = {'SOLD': history([('2025-12-31', 100), ('2026-01-02', 120)]),
              'NEW': history([('2026-01-07', 200)])}
    events = [{'date': date(2026, 1, 2), 'kind': 'SELL', 'ticker': 'SOLD', 'quantity': 1, 'amount': 120, 'currency': 'USD'},
              {'date': date(2026, 1, 7), 'kind': 'BUY', 'ticker': 'NEW', 'quantity': 1, 'amount': 200, 'currency': 'USD'}]
    returns, facts = calculate({'SOLD': 0, 'NEW': 1}, cash=20, prices=prices, events=events)
    assert returns.tolist() == pytest.approx([.1, 0, 0])
    assert facts['opening_value'] == 200
    assert facts['closing_value'] == 220

def test_currency_moves_are_in_account_returns():
    prices = {'CAD_FUND': history([('2025-12-31', 100), ('2026-01-02', 100), ('2026-01-05', 100)], 'CAD')}
    returns, _ = calculate({'CAD_FUND': 1}, prices=prices,
        fx={'CAD': series([('2025-12-31', .70), ('2026-01-02', .77), ('2026-01-05', .77)])}, end=date(2026, 1, 5))
    assert returns.tolist() == pytest.approx([.1, 0])

def test_missing_history_for_a_held_asset_is_not_filled_with_zero():
    with pytest.raises(IncompleteAccountHistory, match='Missing history for IPO'):
        calculate({'IPO': 1}, prices={'IPO': history([('2026-01-05', 50)])})

from test_portfolio_planning import planning_client

@pytest.mark.asyncio
async def test_account_endpoint_preserves_ownership_and_does_not_call_scenarios(planning_client, monkeypatch):
    from app.services import account_performance
    from app.services.portfolio_scenarios import PortfolioScenarioService
    from app.core.redis_client import get_redis_client
    cache = await get_redis_client()
    await cache.delete_prefix('portfolio:')
    seen = []
    async def account(pid, db, currency):
        seen.append((pid, currency))
        return {'performance_basis': 'account_ytd', 'ytd_return_percentage': 25, 'sharpe_ratio': 1.5}
    async def forbidden(*args, **kwargs):
        raise AssertionError('Account performance must not be an allocation simulation')
    monkeypatch.setattr(account_performance, 'calculate_account_performance', account)
    monkeypatch.setattr(PortfolioScenarioService, 'analyze', forbidden)
    client, headers, pid = planning_client
    path = f'/api/v1/analysis/portfolios/{pid}/account-performance'
    response = await client.get(path, params={'currency': 'CAD'}, headers=headers)
    assert response.status_code == 200
    assert response.json()['sharpe_ratio'] == 1.5
    assert seen == [(pid, 'CAD')]
    assert (await client.get(path)).status_code == 401
    from app.core.security import create_access_token
    other = {'Authorization': f"Bearer {create_access_token({'sub': 'other'})}"}
    assert (await client.get(path, headers=other)).status_code == 404


def test_split_normalization_changes_shares_without_changing_trade_cash():
    from app.services.account_performance import normalized_trades
    trade = {'date': date(2026, 1, 2), 'kind': 'BUY', 'ticker': 'SPLIT', 'quantity': 10, 'amount': 1000}
    rows = normalized_trades([trade], {'SPLIT': {'splits': [('2026-01-05', 2)]}})
    assert rows[0]['quantity'] == 20
    assert rows[0]['amount'] == 1000
    assert trade['quantity'] == 10


@pytest.mark.asyncio
async def test_account_valuation_uses_quoted_close_instead_of_dividend_adjusted_close(monkeypatch):
    import yfinance as yf
    from app.services.account_performance import account_history
    from app.core.redis_client import get_redis_client
    cache = await get_redis_client()
    await cache.delete_prefix('market:account-closes:')
    calls = []
    class Ticker:
        def history(self, **params):
            calls.append(params)
            return pd.DataFrame({'Close': [100, 101], 'Adj Close': [99, 100], 'Stock Splits': [0, 2]},
                                index=pd.to_datetime(['2025-12-31', '2026-01-02']))
    monkeypatch.setattr(yf, 'Ticker', lambda symbol: Ticker())
    result = await account_history('TEST', 'stock', date(2026, 1, 6))
    assert calls[0]['auto_adjust'] is False
    assert result['points'][0][1] == 100
    assert result['splits'] == [('2026-01-02', 2)]


@pytest.mark.asyncio
async def test_empty_download_is_retried_before_caching(monkeypatch):
    import yfinance as yf
    from app.services.account_performance import account_history
    from app.core.redis_client import RedisClient
    from app.services import account_performance
    cache = RedisClient()
    async def get_cache(): return cache
    monkeypatch.setattr(account_performance, 'get_redis_client', get_cache)
    calls = []
    class Ticker:
        def history(self, **params):
            calls.append(1)
            if len(calls) == 1:
                return pd.DataFrame()
            return pd.DataFrame({'Close': [100, 101]}, index=pd.to_datetime(['2025-12-31', '2026-01-02']))
    monkeypatch.setattr(yf, 'Ticker', lambda symbol: Ticker())
    result = await account_history('MU', 'stock', date(2026, 1, 6))
    assert len(result['points']) == 2
    assert len(calls) == 2
    cached = await account_history('MU', 'stock', date(2026, 1, 6))
    assert [tuple(point) for point in cached['points']] == result['points']
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_persistent_failure_is_not_cached_and_next_request_can_recover(monkeypatch):
    import yfinance as yf
    from app.core.redis_client import RedisClient
    from app.services import account_performance
    cache = RedisClient()
    async def get_cache(): return cache
    monkeypatch.setattr(account_performance, 'get_redis_client', get_cache)
    failed = [True]
    class Ticker:
        def history(self, **params):
            if failed[0]:
                raise TimeoutError('upstream temporarily unavailable')
            return pd.DataFrame({'Close': [100, 101]}, index=pd.to_datetime(['2025-12-31', '2026-01-02']))
    monkeypatch.setattr(yf, 'Ticker', lambda symbol: Ticker())
    key = 'market:account-closes:v1:MU:stock:2026-01-06'
    result = await account_performance.account_history('MU', 'stock', date(2026, 1, 6))
    assert result['points'] == []
    assert await cache.get(key) is None
    failed[0] = False
    result = await account_performance.account_history('MU', 'stock', date(2026, 1, 6))
    assert len(result['points']) == 2


@pytest.mark.asyncio
async def test_previously_cached_empty_or_invalid_history_is_evicted(monkeypatch):
    import yfinance as yf
    from app.core.redis_client import RedisClient
    from app.services import account_performance
    cache = RedisClient()
    async def get_cache(): return cache
    monkeypatch.setattr(account_performance, 'get_redis_client', get_cache)
    class Ticker:
        def history(self, **params):
            return pd.DataFrame({'Close': [100, 101]}, index=pd.to_datetime(['2025-12-31', '2026-01-02']))
    monkeypatch.setattr(yf, 'Ticker', lambda symbol: Ticker())
    key = 'market:account-closes:v1:MU:stock:2026-01-06'
    for points in [[], [('2025-12-31', float('nan'))], [('2025-12-31', 0)]]:
        await cache.set(key, {'points': points, 'splits': []}, ttl=900)
        result = await account_performance.account_history('MU', 'stock', date(2026, 1, 6))
        assert len(result['points']) == 2
