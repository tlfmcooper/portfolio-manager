from datetime import date, timedelta
from types import SimpleNamespace
import numpy as np
import pandas as pd
import pytest
import pytest_asyncio
from app.core.redis_client import get_redis_client
from app.schemas.scenario import ScenarioRequest
from app.services import portfolio_scenarios as scenarios
from test_portfolio_planning import planning_client


def history(ticker, kind):
    dates = pd.bdate_range(end=date.today() - timedelta(days=1), periods=180)
    returns = np.sin(np.arange(180) * (0.73 if ticker == 'AAA' else 0.31)) * (.01 if ticker == 'AAA' else .025) + .0005
    prices = 100 * np.cumprod(1 + returns) if '=X' not in ticker else np.full(180, 1.4)
    return {'points': [(str(day.date()), float(value)) for day, value in zip(dates, prices)], 'source': 'fixture', 'basis': 'price_only' if kind == 'mutual_fund' else 'adjusted_close'}


@pytest_asyncio.fixture
async def scenario_client(planning_client, monkeypatch):
    async def fetch(ticker, kind):
        return history(ticker, kind)
    monkeypatch.setattr(scenarios, 'historical_prices', fetch)
    cache = await get_redis_client()
    await cache.delete_prefix('portfolio:')
    yield planning_client


@pytest.mark.asyncio
async def test_scenario_recalculates_all_analytics_without_writing_holdings(scenario_client):
    client, headers, pid = scenario_client
    url = f'/api/v1/analysis/portfolios/{pid}/scenario'
    current = (await client.post(url, headers=headers, json={'preset': 'current', 'scenarios': 20, 'time_horizon': 30})).json()
    response = await client.post(url, headers=headers, json={'preset': 'custom', 'weights': {'weights': {'AAA': 0, 'BBB': 80, 'CASH': 20}}, 'scenarios': 20, 'time_horizon': 30})
    assert response.status_code == 200, response.text
    custom = response.json()
    assert custom['analysis_context']['weights'] == {'AAA': 0, 'BBB': 80, 'CASH': 20}
    assert current['analytics']['metrics']['portfolio_volatility_annualized'] != custom['analytics']['metrics']['portfolio_volatility_annualized']
    for kind, field in [('monte-carlo', 'final_mean'), ('cppi', 'final_cppi_value')]:
        assert current['analytics'][kind][field] != custom['analytics'][kind][field]
        assert custom['analytics'][kind]['initial_value'] == 1000
    assert custom['analytics']['cppi']['time_horizon'] == 30
    assert len(custom['analytics']['monte-carlo']['simulation_paths']) == 31
    assert current['analytics']['efficient-frontier']['special_portfolios']['selected'] != custom['analytics']['efficient-frontier']['special_portfolios']['selected']
    snapshot = (await client.get('/api/v1/portfolios/snapshot', headers=headers)).json()
    assert snapshot['cash_balance'] == 200
    assert [h['target_allocation'] for h in snapshot['holdings']] == [None, None]
    assert [h['quantity'] for h in snapshot['holdings']] == [6, 4]
    repeated = (await client.post(url, headers=headers, json={'preset': 'current', 'scenarios': 20, 'time_horizon': 30})).json()
    assert repeated == current
    reset = (await client.get(f'/api/v1/analysis/portfolios/{pid}/metrics', headers=headers)).json()
    assert reset['portfolio_volatility_annualized'] == current['analytics']['metrics']['portfolio_volatility_annualized']


@pytest.mark.asyncio
async def test_scenario_currency_cash_validation_and_ownership(scenario_client):
    client, headers, pid = scenario_client
    url = f'/api/v1/analysis/portfolios/{pid}/scenario'
    msr = (await client.post(url, headers=headers, json={'preset': 'msr', 'currency': 'CAD', 'kind': 'metrics'})).json()
    assert msr['analysis_context']['weights']['CASH'] == 20
    assert msr['analysis_context']['portfolio_total_value'] == 1400
    assert abs(sum(msr['analysis_context']['weights'].values()) - 100) < 1e-6
    assert (await client.post(url, json={})).status_code == 401
    for request in [ {'preset': 'custom'}, {'preset': 'current', 'weights': {'weights': {'CASH': 100}}},
                     {'preset': 'custom', 'weights': {'weights': {'UNKNOWN': 80, 'CASH': 20}}},
                     {'preset': 'custom', 'weights': {'weights': {'AAA': 99, 'CASH': 0}}},
                     {'currency': 'EUR'}, {'scenarios': 10000, 'time_horizon': 2520}]:
        assert (await client.post(url, headers=headers, json=request)).status_code == 422
    from app.core.security import create_access_token
    other = {'Authorization': f"Bearer {create_access_token({'sub': 'other'})}"}
    assert (await client.post(url, headers=other, json={})).status_code == 404


@pytest.mark.asyncio
async def test_fund_and_crypto_history_are_included_and_fx_affects_returns(monkeypatch):
    seen = []
    async def fetch(ticker, kind):
        seen.append((ticker, kind))
        data = history(ticker, kind)
        if '=X' in ticker:
            data['points'] = [(day, value * (1 + i / 10000)) for i, (day, value) in enumerate(data['points'])]
        return data
    monkeypatch.setattr(scenarios, 'historical_prices', fetch)
    snapshot = {'currency': 'USD', 'holdings': [
        {'ticker': 'PHN9756.CF', 'asset_type': 'mutual_fund', 'asset_currency': 'CAD'},
        {'ticker': 'BTC', 'asset_type': 'crypto', 'asset_currency': 'USD'}]}
    data = await scenarios.build_dataset(snapshot)
    assert set(data['returns']) == {'PHN9756.CF', 'BTC'}
    assert ('CADUSD=X', 'fx') in seen
    assert all(row['available'] for row in data['coverage'])
    assert data['returns']['PHN9756.CF'] != data['returns']['BTC']


@pytest.mark.asyncio
async def test_native_fund_and_crypto_providers_are_used(monkeypatch):
    cache = await get_redis_client()
    await cache.delete_prefix('market:scenario-history:')
    calls = []
    async def fund(ticker, **kwargs):
        calls.append(ticker)
        return [{'raw': {'tradeTime': '2026-01-02', 'lastPrice': 10}}, {'raw': {'tradeTime': '2026-01-05', 'lastPrice': 11}}]
    def yahoo(self, ticker, *args):
        calls.append(ticker)
        return pd.DataFrame({'Close': [100., 110.]}, index=pd.to_datetime(['2026-01-02', '2026-01-05']))
    monkeypatch.setattr(scenarios.FinanceService, '_get_mutual_fund_history', fund)
    monkeypatch.setattr(scenarios.YFinanceProvider, 'get_price_data', yahoo)
    fund_result = await scenarios.historical_prices('TEST.CF', 'mutual_fund')
    crypto_result = await scenarios.historical_prices('BTC', 'crypto')
    assert calls == ['TEST.CF', 'BTC-USD']
    assert fund_result['basis'] == 'price_only'
    assert crypto_result['points'][-1][1] == 110


@pytest.mark.asyncio
async def test_returns_span_the_same_dates_across_market_holidays(monkeypatch):
    monkeypatch.setattr(scenarios, 'MIN_OBSERVATIONS', 1)
    async def fetch(ticker, kind):
        points = [('2026-01-02', 100), ('2026-01-06', 121)]
        if ticker == 'AAA':
            points.insert(1, ('2026-01-05', 110))
        return {'points': points, 'source': 'fixture', 'basis': 'adjusted_close'}
    monkeypatch.setattr(scenarios, 'historical_prices', fetch)
    data = await scenarios.build_dataset({'currency': 'USD', 'holdings': [
        {'ticker': ticker, 'asset_type': 'stock', 'asset_currency': 'USD'} for ticker in ['AAA', 'BBB']]})
    assert data['dates'] == ['2026-01-06']
    assert data['returns']['AAA'] == pytest.approx([.21])
    assert data['returns']['BBB'] == pytest.approx([.21])


def prepared_service(missing=False):
    service = scenarios.PortfolioScenarioService(1, None, 'USD')
    frame = pd.DataFrame({'AAA': np.sin(np.arange(100)) * .01 + .001, 'BBB': np.cos(np.arange(100)) * .02 + .001}, index=pd.bdate_range('2026-01-01', periods=100))
    service.frame = frame
    service.snapshot = {'currency': 'USD', 'total_value': 1000}
    service.actual = {'AAA': .4, 'BBB': .3, 'CASH': .1, **({'MISSING': .2} if missing else {'OTHER': .2})}
    service.revision = 'test'
    service.dataset = {'dates': [str(day.date()) for day in frame.index], 'coverage': [
        {'ticker': ticker, 'available': ticker in frame, 'return_basis': 'adjusted_close', 'reason': 'No history' if ticker not in frame else None} for ticker in service.actual if ticker != 'CASH']}
    return service


def test_msr_keeps_unavailable_assets_fixed_and_simulations_model_only_covered_value():
    service = prepared_service(missing=True)
    weights = service.resolve_weights('msr')
    assert weights['MISSING'] == .2 and weights['CASH'] == .1
    assert sum(weights.values()) == pytest.approx(1)
    result = service.compute('monte-carlo', weights, 'msr', {'scenarios': 30, 'time_horizon': 10})
    assert result['initial_value'] == pytest.approx(800)
    assert result['analysis_context']['coverage_percentage'] == pytest.approx(80)
    # Separate generators give exactly the same stochastic draws without cache/global RNG.
    assert result == service.compute('monte-carlo', weights, 'msr', {'scenarios': 30, 'time_horizon': 10})


def test_daily_cppi_safe_rate_and_distinct_horizon():
    service = prepared_service()
    result = service.compute('cppi', service.actual, 'current', {'floor': 1., 'time_horizon': 80, 'cppi_time_horizon': 10})
    assert result['time_horizon'] == 10
    assert result['performance_data'][0]['risky_allocation'] == 0
    assert result['performance_data'][0]['cppi_wealth'] == pytest.approx(result['initial_value'] * (1 + scenarios.RISK_FREE_RATE) ** (1 / 252))
