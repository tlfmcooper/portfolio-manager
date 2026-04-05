from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any, Awaitable, Callable, Dict, Iterable


PortfolioPerformanceFetcher = Callable[[str, str | None], Awaitable[Dict[str, Any]]]


def _coerce_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _parse_currency_from_notes(notes: str | None, default_currency: str) -> str:
    if not notes:
        return default_currency

    match = re.search(r"\[Currency:\s*([A-Z]{3})\]", notes)
    if not match:
        return default_currency
    return match.group(1).upper()


def _convert_amount(
    amount: float,
    from_currency: str,
    to_currency: str,
    exchange_rates: Dict[str, float],
) -> float:
    if from_currency == to_currency:
        return amount
    rate = exchange_rates.get(from_currency)
    if rate is None:
        return amount
    return amount * rate


async def calculate_portfolio_ytd_metrics(
    *,
    current_holdings: Iterable[Dict[str, Any]],
    transactions: Iterable[Dict[str, Any]],
    current_cash_balance: float,
    portfolio_currency: str,
    display_currency: str,
    exchange_rates: Dict[str, float],
    performance_fetcher: PortfolioPerformanceFetcher,
    as_of: datetime | None = None,
) -> Dict[str, Any]:
    current_time = _coerce_utc(as_of) or datetime.now(timezone.utc)
    year_start = datetime(current_time.year, 1, 1, tzinfo=timezone.utc)

    positions: Dict[str, Dict[str, Any]] = {}
    start_quantities: Dict[str, float] = {}

    current_holdings_value = 0.0
    for holding in current_holdings:
        ticker = str(holding.get("ticker") or "").upper().strip()
        if not ticker:
            continue

        quantity = float(holding.get("quantity") or 0.0)
        current_price = holding.get("current_price")
        current_price = float(current_price) if current_price is not None else None
        market_value = float(holding.get("market_value") or 0.0)
        current_holdings_value += market_value

        positions[ticker] = {
            "quantity": quantity,
            "current_price": current_price,
            "asset_type": holding.get("asset_type"),
            "currency": str(holding.get("currency") or portfolio_currency).upper(),
        }
        start_quantities[ticker] = quantity

    external_flows = 0.0
    buy_spend = 0.0
    sell_proceeds = 0.0

    for transaction in transactions:
        transaction_date = _coerce_utc(transaction.get("transaction_date"))
        if not transaction_date or transaction_date < year_start:
            continue

        transaction_type = str(transaction.get("transaction_type") or "").upper()
        ticker = str(transaction.get("asset_ticker") or "").upper().strip()
        quantity = float(transaction.get("quantity") or 0.0)
        price = float(transaction.get("price") or 0.0)

        if transaction_type in {"BUY", "SELL"} and ticker:
            asset_currency = str(transaction.get("asset_currency") or portfolio_currency).upper()
            amount = _convert_amount(quantity * price, asset_currency, display_currency, exchange_rates)

            position = positions.setdefault(
                ticker,
                {
                    "quantity": 0.0,
                    "current_price": None,
                    "asset_type": transaction.get("asset_type"),
                    "currency": asset_currency,
                },
            )
            if not position.get("asset_type") and transaction.get("asset_type"):
                position["asset_type"] = transaction.get("asset_type")
            if not position.get("currency"):
                position["currency"] = asset_currency

            if transaction_type == "BUY":
                start_quantities[ticker] = start_quantities.get(ticker, 0.0) - quantity
                buy_spend += amount
            else:
                start_quantities[ticker] = start_quantities.get(ticker, 0.0) + quantity
                sell_proceeds += amount
            continue

        if transaction_type in {"DEPOSIT", "WITHDRAWAL"}:
            transaction_currency = _parse_currency_from_notes(transaction.get("notes"), portfolio_currency)
            amount = _convert_amount(price, transaction_currency, display_currency, exchange_rates)
            external_flows += amount if transaction_type == "DEPOSIT" else -amount

    start_cash_balance = current_cash_balance + buy_spend - sell_proceeds - external_flows

    start_holdings_value = 0.0
    missing_tickers: list[str] = []

    for ticker, quantity in start_quantities.items():
        if quantity <= 1e-9:
            continue

        position = positions.get(ticker, {})
        perf_data = await performance_fetcher(ticker, position.get("asset_type"))
        ytd_return = perf_data.get("ytd_return")
        current_price = position.get("current_price")

        if current_price is None:
            fetched_price = perf_data.get("current_price")
            if fetched_price is not None:
                current_price = _convert_amount(
                    float(fetched_price),
                    str(position.get("currency") or portfolio_currency).upper(),
                    display_currency,
                    exchange_rates,
                )

        historical_data_available = bool(perf_data.get("historical_data_available", ytd_return is not None))
        if not historical_data_available or ytd_return is None or current_price in (None, 0):
            missing_tickers.append(ticker)
            continue

        start_price = float(current_price) / (1 + (float(ytd_return) / 100))
        start_holdings_value += quantity * start_price

    if missing_tickers:
        missing_tickers = sorted(set(missing_tickers))
        return {
            "ytd_return_percentage": None,
            "ytd_gain": None,
            "ytd_complete": False,
            "ytd_missing_tickers": missing_tickers,
            "ytd_message": (
                "Exact YTD return is unavailable because year-start price history is missing for: "
                + ", ".join(missing_tickers)
            ),
        }

    start_total_value = start_holdings_value + start_cash_balance
    current_total_value = current_holdings_value + current_cash_balance
    if start_total_value <= 0:
        return {
            "ytd_return_percentage": None,
            "ytd_gain": None,
            "ytd_complete": False,
            "ytd_missing_tickers": [],
            "ytd_message": "Exact YTD return is unavailable because the portfolio had no positive starting value this year.",
        }

    ytd_gain = current_total_value - start_total_value - external_flows
    ytd_return_percentage = (ytd_gain / start_total_value) * 100
    return {
        "ytd_return_percentage": ytd_return_percentage,
        "ytd_gain": ytd_gain,
        "ytd_complete": True,
        "ytd_missing_tickers": [],
        "ytd_message": None,
    }