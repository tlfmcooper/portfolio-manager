"""Daily account performance from recorded trades, cash flows and historical closes.

The allocation scenario engine deliberately remains a separate what-if model.
"""
import asyncio
import re
from datetime import date, timedelta

import numpy as np
import pandas as pd
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.crud.portfolio import get_portfolio
from app.models import Transaction
from app.core.redis_client import get_redis_client
from app.services.portfolio_analysis import AdvancedPortfolioAnalytics
from app.services.portfolio_scenarios import historical_prices, price_series, RISK_FREE_RATE


class IncompleteAccountHistory(ValueError):
    pass


async def account_history(ticker, kind, today):
    """Use quoted closes for ledger valuation, not dividend-reinvested prices."""
    if kind == 'mutual_fund' or ticker.upper().endswith('.CF'):
        return {**await historical_prices(ticker, kind), 'splits': []}
    cache = await get_redis_client()
    key = f'market:account-closes:v1:{ticker}:{kind}:{today}'

    def usable(payload):
        try:
            return bool(payload) and not payload.get('error') and not price_series(payload['points']).empty
        except (KeyError, TypeError, ValueError):
            return False

    # Older releases cached an empty provider response for the success TTL.
    cached = await cache.get(key)
    if cached is not None and not usable(cached):
        await cache.delete(key)

    async def load():
        import yfinance as yf
        symbol = ticker
        if kind in {'crypto', 'cryptocurrency'} and '-' not in symbol:
            symbol = symbol.upper() + '-USD'
        def fetch():
            frame = yf.Ticker(symbol).history(start=date(today.year - 1, 12, 20),
                end=today + timedelta(days=1), auto_adjust=False, actions=True, timeout=10)
            # Yahoo sometimes returns an empty frame instead of raising on an outage.
            prices = price_series([(str(day.date()), value) for day, value in frame['Close'].items()])
            return {'points': [(str(day.date()), float(value)) for day, value in prices.items()],
                'splits': [(str(day.date()), float(value)) for day, value in frame.get('Stock Splits', pd.Series(dtype=float)).items() if value > 0]}
        for attempt in range(2):
            try:
                payload = await asyncio.to_thread(fetch)
                if usable(payload):
                    return payload
            except Exception:
                pass
            if attempt == 0:
                await asyncio.sleep(0.25)
        # RedisClient deliberately does not cache results marked as errors.
        return {'points': [], 'splits': [], 'error': 'Historical price provider temporarily unavailable'}
    return await cache.get_or_load(key, load, 900)


def normalized_trades(events, histories):
    """Yahoo closes are split-adjusted; put historical share trades on that basis."""
    normalized = []
    for event in events:
        tx = dict(event)
        if tx['kind'] in {'BUY', 'SELL'}:
            factor = np.prod([ratio for day, ratio in histories[tx['ticker']]['splits']
                              if day > str(tx['date'])])
            tx['quantity'] *= float(factor)
        normalized.append(tx)
    return normalized


def account_returns(*, quantities, cash, transactions, prices, fx, portfolio_currency,
                    display_currency, start, end):
    """Rewind today's ledger, then value only positions held on each date.

    External flows use the end-of-day convention. Weekend flows are removed
    from the next valuation interval. Missing prices are never zero-filled.
    """
    def rate(currency, day):
        if currency == display_currency:
            return 1.0
        return close(fx.get(currency), day, f'{currency}/{display_currency} FX')

    def close(series, day, label):
        if series is None or series.empty:
            raise IncompleteAccountHistory(f'Missing history for {label} on {day}')
        known = series.loc[:pd.Timestamp(day)].dropna()
        if known.empty or (pd.Timestamp(day) - known.index[-1]).days > 7:
            raise IncompleteAccountHistory(f'Missing history for {label} on {day}')
        value = float(known.iloc[-1])
        if not np.isfinite(value) or value <= 0:
            raise IncompleteAccountHistory(f'Invalid history for {label} on {day}')
        return value

    def cash_change(tx):
        # Cash is recorded in the portfolio's base currency. Dated FX is used
        # because legacy trades do not persist their executed conversion rate.
        amount = tx['amount'] * rate(tx['currency'], tx['date']) / rate(portfolio_currency, tx['date'])
        return amount if tx['kind'] in {'SELL', 'DEPOSIT'} else -amount

    positions = dict(quantities)
    ledger_cash = float(cash)
    relevant = [tx for tx in transactions if tx['date'] > start]
    # Include trades after the final completed close when rewinding current state.
    for tx in reversed(relevant):
        ledger_cash -= cash_change(tx)
        if tx['kind'] in {'BUY', 'SELL'}:
            positions[tx['ticker']] = positions.get(tx['ticker'], 0) + tx['quantity'] * (-1 if tx['kind'] == 'BUY' else 1)

    def valuation(day):
        value = ledger_cash * rate(portfolio_currency, day)
        for ticker, quantity in positions.items():
            if quantity < -1e-6:
                raise IncompleteAccountHistory(f'Trades imply a negative holding for {ticker} on {day}')
            if quantity > 1e-6:
                payload = prices[ticker]
                value += quantity * close(payload['prices'], day, ticker) * rate(payload['currency'], day)
        if not np.isfinite(value) or value <= 0:
            raise IncompleteAccountHistory(f'No positive account value on {day}')
        return value

    previous = valuation(start)
    opening_value = previous
    by_date = {}
    for tx in relevant:
        by_date.setdefault(tx['date'], []).append(tx)
    flow = total_flows = 0.0
    values, returns, dates = [], [], []
    for timestamp in pd.date_range(start + timedelta(days=1), end):
        day = timestamp.date()
        for tx in by_date.get(day, []):
            ledger_cash += cash_change(tx)
            if tx['kind'] in {'BUY', 'SELL'}:
                positions[tx['ticker']] = positions.get(tx['ticker'], 0) + tx['quantity'] * (1 if tx['kind'] == 'BUY' else -1)
            else:
                external = tx['amount'] * rate(tx['currency'], day) * (1 if tx['kind'] == 'DEPOSIT' else -1)
                flow += external
                total_flows += external
        # Use completed weekday market sessions, not today's partial quotes.
        if timestamp.dayofweek >= 5:
            continue
        active = [payload['prices'] for ticker, payload in prices.items() if positions.get(ticker, 0) > 1e-6]
        if active and not any(timestamp in series.index for series in active):
            continue
        current = valuation(day)
        daily_return = (current - flow) / previous - 1
        if not np.isfinite(daily_return) or daily_return <= -1:
            raise IncompleteAccountHistory(f'Cash flows or valuations cannot be reconciled on {day}')
        dates.append(timestamp)
        returns.append(daily_return)
        values.append(current)
        previous, flow = current, 0.0
    if len(returns) < 2:
        raise IncompleteAccountHistory('At least two completed daily returns are required')
    return pd.Series(returns, index=dates), {'opening_value': opening_value, 'closing_value': values[-1],
        'net_external_flows': total_flows, 'valuation_start': str(start), 'valuation_end': str(dates[-1].date())}


async def calculate_account_performance(portfolio_id, db, currency=None, as_of=None):
    portfolio = await get_portfolio(db, portfolio_id)
    if portfolio is None:
        raise HTTPException(404, 'Portfolio not found')
    today = as_of or date.today()
    start = date(today.year - 1, 12, 31)
    end = today - timedelta(days=1)
    display = currency or portfolio.currency
    result = await db.execute(select(Transaction).options(selectinload(Transaction.asset)).where(
        Transaction.portfolio_id == portfolio_id).order_by(Transaction.transaction_date, Transaction.id))
    recorded = list(result.scalars())
    assets = {h.ticker: h.asset for h in portfolio.holdings}
    quantities = {h.ticker: float(h.quantity or 0) for h in portfolio.holdings}
    events = []
    for tx in recorded:
        if tx.transaction_date.date() <= start:
            continue
        kind = tx.transaction_type.value
        if kind in {'BUY', 'SELL'}:
            if tx.asset is None:
                raise HTTPException(422, 'A recorded trade is missing its asset')
            ticker = tx.asset.ticker
            assets[ticker] = tx.asset
            events.append({'date': tx.transaction_date.date(), 'kind': kind, 'ticker': ticker,
                'quantity': float(tx.quantity or 0), 'amount': float(tx.quantity or 0) * tx.price,
                'currency': tx.asset.currency or portfolio.currency})
        else:
            match = re.search(r'\[Currency:\s*([A-Z]{3})\]', tx.notes or '')
            events.append({'date': tx.transaction_date.date(), 'kind': kind, 'amount': tx.price,
                'currency': match.group(1) if match else portfolio.currency})
    semaphore = asyncio.Semaphore(4)

    async def fetch(ticker, kind):
        async with semaphore:
            return await account_history(ticker, kind, today)

    currencies = {portfolio.currency} | {a.currency or portfolio.currency for a in assets.values()} | {t['currency'] for t in events}
    tasks = {ticker: asyncio.create_task(fetch(ticker, asset.asset_type)) for ticker, asset in assets.items()}
    fx_tasks = {source: asyncio.create_task(fetch(source + display + '=X', 'fx')) for source in currencies if source != display}
    histories = {ticker: await task for ticker, task in tasks.items()}
    events = normalized_trades(events, histories)
    prices = {ticker: {'prices': price_series(histories[ticker]['points']), 'currency': asset.currency or portfolio.currency}
              for ticker, asset in assets.items()}
    fx = {source: price_series((await task)['points']) for source, task in fx_tasks.items()}
    try:
        returns, facts = account_returns(quantities=quantities, cash=portfolio.cash_balance or 0,
            transactions=events, prices=prices, fx=fx, portfolio_currency=portfolio.currency,
            display_currency=display, start=start, end=end)
    except IncompleteAccountHistory as exc:
        raise HTTPException(422, f'Account YTD performance unavailable: {exc}') from exc
    engine = AdvancedPortfolioAnalytics(portfolio_id, db, display)
    metrics = engine._compute_metrics_from_returns(returns, {}, {}, facts['closing_value'])
    for field in ('number_of_positions', 'concentration_risk', 'individual_performance'):
        metrics.pop(field, None)
    metrics.update({'ytd_return_percentage': float((1 + returns).prod() - 1) * 100,
        'ytd_complete': True, 'performance_basis': 'account_ytd', 'account_valuation': facts,
        'analysis_context': {'method': 'account_ytd', 'holdings': [], 'coverage_percentage': 100.0,
            'observations': len(returns), 'history_start': str(returns.index[0].date()),
            'history_end': facts['valuation_end'], 'risk_free_rate': RISK_FREE_RATE,
            'notes': ['Account YTD returns use recorded positions, trades and cash flows, through the last completed market session.',
                'Deposits and withdrawals are removed using an end-of-day cash-flow convention; intraday timing is approximated.',
                'Trade FX uses historical daily rates because executed conversion rates were not recorded.',
                'Account history uses quoted closes and fund NAVs; dividends, distributions and fees absent from the ledger are excluded.']}})
    return metrics
