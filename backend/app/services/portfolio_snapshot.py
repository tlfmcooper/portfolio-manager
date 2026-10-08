"""Fast portfolio valuation using stored prices, without historical market calls."""
import asyncio
from datetime import datetime, timezone
import math

from app.services.exchange_rate_service import get_exchange_rate_service


def utc_timestamp(value):
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def stored_price(holding):
    candidates = []
    for price, timestamp in [(holding.current_price, holding.last_price_update),
                             (holding.asset.current_price, holding.asset.last_price_update)]:
        if price is not None and math.isfinite(price) and price > 0:
            candidates.append((price, utc_timestamp(timestamp)))
    if candidates:
        # Prefer the newest timestamped price; never attach another quote's date.
        price, timestamp = max(candidates, key=lambda item: item[1].timestamp() if item[1] else float('-inf'))
        return price, timestamp, False
    return holding.average_cost, None, True


async def build_portfolio_snapshot(portfolio, currency):
    holdings = [h for h in portfolio.holdings if h.is_active and h.quantity > 0]
    currencies = {portfolio.currency.upper()} | {
        (h.asset.currency or portfolio.currency).upper() for h in holdings
    }
    exchange = get_exchange_rate_service()

    async def rate_for(source):
        if source == currency:
            return source, 1.0
        # Never silently treat missing FX as parity in a valuation/planning tool.
        rate = await asyncio.wait_for(exchange.get_exchange_rate(source, currency, strict=True), timeout=4)
        if not math.isfinite(rate) or rate <= 0:
            raise ValueError("Exchange rate unavailable")
        return source, rate

    rates = dict(await asyncio.gather(*(rate_for(source) for source in currencies)))
    rows = []
    for h in holdings:
        asset_currency = (h.asset.currency or portfolio.currency).upper()
        rate = rates[asset_currency]
        price, price_date, estimated = stored_price(h)
        market_value = h.quantity * price * rate
        cost_basis = h.quantity * h.average_cost * rate
        rows.append({
            "id": h.id, "ticker": h.ticker, "name": h.asset.name or h.ticker,
            "sector": h.asset.sector or "Unclassified", "asset_type": h.asset.asset_type,
            "asset_currency": asset_currency, "quantity": h.quantity,
            "current_price": price * rate, "average_cost": h.average_cost * rate,
            "market_value": market_value, "cost_basis": cost_basis,
            "unrealized_gain_loss": market_value - cost_basis,
            "target_allocation": h.target_allocation,
            "price_as_of": price_date.isoformat() if price_date and not estimated else None,
            "price_source": "cost_basis_estimate" if estimated else "stored_quote",
        })
    cash = float(portfolio.cash_balance or 0) * rates[portfolio.currency.upper()]
    invested = sum(row["market_value"] for row in rows)
    cost = sum(row["cost_basis"] for row in rows)
    return {
        "portfolio_id": portfolio.id, "name": portfolio.name, "currency": currency,
        "cash_balance": cash, "holdings_value": invested, "total_value": invested + cash,
        "cost_basis": cost, "unrealized_gain_loss": invested - cost, "holdings": rows,
        "estimated_prices": sum(row["price_source"] == "cost_basis_estimate" for row in rows),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
