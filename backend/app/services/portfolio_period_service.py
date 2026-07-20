"""Build normalized historical inputs for portfolio period analysis."""

from __future__ import annotations

import asyncio
import re
from collections import defaultdict
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.asset import Asset
from app.models.holding import Holding
from app.models.transaction import Transaction, TransactionType
from app.services.exchange_rate_service import get_exchange_rate_service
from app.services.finance_service import FinanceService


_CURRENCY_NOTE = re.compile(r"\[Currency:\s*([A-Za-z]{3})\]")


def _transaction_type(transaction: Transaction) -> str:
    value = transaction.transaction_type
    return str(getattr(value, "value", value)).upper()


def _cash_transaction_currency(transaction: Transaction, portfolio_currency: str) -> str:
    match = _CURRENCY_NOTE.search(transaction.notes or "")
    return match.group(1).upper() if match else portfolio_currency


def _quantity_at(
    current_quantity: float,
    transactions: list[Transaction],
    boundary: date,
) -> float:
    quantity = float(current_quantity or 0)
    for transaction in transactions:
        transaction_date = transaction.transaction_date
        if not transaction_date or transaction_date.date() <= boundary:
            continue
        transaction_quantity = float(transaction.quantity or 0)
        kind = _transaction_type(transaction)
        if kind == TransactionType.BUY.value:
            quantity -= transaction_quantity
        elif kind == TransactionType.SELL.value:
            quantity += transaction_quantity
    return max(quantity, 0.0)


async def build_portfolio_period_inputs(
    db,
    portfolio,
    start_date: date,
    end_date: date,
    currency: str,
) -> dict[str, Any]:
    """Return historical portfolio facts without calculating the final return."""
    holdings_result = await db.execute(
        select(Holding)
        .options(selectinload(Holding.asset))
        .where(Holding.portfolio_id == portfolio.id)
    )
    holdings = list(holdings_result.scalars().all())

    transactions_result = await db.execute(
        select(Transaction)
        .options(selectinload(Transaction.asset))
        .where(Transaction.portfolio_id == portfolio.id)
        .order_by(Transaction.transaction_date)
    )
    transactions = list(transactions_result.scalars().all())

    holdings_by_asset = {holding.asset_id: holding for holding in holdings}
    assets: dict[int, Asset] = {
        holding.asset_id: holding.asset
        for holding in holdings
        if holding.asset is not None
    }
    transactions_by_asset: dict[int, list[Transaction]] = defaultdict(list)
    for transaction in transactions:
        if transaction.asset_id is not None:
            transactions_by_asset[transaction.asset_id].append(transaction)
            if transaction.asset is not None:
                assets[transaction.asset_id] = transaction.asset

    exchange_service = get_exchange_rate_service()
    price_tasks = {
        asset_id: asyncio.create_task(
            FinanceService.get_price_points(
                asset.ticker,
                start_date,
                end_date,
                asset.asset_type,
            )
        )
        for asset_id, asset in assets.items()
    }
    asset_currencies = {
        (asset.currency or portfolio.currency).upper() for asset in assets.values()
    }
    fx_tasks = {
        (asset_currency, boundary): asyncio.create_task(
            exchange_service.get_historical_exchange_rate(
                asset_currency,
                currency,
                boundary,
            )
        )
        for asset_currency in asset_currencies
        for boundary in (start_date, end_date)
    }

    price_points = {
        asset_id: await task for asset_id, task in price_tasks.items()
    }
    fx_points = {key: await task for key, task in fx_tasks.items()}

    coverage_issues: list[dict[str, Any]] = []
    asset_rows: list[dict[str, Any]] = []
    opening_securities_value = 0.0
    closing_securities_value = 0.0
    priced_assets = 0

    for asset_id, asset in sorted(assets.items(), key=lambda item: item[1].ticker):
        holding = holdings_by_asset.get(asset_id)
        asset_transactions = transactions_by_asset.get(asset_id, [])
        current_quantity = float(holding.quantity or 0) if holding else 0.0
        opening_quantity = _quantity_at(current_quantity, asset_transactions, start_date)
        closing_quantity = _quantity_at(current_quantity, asset_transactions, end_date)

        points = price_points[asset_id]
        start_point = points.get("start")
        end_point = points.get("end")
        asset_currency = (asset.currency or portfolio.currency).upper()
        start_fx = fx_points[(asset_currency, start_date)]
        end_fx = fx_points[(asset_currency, end_date)]
        opening_value = (
            opening_quantity * float(start_point["close"]) * float(start_fx["rate"])
            if start_point
            else None
        )
        closing_value = (
            closing_quantity * float(end_point["close"]) * float(end_fx["rate"])
            if end_point
            else None
        )

        if opening_value is not None and closing_value is not None:
            priced_assets += 1
            opening_securities_value += opening_value
            closing_securities_value += closing_value
        else:
            coverage_issues.append(
                {
                    "type": "missing_price_history",
                    "ticker": asset.ticker,
                    "message": "Opening or closing price history is unavailable.",
                }
            )
        if not start_fx["is_historical"] or not end_fx["is_historical"]:
            coverage_issues.append(
                {
                    "type": "current_fx_fallback",
                    "ticker": asset.ticker,
                    "message": (
                        f"Historical {asset_currency}/{currency} FX was unavailable; "
                        "a current rate was used."
                    ),
                }
            )

        period_trades = []
        buys_value = 0.0
        sells_value = 0.0
        for transaction in asset_transactions:
            transaction_date = transaction.transaction_date
            if (
                not transaction_date
                or transaction_date.date() <= start_date
                or transaction_date.date() > end_date
            ):
                continue
            kind = _transaction_type(transaction)
            transaction_value = float(transaction.quantity or 0) * float(transaction.price or 0)
            # Use the period-end FX rate as a clearly disclosed approximation when
            # a dated transaction FX rate was not persisted by the legacy schema.
            converted_value = transaction_value * float(end_fx["rate"])
            if kind == TransactionType.BUY.value:
                buys_value += converted_value
            elif kind == TransactionType.SELL.value:
                sells_value += converted_value
            period_trades.append(
                {
                    "id": transaction.id,
                    "date": transaction_date.isoformat(),
                    "type": kind,
                    "quantity": transaction.quantity,
                    "price": transaction.price,
                    "currency": asset_currency,
                    "value": transaction_value,
                    "value_in_display_currency": converted_value,
                    "fx_method": "period_end_rate",
                }
            )

        period_pnl = (
            closing_value - opening_value - buys_value + sells_value
            if opening_value is not None and closing_value is not None
            else None
        )
        asset_rows.append(
            {
                "ticker": asset.ticker,
                "name": asset.name,
                "asset_type": asset.asset_type,
                "asset_currency": asset_currency,
                "opening_quantity": opening_quantity,
                "closing_quantity": closing_quantity,
                "opening_price": start_point,
                "closing_price": end_point,
                "opening_fx": start_fx,
                "closing_fx": end_fx,
                "opening_value": opening_value,
                "closing_value": closing_value,
                "buys_value": buys_value,
                "sells_value": sells_value,
                "period_pnl": period_pnl,
                "price_source": points.get("source"),
                "trades": period_trades,
            }
        )

    external_cash_flows: list[dict[str, Any]] = []
    net_external_flows = 0.0
    period_days = max((end_date - start_date).days, 1)
    for transaction in transactions:
        transaction_date = transaction.transaction_date
        kind = _transaction_type(transaction)
        if (
            kind not in {TransactionType.DEPOSIT.value, TransactionType.WITHDRAWAL.value}
            or not transaction_date
            or transaction_date.date() <= start_date
            or transaction_date.date() > end_date
        ):
            continue
        flow_currency = _cash_transaction_currency(transaction, portfolio.currency)
        flow_fx = await exchange_service.get_historical_exchange_rate(
            flow_currency,
            currency,
            transaction_date.date(),
        )
        signed_amount = float(transaction.price or 0) * (
            1 if kind == TransactionType.DEPOSIT.value else -1
        )
        converted_amount = signed_amount * float(flow_fx["rate"])
        elapsed_days = (transaction_date.date() - start_date).days
        weight = max(0.0, min(1.0, (period_days - elapsed_days) / period_days))
        net_external_flows += converted_amount
        external_cash_flows.append(
            {
                "id": transaction.id,
                "date": transaction_date.isoformat(),
                "type": kind,
                "amount": abs(float(transaction.price or 0)),
                "currency": flow_currency,
                "signed_amount_in_display_currency": converted_amount,
                "modified_dietz_weight": weight,
                "fx": flow_fx,
            }
        )
        if not flow_fx["is_historical"]:
            coverage_issues.append(
                {
                    "type": "current_fx_fallback",
                    "transaction_id": transaction.id,
                    "message": "Historical cash-flow FX was unavailable; a current rate was used.",
                }
            )

    fx_cache: dict[tuple[str, date], dict[str, Any]] = {}

    async def transaction_cash_impact(transaction: Transaction) -> float:
        transaction_date = transaction.transaction_date
        if not transaction_date:
            return 0.0
        kind = _transaction_type(transaction)
        if kind in {TransactionType.BUY.value, TransactionType.SELL.value}:
            asset = transaction.asset
            transaction_currency = (
                asset.currency if asset and asset.currency else portfolio.currency
            ).upper()
            amount = float(transaction.quantity or 0) * float(transaction.price or 0)
            direction = -1 if kind == TransactionType.BUY.value else 1
        elif kind in {
            TransactionType.DEPOSIT.value,
            TransactionType.WITHDRAWAL.value,
        }:
            transaction_currency = _cash_transaction_currency(
                transaction, portfolio.currency
            )
            amount = float(transaction.price or 0)
            direction = 1 if kind == TransactionType.DEPOSIT.value else -1
        else:
            return 0.0

        cache_key = (transaction_currency, transaction_date.date())
        if cache_key not in fx_cache:
            fx_cache[cache_key] = await exchange_service.get_historical_exchange_rate(
                transaction_currency,
                currency,
                transaction_date.date(),
            )
        fx = fx_cache[cache_key]
        if not fx["is_historical"] and transaction_currency != currency:
            coverage_issues.append(
                {
                    "type": "current_fx_fallback",
                    "transaction_id": transaction.id,
                    "message": (
                        "Historical transaction FX was unavailable; a current rate "
                        "was used to reconstruct cash."
                    ),
                }
            )
        return direction * amount * float(fx["rate"])

    current_cash = float(portfolio.cash_balance or 0)

    async def cash_at(boundary: date) -> float:
        later_impacts = [
            await transaction_cash_impact(transaction)
            for transaction in transactions
            if transaction.transaction_date
            and transaction.transaction_date.date() > boundary
        ]
        return current_cash - sum(later_impacts)

    opening_cash, closing_cash = await asyncio.gather(
        cash_at(start_date),
        cash_at(end_date),
    )
    coverage_issues.append(
        {
            "type": "cash_reconstructed",
            "message": (
                "Historical cash balances were reconstructed from the transaction "
                "ledger because daily cash snapshots are not persisted."
            ),
        }
    )
    coverage_issues.append(
        {
            "type": "dividend_ledger_unavailable",
            "message": "Dividend and fee events are not recorded in the transaction ledger.",
        }
    )

    opening_total = (
        opening_securities_value + opening_cash if opening_cash is not None else None
    )
    closing_total = (
        closing_securities_value + closing_cash if closing_cash is not None else None
    )
    start_dates = sorted(
        {
            row["opening_price"]["date"]
            for row in asset_rows
            if row["opening_price"] is not None
        }
    )
    end_dates = sorted(
        {
            row["closing_price"]["date"]
            for row in asset_rows
            if row["closing_price"] is not None
        }
    )

    return {
        "requested_period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "timezone": "America/Toronto",
        },
        "effective_period": {
            "start_dates": start_dates,
            "end_dates": end_dates,
        },
        "currency": currency,
        "opening": {
            "securities_value": opening_securities_value,
            "cash_balance": opening_cash,
            "total_value": opening_total,
        },
        "closing": {
            "securities_value": closing_securities_value,
            "cash_balance": closing_cash,
            "total_value": closing_total,
        },
        "assets": asset_rows,
        "external_cash_flows": external_cash_flows,
        "net_external_cash_flow": net_external_flows,
        "calculation_contract": {
            "method": "modified_dietz",
            "numerator": "closing_total - opening_total - net_external_cash_flow",
            "denominator": (
                "opening_total + sum(signed_amount_in_display_currency * "
                "modified_dietz_weight)"
            ),
            "asset_period_pnl": (
                "closing_value - opening_value - buys_value + sells_value"
            ),
            "instruction": (
                "Calculate in the code interpreter. Do not claim an exact portfolio "
                "return when opening_total or closing_total is null."
            ),
        },
        "coverage": {
            "complete": not coverage_issues,
            "priced_assets": priced_assets,
            "total_assets": len(asset_rows),
            "issues": coverage_issues,
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
