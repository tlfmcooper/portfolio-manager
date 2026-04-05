"""Typed MCP capability handlers backed by the portfolio domain services."""

from __future__ import annotations

import json
import csv
import io
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.mcp.errors import invalid_params, not_found, unauthorized, upstream_error
from app.mcp.models import PromptMessage, PromptResult, ResourceContent, ResourceReadResult, SamplingResult, TextContent, ToolResult
from app.mcp.session_store import session_store
from app.schemas import HoldingCreate, HoldingInDB, HoldingUpdate, MCPAPIKeyCreateRequest
from app.schemas.holding_extended import AssetSellRequest
from app.schemas.transaction import CashTransactionCreate


@dataclass(slots=True)
class HandlerContext:
    db: AsyncSession
    auth: Any
    request_id: str
    rpc_method: str
    session_id: str | None = None


def _tool_result(text: str, data: Any = None, ui: Dict[str, Any] | None = None) -> ToolResult:
    meta = {}
    if ui:
        meta = {"ui": ui}
    return ToolResult(
        content=[TextContent(text=text).model_dump()],
        structuredContent=data,
        _meta=meta,
    )


def _normalize_http_error(exc: HTTPException) -> None:
    if exc.status_code == 404:
        raise not_found(message=str(exc.detail)) from exc
    raise invalid_params(message=str(exc.detail)) from exc


async def _get_current_user(ctx: HandlerContext):
    from app.crud import get_user_by_username

    if not getattr(ctx.auth, "username", None):
        raise unauthorized(
            message="Authenticated MCP requests for portfolio tools must include a user-bound bearer token or an API key configured with a username"
        )

    user = await get_user_by_username(ctx.db, ctx.auth.username)
    if not user or not user.is_active:
        raise unauthorized(message="Authenticated MCP user was not found or is inactive")

    return user


async def _get_current_portfolio(ctx: HandlerContext):
    from app.crud import get_user_portfolio

    user = await _get_current_user(ctx)
    portfolio = await get_user_portfolio(ctx.db, user.id)
    if not portfolio:
        raise not_found(message="Portfolio not found")
    return user, portfolio


async def _ensure_current_portfolio(ctx: HandlerContext):
    from app.crud import create_portfolio, get_user_portfolio
    from app.schemas import PortfolioCreate

    user = await _get_current_user(ctx)
    portfolio = await get_user_portfolio(ctx.db, user.id)
    if portfolio:
        return user, portfolio

    portfolio = await create_portfolio(
        ctx.db,
        user.id,
        PortfolioCreate(
            name=f"{user.username}'s Portfolio",
            description="Default portfolio created through MCP onboarding",
            initial_value=0.0,
            currency="USD",
            risk_tolerance="Moderate",
            investment_objective="Growth",
            time_horizon="Long-term",
        ),
    )
    return user, portfolio


async def _build_onboarding_status(ctx: HandlerContext) -> dict[str, Any]:
    from app.crud import get_portfolio_holdings_count, get_user_portfolio

    user = await _get_current_user(ctx)
    portfolio = await get_user_portfolio(ctx.db, user.id)
    holdings_count = await get_portfolio_holdings_count(ctx.db, portfolio.id) if portfolio else 0
    return {
        "user_id": user.id,
        "portfolio_id": portfolio.id if portfolio else None,
        "has_portfolio": bool(portfolio),
        "holdings_count": holdings_count,
        "is_onboarded": bool(portfolio and holdings_count > 0),
    }


async def _onboard_assets(ctx: HandlerContext, asset_items: list[dict[str, Any]]) -> dict[str, Any]:
    from sqlalchemy import select

    from app.api.v1.assets import AssetOnboardingRequest, batch_fetch_asset_data
    from app.models.asset import Asset
    from app.models.holding import Holding
    from app.models.transaction import Transaction

    user, portfolio = await _ensure_current_portfolio(ctx)
    data = [AssetOnboardingRequest.model_validate(item) for item in asset_items]

    created_assets: list[dict[str, Any]] = []
    errors: list[str] = []

    tickers = [item.ticker.upper().strip() for item in data]
    stmt = select(Asset).where(Asset.ticker.in_(tickers))
    result = await ctx.db.execute(stmt)
    existing_assets_list = result.scalars().all()
    existing_assets = {asset.ticker: asset for asset in existing_assets_list}
    asset_data_map = await batch_fetch_asset_data(data, existing_assets)

    asset_model_fields = {
        "ticker",
        "name",
        "asset_type",
        "sector",
        "industry",
        "description",
        "currency",
        "exchange",
        "current_price",
        "market_cap",
        "dividend_yield",
        "pe_ratio",
        "beta",
        "last_price_update",
    }

    for item in data:
        try:
            ticker = item.ticker.upper().strip()
            asset_obj = existing_assets.get(ticker)

            if not asset_obj:
                asset_data = asset_data_map.get(ticker)
                if not asset_data:
                    errors.append(f"Could not fetch data for ticker: {ticker}")
                    continue
                filtered_asset_data = {key: value for key, value in asset_data.items() if key in asset_model_fields}
                asset_obj = Asset(**filtered_asset_data)
                ctx.db.add(asset_obj)
                await ctx.db.flush()

            existing_holding_stmt = select(Holding).where(Holding.portfolio_id == portfolio.id, Holding.ticker == ticker)
            existing_holding = (await ctx.db.execute(existing_holding_stmt)).scalar_one_or_none()

            if existing_holding:
                new_total_quantity = existing_holding.quantity + item.quantity
                new_total_cost = (existing_holding.quantity * existing_holding.average_cost) + (item.quantity * item.average_cost)
                new_average_cost = new_total_cost / new_total_quantity
                existing_holding.quantity = new_total_quantity
                existing_holding.average_cost = new_average_cost
                existing_holding.cost_basis = new_total_quantity * new_average_cost
                existing_holding.market_value = new_total_quantity * (asset_obj.current_price or new_average_cost)
                existing_holding.current_price = asset_obj.current_price
                holding_to_use = existing_holding
            else:
                holding_to_use = Holding(
                    asset_id=asset_obj.id,
                    ticker=asset_obj.ticker,
                    quantity=item.quantity,
                    average_cost=item.average_cost,
                    portfolio_id=portfolio.id,
                    cost_basis=item.quantity * item.average_cost,
                    market_value=item.quantity * (asset_obj.current_price or item.average_cost),
                    current_price=asset_obj.current_price,
                )
                ctx.db.add(holding_to_use)

            await ctx.db.flush()

            transaction = Transaction(
                portfolio_id=holding_to_use.portfolio_id,
                asset_id=asset_obj.id,
                transaction_type="BUY",
                quantity=item.quantity,
                price=item.average_cost,
            )
            ctx.db.add(transaction)
            await ctx.db.flush()

            created_assets.append(
                {
                    "ticker": ticker,
                    "name": asset_obj.name or ticker,
                    "quantity": item.quantity,
                    "average_cost": item.average_cost,
                    "purchase_cost": item.quantity * item.average_cost,
                    "current_price": asset_obj.current_price,
                    "market_value": holding_to_use.market_value,
                    "asset_id": asset_obj.id,
                    "holding_id": holding_to_use.id,
                    "transaction_id": transaction.id,
                }
            )
        except Exception as exc:
            errors.append(f"Error processing {item.ticker}: {str(exc)}")

    if created_assets:
        await ctx.db.commit()
        await notify_resource_updated("portfolio://current/holdings")
        await notify_resource_updated("portfolio://current/summary")
        await notify_resource_updated("portfolio://current/onboarding-status")

    return {"assets": created_assets, "errors": errors, "portfolio_id": portfolio.id, "user_id": user.id}


async def tool_portfolio_get_summary(ctx: HandlerContext, arguments: Dict[str, Any]) -> ToolResult:
    try:
        from app.api.v1.portfolios import get_portfolio_summary

        user = await _get_current_user(ctx)
        result = await get_portfolio_summary(current_user=user, db=ctx.db, currency=arguments.get("currency"))
    except HTTPException as exc:
        _normalize_http_error(exc)

    ui = {
        "resourceUri": "ui://portfolio/dashboard/current",
        "type": "dashboard",
        "schema": {
            "title": "Portfolio overview",
            "cards": [
                {"key": "total_value", "label": "Total value", "format": "currency"},
                {"key": "total_return", "label": "Total return", "format": "currency"},
                {"key": "total_return_percentage", "label": "Return %", "format": "percentage"},
                {"key": "total_holdings_count", "label": "Holdings", "format": "number"},
            ],
        },
        "data": result,
    }
    return _tool_result(
        text=(
            f"Portfolio {result['name']} is worth {result['total_value']:.2f} {result['currency']} "
            f"across {result['total_holdings_count']} holdings."
        ),
        data=result,
        ui=ui,
    )


async def tool_portfolio_get_analysis(ctx: HandlerContext, arguments: Dict[str, Any]) -> ToolResult:
    try:
        from app.api.v1.portfolios import get_portfolio_analysis

        user = await _get_current_user(ctx)
        result = await get_portfolio_analysis(current_user=user, db=ctx.db, currency=arguments.get("currency"))
    except HTTPException as exc:
        _normalize_http_error(exc)

    ui = {
        "resourceUri": "ui://portfolio/dashboard/analysis",
        "type": "dashboard",
        "schema": {
            "title": "Portfolio analysis",
            "sections": [
                {"key": "risk", "label": "Risk metrics"},
                {"key": "allocation", "label": "Allocation"},
                {"key": "performance", "label": "Performance"},
            ],
        },
        "data": result,
    }
    return _tool_result(
        text="Portfolio analysis completed with structured risk, allocation, and performance metrics.",
        data=result,
        ui=ui,
    )


async def tool_holdings_list(ctx: HandlerContext, arguments: Dict[str, Any]) -> ToolResult:
    try:
        from app.api.v1.holdings import get_holdings

        user = await _get_current_user(ctx)
        result = await get_holdings(
            current_user=user,
            db=ctx.db,
            currency=arguments.get("currency"),
            skip=arguments.get("skip", 0),
            limit=arguments.get("limit"),
        )
    except HTTPException as exc:
        _normalize_http_error(exc)

    ui = {
        "resourceUri": "ui://portfolio/holdings/table",
        "type": "table",
        "schema": {
            "columns": [
                {"key": "ticker", "label": "Ticker"},
                {"key": "quantity", "label": "Quantity"},
                {"key": "average_cost", "label": "Average cost"},
                {"key": "market_value", "label": "Market value"},
                {"key": "unrealized_gain_loss_percentage", "label": "Return %"},
            ]
        },
        "data": result,
    }
    return _tool_result(
        text=f"Retrieved {result['total']} holdings.",
        data=result,
        ui=ui,
    )


async def tool_holdings_create(ctx: HandlerContext, arguments: Dict[str, Any]) -> ToolResult:
    try:
        from app.api.v1.holdings import create_user_holding

        payload = HoldingCreate.model_validate(arguments)
        user = await _get_current_user(ctx)
        result = await create_user_holding(holding_create=payload, current_user=user, db=ctx.db)
    except HTTPException as exc:
        _normalize_http_error(exc)
    except Exception as exc:
        raise invalid_params(message="Holding payload failed validation", data={"error": str(exc)}) from exc

    serialized = HoldingInDB.model_validate(result).model_dump(mode="json")
    await notify_resource_updated("portfolio://current/holdings")
    await notify_resource_updated("portfolio://current/summary")

    return _tool_result(
        text=f"Created holding {serialized['ticker']} with quantity {serialized['quantity']}.",
        data=serialized,
    )


async def tool_holdings_open_create_form(ctx: HandlerContext, arguments: Dict[str, Any]) -> ToolResult:
    schema = {
        "title": "Create holding",
        "submitTool": "holdings_create",
        "fields": [
            {"name": "ticker", "type": "string", "label": "Ticker", "required": True},
            {"name": "quantity", "type": "number", "label": "Quantity", "required": True, "min": 0.0001},
            {"name": "average_cost", "type": "number", "label": "Average cost", "required": True, "min": 0.0001},
            {"name": "target_allocation", "type": "number", "label": "Target allocation", "min": 0, "max": 100},
            {"name": "notes", "type": "string", "label": "Notes", "multiline": True},
        ],
    }
    return _tool_result(
        text="Create holding form is ready.",
        data={"form": schema},
        ui={
            "resourceUri": "ui://portfolio/forms/create-holding",
            "type": "form",
            "schema": schema,
            "data": arguments,
        },
    )


async def tool_holdings_open_sell_form(ctx: HandlerContext, arguments: Dict[str, Any]) -> ToolResult:
    schema = {
        "title": "Sell holding",
        "submitTool": "holdings_sell",
        "fields": [
            {"name": "ticker", "type": "string", "label": "Ticker", "required": True},
            {"name": "quantity", "type": "number", "label": "Quantity to sell", "required": True, "min": 0.0001},
            {"name": "price", "type": "number", "label": "Sell price", "required": True, "min": 0.0001},
        ],
    }
    return _tool_result(
        text="Sell holding form is ready.",
        data={"form": schema},
        ui={
            "resourceUri": "ui://portfolio/forms/sell-holding",
            "type": "form",
            "schema": schema,
            "data": arguments,
        },
    )


async def tool_holdings_open_edit_form(ctx: HandlerContext, arguments: Dict[str, Any]) -> ToolResult:
    schema = {
        "title": "Edit holding",
        "submitTool": "holdings_update",
        "fields": [
            {"name": "holding_id", "type": "number", "label": "Holding ID", "required": True, "min": 1},
            {"name": "quantity", "type": "number", "label": "Quantity", "required": False, "min": 0.0001},
            {"name": "average_cost", "type": "number", "label": "Average cost", "required": False, "min": 0.0001},
            {"name": "target_allocation", "type": "number", "label": "Target allocation", "required": False, "min": 0, "max": 100},
            {"name": "notes", "type": "string", "label": "Notes", "required": False, "multiline": True},
        ],
    }
    return _tool_result(
        text="Edit holding form is ready.",
        data={"form": schema},
        ui={
            "resourceUri": "ui://portfolio/forms/edit-holding",
            "type": "form",
            "schema": schema,
            "data": arguments,
        },
    )


async def tool_cash_open_transaction_form(ctx: HandlerContext, arguments: Dict[str, Any]) -> ToolResult:
    transaction_type = str(arguments.get("transaction_type") or "DEPOSIT").upper()
    submit_tool = "cash_withdraw" if transaction_type == "WITHDRAWAL" else "cash_deposit"
    schema = {
        "title": "Cash transaction",
        "submitTool": submit_tool,
        "fields": [
            {"name": "amount", "type": "number", "label": "Amount", "required": True, "min": 0.01},
            {"name": "currency", "type": "string", "label": "Currency", "required": False, "enum": ["USD", "CAD"]},
            {"name": "notes", "type": "string", "label": "Notes", "required": False, "multiline": True},
        ],
    }
    return _tool_result(
        text=f"Cash {transaction_type.lower()} form is ready.",
        data={"form": schema, "transaction_type": transaction_type},
        ui={
            "resourceUri": "ui://portfolio/forms/cash-transaction",
            "type": "form",
            "schema": schema,
            "data": {"transaction_type": transaction_type, **arguments},
        },
    )


async def tool_holdings_update(ctx: HandlerContext, arguments: Dict[str, Any]) -> ToolResult:
    try:
        from app.api.v1.holdings import update_user_holding

        holding_id = int(arguments.get("holding_id"))
        payload = HoldingUpdate.model_validate({key: value for key, value in arguments.items() if key != "holding_id"})
        user = await _get_current_user(ctx)
        result = await update_user_holding(holding_id=holding_id, holding_update=payload, current_user=user, db=ctx.db)
    except HTTPException as exc:
        _normalize_http_error(exc)
    except Exception as exc:
        raise invalid_params(message="Holding update payload failed validation", data={"error": str(exc)}) from exc

    serialized = HoldingInDB.model_validate(result).model_dump(mode="json")
    await notify_resource_updated("portfolio://current/holdings")
    await notify_resource_updated("portfolio://current/summary")
    return _tool_result(
        text=f"Updated holding {serialized['ticker']}.",
        data=serialized,
    )


async def tool_holdings_sell(ctx: HandlerContext, arguments: Dict[str, Any]) -> ToolResult:
    try:
        from app.api.v1.holdings import sell_asset

        payload = AssetSellRequest.model_validate(arguments)
        user = await _get_current_user(ctx)
        result = await sell_asset(sell_request=payload, current_user=user, db=ctx.db)
    except HTTPException as exc:
        _normalize_http_error(exc)
    except Exception as exc:
        raise invalid_params(message="Sell payload failed validation", data={"error": str(exc)}) from exc

    await notify_resource_updated("portfolio://current/holdings")
    await notify_resource_updated("portfolio://current/summary")
    await notify_resource_updated("portfolio://current/cash-balance")
    await notify_resource_updated("portfolio://current/transactions")

    return _tool_result(
        text=f"Sold {result['quantity_sold']} of {payload.ticker.upper()}.",
        data=result,
    )


async def tool_cash_deposit(ctx: HandlerContext, arguments: Dict[str, Any]) -> ToolResult:
    try:
        from app.api.v1.transactions import deposit_cash
        from app.models.transaction import TransactionType

        user, portfolio = await _get_current_portfolio(ctx)
        payload = CashTransactionCreate.model_validate(
            {
                "amount": arguments.get("amount"),
                "transaction_type": TransactionType.DEPOSIT,
                "currency": arguments.get("currency"),
                "notes": arguments.get("notes"),
            }
        )
        result = await deposit_cash(portfolio_id=portfolio.id, cash_in=payload, db=ctx.db, current_user=user)
    except HTTPException as exc:
        _normalize_http_error(exc)
    except Exception as exc:
        raise invalid_params(message="Deposit payload failed validation", data={"error": str(exc)}) from exc

    await notify_resource_updated("portfolio://current/summary")
    await notify_resource_updated("portfolio://current/cash-balance")
    await notify_resource_updated("portfolio://current/transactions")

    return _tool_result(text=result["message"], data=result)


async def tool_cash_withdraw(ctx: HandlerContext, arguments: Dict[str, Any]) -> ToolResult:
    try:
        from app.api.v1.transactions import withdraw_cash
        from app.models.transaction import TransactionType

        user, portfolio = await _get_current_portfolio(ctx)
        payload = CashTransactionCreate.model_validate(
            {
                "amount": arguments.get("amount"),
                "transaction_type": TransactionType.WITHDRAWAL,
                "currency": arguments.get("currency"),
                "notes": arguments.get("notes"),
            }
        )
        result = await withdraw_cash(portfolio_id=portfolio.id, cash_in=payload, db=ctx.db, current_user=user)
    except HTTPException as exc:
        _normalize_http_error(exc)
    except Exception as exc:
        raise invalid_params(message="Withdrawal payload failed validation", data={"error": str(exc)}) from exc

    await notify_resource_updated("portfolio://current/summary")
    await notify_resource_updated("portfolio://current/cash-balance")
    await notify_resource_updated("portfolio://current/transactions")

    return _tool_result(text=result["message"], data=result)


async def tool_portfolio_get_cash_balance(ctx: HandlerContext, arguments: Dict[str, Any]) -> ToolResult:
    try:
        from app.api.v1.portfolios import get_portfolio_summary

        user = await _get_current_user(ctx)
        summary = await get_portfolio_summary(current_user=user, db=ctx.db, currency=arguments.get("currency"))
    except HTTPException as exc:
        _normalize_http_error(exc)

    payload = {
        "portfolio_id": summary["id"],
        "portfolio_name": summary["name"],
        "cash_balance": summary.get("cash_balance", 0),
        "currency": summary["currency"],
        "last_updated": summary.get("last_updated"),
    }
    return _tool_result(
        text=f"Cash balance is {payload['cash_balance']:.2f} {payload['currency']}.",
        data=payload,
        ui={
            "resourceUri": "ui://portfolio/dashboard/cash-balance",
            "type": "dashboard",
            "schema": {"title": "Cash balance", "cards": [{"key": "cash_balance", "label": "Cash balance", "format": "currency"}]},
            "data": payload,
        },
    )


async def tool_transactions_list(ctx: HandlerContext, arguments: Dict[str, Any]) -> ToolResult:
    from app.crud.transaction import get_transactions_by_portfolio

    user, portfolio = await _get_current_portfolio(ctx)
    skip = int(arguments.get("skip", 0) or 0)
    limit = int(arguments.get("limit", 100) or 100)
    transactions = await get_transactions_by_portfolio(ctx.db, portfolio.id, skip=skip, limit=limit)
    items = [
        {
            "id": transaction.id,
            "portfolio_id": transaction.portfolio_id,
            "asset_id": transaction.asset_id,
            "asset_ticker": transaction.asset.ticker if getattr(transaction, "asset", None) else None,
            "transaction_type": getattr(transaction.transaction_type, "value", transaction.transaction_type),
            "quantity": transaction.quantity,
            "price": transaction.price,
            "transaction_date": transaction.transaction_date.isoformat() if transaction.transaction_date else None,
            "notes": transaction.notes,
            "realized_gain_loss": transaction.realized_gain_loss,
        }
        for transaction in transactions
    ]
    payload = {"items": items, "total": len(items), "skip": skip, "limit": limit}
    return _tool_result(
        text=f"Retrieved {len(items)} transactions.",
        data=payload,
        ui={
            "resourceUri": "ui://portfolio/transactions/table",
            "type": "table",
            "schema": {
                "columns": [
                    {"key": "transaction_date", "label": "Date"},
                    {"key": "transaction_type", "label": "Type"},
                    {"key": "asset_ticker", "label": "Ticker"},
                    {"key": "quantity", "label": "Quantity"},
                    {"key": "price", "label": "Price"},
                    {"key": "realized_gain_loss", "label": "Realized P/L"},
                ]
            },
            "data": payload,
        },
    )


async def tool_market_get_live_board(ctx: HandlerContext, arguments: Dict[str, Any]) -> ToolResult:
    try:
        from app.api.v1.market import get_live_market_data

        user = await _get_current_user(ctx)
        payload = await get_live_market_data(currency=arguments.get("currency"), current_user=user, db=ctx.db)
    except HTTPException as exc:
        _normalize_http_error(exc)

    return _tool_result(
        text=f"Retrieved live market board with {len(payload.get('holdings', []))} holdings.",
        data=payload,
        ui={
            "resourceUri": "ui://portfolio/market/live-board",
            "type": "table",
            "schema": {
                "columns": [
                    {"key": "ticker", "label": "Ticker"},
                    {"key": "quantity", "label": "Quantity"},
                    {"key": "current_price", "label": "Current price"},
                    {"key": "market_value", "label": "Market value"},
                    {"key": "change_percent", "label": "Change %"},
                ]
            },
            "data": payload,
        },
    )


async def tool_market_get_quote(ctx: HandlerContext, arguments: Dict[str, Any]) -> ToolResult:
    from app.services.finance_service import FinanceService

    symbol = str(arguments.get("symbol", "")).strip().upper()
    if not symbol:
        raise invalid_params(message="symbol is required")

    asset_type = arguments.get("asset_type")
    data = await FinanceService.get_asset_info(symbol, asset_type=asset_type)
    if not data:
        raise not_found(message=f"No market data found for {symbol}")

    return _tool_result(
        text=f"Fetched market quote for {symbol}.",
        data=data,
    )


async def tool_overview_get_dashboard(ctx: HandlerContext, arguments: Dict[str, Any]) -> ToolResult:
    try:
        from app.api.v1.analysis import get_portfolio_metrics as get_analysis_metrics
        from app.api.v1.dashboard import get_dashboard_overview

        user, portfolio = await _get_current_portfolio(ctx)
        dashboard = await get_dashboard_overview(current_user=user, db=ctx.db, currency=arguments.get("currency"))
        metrics = await get_analysis_metrics(portfolio_id=portfolio.id, db=ctx.db)
    except HTTPException as exc:
        _normalize_http_error(exc)

    payload = {"dashboard": dashboard, "metrics": metrics}
    return _tool_result(
        text="Retrieved overview dashboard data.",
        data=payload,
        ui={
            "resourceUri": "ui://portfolio/dashboard/overview",
            "type": "dashboard",
            "schema": {
                "title": "Performance overview",
                "sections": [
                    {"key": "dashboard.cash_balance", "label": "Cash balance"},
                    {"key": "dashboard.realized_gains", "label": "Realized gains"},
                    {"key": "metrics", "label": "Performance metrics"},
                ],
            },
            "data": payload,
        },
    )


async def tool_analytics_get_risk(ctx: HandlerContext, arguments: Dict[str, Any]) -> ToolResult:
    try:
        from app.api.v1.analysis import get_portfolio_metrics as get_analysis_metrics

        _, portfolio = await _get_current_portfolio(ctx)
        payload = await get_analysis_metrics(portfolio_id=portfolio.id, db=ctx.db)
    except HTTPException as exc:
        _normalize_http_error(exc)

    return _tool_result(
        text="Retrieved risk analytics.",
        data=payload,
        ui={
            "resourceUri": "ui://portfolio/analytics/risk",
            "type": "dashboard",
            "schema": {"title": "Risk analytics", "sections": [{"key": "metrics", "label": "Risk metrics"}]},
            "data": payload,
        },
    )


async def tool_analytics_get_allocation(ctx: HandlerContext, arguments: Dict[str, Any]) -> ToolResult:
    try:
        from app.api.v1.analysis import get_sector_allocation

        _, portfolio = await _get_current_portfolio(ctx)
        payload = await get_sector_allocation(portfolio_id=portfolio.id, currency=arguments.get("currency"), db=ctx.db)
    except HTTPException as exc:
        _normalize_http_error(exc)

    return _tool_result(
        text="Retrieved allocation analytics.",
        data=payload,
        ui={
            "resourceUri": "ui://portfolio/analytics/allocation",
            "type": "dashboard",
            "schema": {"title": "Allocation analytics", "sections": [{"key": "allocation", "label": "Sector allocation"}]},
            "data": payload,
        },
    )


async def tool_analytics_get_efficient_frontier(ctx: HandlerContext, arguments: Dict[str, Any]) -> ToolResult:
    try:
        from app.api.v1.analysis import get_efficient_frontier

        _, portfolio = await _get_current_portfolio(ctx)
        payload = await get_efficient_frontier(portfolio_id=portfolio.id, currency=arguments.get("currency"), db=ctx.db)
    except HTTPException as exc:
        _normalize_http_error(exc)

    return _tool_result(
        text="Retrieved efficient frontier analytics.",
        data=payload,
        ui={
            "resourceUri": "ui://portfolio/analytics/efficient-frontier",
            "type": "dashboard",
            "schema": {"title": "Efficient frontier", "sections": [{"key": "frontier", "label": "Efficient frontier"}]},
            "data": payload,
        },
    )


async def tool_analytics_get_monte_carlo(ctx: HandlerContext, arguments: Dict[str, Any]) -> ToolResult:
    try:
        from app.api.v1.analysis import run_monte_carlo_simulation

        _, portfolio = await _get_current_portfolio(ctx)
        payload = await run_monte_carlo_simulation(
            portfolio_id=portfolio.id,
            currency=arguments.get("currency"),
            db=ctx.db,
            scenarios=int(arguments.get("scenarios", 1000) or 1000),
            time_horizon=int(arguments.get("time_horizon", 252) or 252),
        )
    except HTTPException as exc:
        _normalize_http_error(exc)

    return _tool_result(
        text="Retrieved Monte Carlo analytics.",
        data=payload,
        ui={
            "resourceUri": "ui://portfolio/analytics/monte-carlo",
            "type": "dashboard",
            "schema": {"title": "Monte Carlo simulation", "sections": [{"key": "simulation", "label": "Simulation results"}]},
            "data": payload,
        },
    )


async def tool_analytics_get_cppi(ctx: HandlerContext, arguments: Dict[str, Any]) -> ToolResult:
    try:
        from app.api.v1.analysis import run_cppi_simulation

        _, portfolio = await _get_current_portfolio(ctx)
        payload = await run_cppi_simulation(
            portfolio_id=portfolio.id,
            currency=arguments.get("currency"),
            db=ctx.db,
            multiplier=int(arguments.get("multiplier", 3) or 3),
            floor=float(arguments.get("floor", 0.8) or 0.8),
            time_horizon=int(arguments.get("time_horizon", 252) or 252),
        )
    except HTTPException as exc:
        _normalize_http_error(exc)

    return _tool_result(
        text="Retrieved CPPI analytics.",
        data=payload,
        ui={
            "resourceUri": "ui://portfolio/analytics/cppi",
            "type": "dashboard",
            "schema": {"title": "CPPI strategy", "sections": [{"key": "simulation", "label": "CPPI results"}]},
            "data": payload,
        },
    )


async def tool_onboarding_open_manual_form(ctx: HandlerContext, arguments: Dict[str, Any]) -> ToolResult:
    schema = {
        "title": "Manual onboarding",
        "submitTool": "onboarding_import_assets",
        "fields": [
            {
                "name": "assets",
                "type": "array",
                "label": "Assets",
                "required": True,
                "itemSchema": {
                    "type": "object",
                    "fields": [
                        {"name": "ticker", "type": "string", "label": "Ticker", "required": True},
                        {"name": "quantity", "type": "number", "label": "Quantity", "required": True, "min": 0.0001},
                        {"name": "average_cost", "type": "number", "label": "Average cost", "required": True, "min": 0.0001},
                        {"name": "asset_type", "type": "string", "label": "Asset type", "required": False, "enum": ["Stock", "Mutual Fund", "Crypto"]},
                        {"name": "currency", "type": "string", "label": "Currency", "required": False, "enum": ["USD", "CAD", "EUR"]},
                    ],
                },
            }
        ],
    }
    return _tool_result(
        text="Manual onboarding form is ready.",
        data={"form": schema},
        ui={
            "resourceUri": "ui://portfolio/onboarding/manual-form",
            "type": "form",
            "schema": schema,
            "data": arguments,
        },
    )


async def tool_onboarding_open_csv_import_form(ctx: HandlerContext, arguments: Dict[str, Any]) -> ToolResult:
    schema = {
        "title": "CSV onboarding import",
        "submitTool": "onboarding_import_csv",
        "fields": [
            {"name": "csv_content", "type": "string", "label": "CSV content", "required": True, "multiline": True},
        ],
    }
    return _tool_result(
        text="CSV onboarding form is ready.",
        data={"form": schema},
        ui={
            "resourceUri": "ui://portfolio/onboarding/csv-form",
            "type": "form",
            "schema": schema,
            "data": arguments,
        },
    )


async def tool_onboarding_import_assets(ctx: HandlerContext, arguments: Dict[str, Any]) -> ToolResult:
    assets = arguments.get("assets")
    if not isinstance(assets, list) or not assets:
        raise invalid_params(message="assets must be a non-empty array")
    payload = await _onboard_assets(ctx, assets)
    return _tool_result(
        text=f"Processed onboarding for {len(payload['assets'])} assets.",
        data=payload,
        ui={
            "resourceUri": "ui://portfolio/onboarding/result",
            "type": "workflow",
            "schema": {"title": "Onboarding import result", "steps": [{"step": "import", "label": "Import assets"}]},
            "data": payload,
            "steps": [{"step": "import", "label": "Import assets"}],
        },
    )


async def tool_onboarding_import_csv(ctx: HandlerContext, arguments: Dict[str, Any]) -> ToolResult:
    csv_content = str(arguments.get("csv_content") or "")
    if not csv_content.strip():
        raise invalid_params(message="csv_content is required")

    reader = csv.DictReader(io.StringIO(csv_content))
    assets: list[dict[str, Any]] = []
    for row in reader:
        ticker = str(row.get("TICKER", row.get("ticker", ""))).strip()
        quantity = row.get("Quantity", row.get("quantity"))
        average_cost = row.get("Cost", row.get("cost", row.get("average_cost")))
        if ticker and quantity and average_cost:
            assets.append(
                {
                    "ticker": ticker,
                    "quantity": float(quantity),
                    "average_cost": float(average_cost),
                    "asset_type": row.get("ASSET_TYPE", row.get("asset_type", "Stock")),
                    "currency": row.get("CURRENCY", row.get("currency", "USD")),
                }
            )

    if not assets:
        raise invalid_params(message="No valid assets found in csv_content")

    payload = await _onboard_assets(ctx, assets)
    return _tool_result(
        text=f"Processed CSV onboarding for {len(payload['assets'])} assets.",
        data=payload,
        ui={
            "resourceUri": "ui://portfolio/onboarding/result",
            "type": "workflow",
            "schema": {"title": "Onboarding CSV import result", "steps": [{"step": "parse", "label": "Parse CSV"}, {"step": "import", "label": "Import assets"}]},
            "data": payload,
            "steps": [{"step": "parse", "label": "Parse CSV"}, {"step": "import", "label": "Import assets"}],
        },
    )


async def tool_onboarding_get_status(ctx: HandlerContext, arguments: Dict[str, Any]) -> ToolResult:
    payload = await _build_onboarding_status(ctx)
    return _tool_result(
        text="Retrieved onboarding status.",
        data=payload,
        ui={
            "resourceUri": "ui://portfolio/onboarding/status",
            "type": "dashboard",
            "schema": {"title": "Onboarding status", "cards": [{"key": "is_onboarded", "label": "Onboarded"}, {"key": "holdings_count", "label": "Holdings"}]},
            "data": payload,
        },
    )


async def tool_settings_list_mcp_api_keys(ctx: HandlerContext, arguments: Dict[str, Any]) -> ToolResult:
    from app.crud import list_user_mcp_api_keys, serialize_mcp_api_key

    user = await _get_current_user(ctx)
    keys = await list_user_mcp_api_keys(ctx.db, user.id)
    payload = {"items": [serialize_mcp_api_key(key) for key in keys], "total": len(keys)}
    return _tool_result(
        text=f"Retrieved {len(keys)} MCP API keys.",
        data=payload,
        ui={
            "resourceUri": "ui://settings/mcp-api-keys/table",
            "type": "table",
            "schema": {
                "columns": [
                    {"key": "name", "label": "Name"},
                    {"key": "key_preview", "label": "Key preview"},
                    {"key": "is_active", "label": "Active"},
                    {"key": "last_used_at", "label": "Last used"},
                    {"key": "expires_at", "label": "Expires"},
                ]
            },
            "data": payload,
        },
    )


async def tool_settings_open_create_mcp_api_key_form(ctx: HandlerContext, arguments: Dict[str, Any]) -> ToolResult:
    schema = {
        "title": "Create MCP API key",
        "submitTool": "settings_create_mcp_api_key",
        "fields": [
            {"name": "name", "type": "string", "label": "Key name", "required": True},
            {"name": "expires_in_days", "type": "number", "label": "Expires in days", "required": False, "min": 1, "max": 3650},
        ],
    }
    return _tool_result(
        text="Create MCP API key form is ready.",
        data={"form": schema},
        ui={
            "resourceUri": "ui://settings/forms/create-mcp-api-key",
            "type": "form",
            "schema": schema,
            "data": arguments,
        },
    )


async def tool_settings_create_mcp_api_key(ctx: HandlerContext, arguments: Dict[str, Any]) -> ToolResult:
    from app.crud import create_user_mcp_api_key, serialize_mcp_api_key

    user = await _get_current_user(ctx)
    try:
        payload = MCPAPIKeyCreateRequest.model_validate(arguments)
        api_key, raw_key = await create_user_mcp_api_key(ctx.db, user, name=payload.name, expires_in_days=payload.expires_in_days)
    except Exception as exc:
        raise invalid_params(message="MCP API key payload failed validation", data={"error": str(exc)}) from exc

    await notify_resource_updated("settings://mcp-api-keys")
    result = {"api_key": raw_key, "key": serialize_mcp_api_key(api_key)}
    return _tool_result(
        text=f"Created MCP API key {api_key.name}.",
        data=result,
        ui={
            "resourceUri": "ui://settings/mcp-api-keys/secret",
            "type": "dashboard",
            "schema": {"title": "Copy this key now", "cards": [{"key": "api_key", "label": "API key"}]},
            "data": result,
        },
    )


async def tool_settings_rotate_mcp_api_key(ctx: HandlerContext, arguments: Dict[str, Any]) -> ToolResult:
    from app.crud import get_user_mcp_api_key, rotate_user_mcp_api_key, serialize_mcp_api_key

    user = await _get_current_user(ctx)
    try:
        key_id = int(arguments.get("key_id"))
        payload = MCPAPIKeyCreateRequest.model_validate(
            {
                "name": arguments.get("name") or "Rotated MCP Key",
                "expires_in_days": arguments.get("expires_in_days"),
            }
        )
    except Exception as exc:
        raise invalid_params(message="MCP API key rotation payload failed validation", data={"error": str(exc)}) from exc

    api_key = await get_user_mcp_api_key(ctx.db, user.id, key_id)
    if not api_key:
        raise not_found(message="MCP API key not found")

    rotated_key, raw_key = await rotate_user_mcp_api_key(ctx.db, api_key, expires_in_days=payload.expires_in_days)
    if payload.name != rotated_key.name:
        rotated_key.name = payload.name
        await ctx.db.commit()
        await ctx.db.refresh(rotated_key)

    await notify_resource_updated("settings://mcp-api-keys")
    result = {"api_key": raw_key, "key": serialize_mcp_api_key(rotated_key)}
    return _tool_result(
        text=f"Rotated MCP API key {rotated_key.name}.",
        data=result,
        ui={
            "resourceUri": "ui://settings/mcp-api-keys/secret",
            "type": "dashboard",
            "schema": {"title": "Copy this key now", "cards": [{"key": "api_key", "label": "API key"}]},
            "data": result,
        },
    )


async def tool_settings_revoke_mcp_api_key(ctx: HandlerContext, arguments: Dict[str, Any]) -> ToolResult:
    from app.crud import get_user_mcp_api_key, revoke_user_mcp_api_key, serialize_mcp_api_key

    user = await _get_current_user(ctx)
    try:
        key_id = int(arguments.get("key_id"))
    except Exception as exc:
        raise invalid_params(message="key_id is required", data={"error": str(exc)}) from exc

    api_key = await get_user_mcp_api_key(ctx.db, user.id, key_id)
    if not api_key:
        raise not_found(message="MCP API key not found")

    revoked_key = await revoke_user_mcp_api_key(ctx.db, api_key)
    await notify_resource_updated("settings://mcp-api-keys")
    result = {"message": "MCP API key revoked", "key": serialize_mcp_api_key(revoked_key)}
    return _tool_result(text=result["message"], data=result)


async def tool_exchange_convert(ctx: HandlerContext, arguments: Dict[str, Any]) -> ToolResult:
    from app.services.exchange_rate_service import get_exchange_rate_service

    amount = arguments.get("amount")
    from_currency = arguments.get("from_currency")
    to_currency = arguments.get("to_currency")
    if amount is None or not from_currency or not to_currency:
        raise invalid_params(message="amount, from_currency, and to_currency are required")

    service = get_exchange_rate_service()
    converted_amount = await service.convert_amount(float(amount), from_currency, to_currency, use_cache=True)
    rate_info = await service.get_rate_info(from_currency, to_currency)
    payload = {
        "original_amount": float(amount),
        "original_currency": from_currency.upper(),
        "converted_amount": converted_amount,
        "converted_currency": to_currency.upper(),
        "exchange_rate": rate_info["rate"],
        "timestamp": rate_info["timestamp"],
    }
    return _tool_result(
        text=(
            f"Converted {payload['original_amount']:.2f} {payload['original_currency']} to "
            f"{payload['converted_amount']:.2f} {payload['converted_currency']}."
        ),
        data=payload,
    )


async def tool_portfolio_refresh_metrics(ctx: HandlerContext, arguments: Dict[str, Any]) -> ToolResult:
    try:
        from app.api.v1.portfolios import refresh_portfolio_metrics

        user = await _get_current_user(ctx)
        result = await refresh_portfolio_metrics(current_user=user, db=ctx.db)
    except HTTPException as exc:
        _normalize_http_error(exc)

    await notify_resource_updated("portfolio://current/summary")
    await notify_resource_updated("portfolio://current/holdings")

    return _tool_result(text=result["message"], data=result)


async def tool_portfolio_rebalance_workflow(ctx: HandlerContext, arguments: Dict[str, Any]) -> ToolResult:
    from app.api.v1.holdings import get_holdings
    from app.crud import get_user_portfolio

    user = await _get_current_user(ctx)
    portfolio = await get_user_portfolio(ctx.db, user.id)
    if not portfolio:
        raise not_found(message="Portfolio not found")

    currency = arguments.get("currency") or portfolio.currency
    holdings_response = await get_holdings(current_user=user, db=ctx.db, currency=currency, skip=0, limit=50)
    holdings = holdings_response["items"]
    total_market_value = sum((item.get("market_value") or 0) for item in holdings)
    suggestions = []
    for item in holdings:
        market_value = item.get("market_value") or 0
        allocation = (market_value / total_market_value * 100) if total_market_value else 0
        if allocation >= 35:
            suggestions.append(
                {
                    "ticker": item["ticker"],
                    "action": "review_reduce",
                    "reason": f"Allocation is {allocation:.1f}% which is above the 35% review threshold.",
                }
            )

    payload = {
        "step": arguments.get("step", "preview"),
        "portfolio_id": portfolio.id,
        "currency": currency,
        "summary": {
            "total_market_value": total_market_value,
            "holdings_count": len(holdings),
        },
        "suggestions": suggestions,
        "nextActions": [
            {"step": "preview", "label": "Preview rebalance suggestions"},
            {"step": "validate", "label": "Validate thresholds and exclusions"},
            {"step": "confirm", "label": "Confirm manual execution plan"},
        ],
    }
    return _tool_result(
        text="Prepared a multi-step rebalance workflow preview.",
        data=payload,
        ui={
            "resourceUri": "ui://portfolio/workflows/rebalance",
            "type": "workflow",
            "schema": {
                "title": "Rebalance workflow",
                "stepField": "step",
                "steps": payload["nextActions"],
            },
            "data": payload,
            "steps": payload["nextActions"],
        },
    )


async def resource_portfolio_summary(ctx: HandlerContext, arguments: Dict[str, Any]) -> ResourceReadResult:
    tool_result = await tool_portfolio_get_summary(ctx, arguments)
    return ResourceReadResult(
        contents=[
            ResourceContent(
                uri="portfolio://current/summary",
                mimeType="application/json",
                text=json.dumps(tool_result.structuredContent, default=str),
            )
        ]
    )


async def resource_portfolio_holdings(ctx: HandlerContext, arguments: Dict[str, Any]) -> ResourceReadResult:
    tool_result = await tool_holdings_list(ctx, arguments)
    return ResourceReadResult(
        contents=[
            ResourceContent(
                uri="portfolio://current/holdings",
                mimeType="application/json",
                text=json.dumps(tool_result.structuredContent, default=str),
            )
        ]
    )


async def resource_portfolio_cash_balance(ctx: HandlerContext, arguments: Dict[str, Any]) -> ResourceReadResult:
    tool_result = await tool_portfolio_get_cash_balance(ctx, arguments)
    return ResourceReadResult(
        contents=[
            ResourceContent(
                uri="portfolio://current/cash-balance",
                mimeType="application/json",
                text=json.dumps(tool_result.structuredContent, default=str),
            )
        ]
    )


async def resource_portfolio_transactions(ctx: HandlerContext, arguments: Dict[str, Any]) -> ResourceReadResult:
    tool_result = await tool_transactions_list(ctx, arguments)
    return ResourceReadResult(
        contents=[
            ResourceContent(
                uri="portfolio://current/transactions",
                mimeType="application/json",
                text=json.dumps(tool_result.structuredContent, default=str),
            )
        ]
    )


async def resource_market_quote(ctx: HandlerContext, arguments: Dict[str, Any]) -> ResourceReadResult:
    symbol = arguments.get("symbol")
    if not symbol:
        raise invalid_params(message="symbol is required in the market resource URI")
    tool_result = await tool_market_get_quote(ctx, {"symbol": symbol})
    return ResourceReadResult(
        contents=[
            ResourceContent(
                uri=f"market://quote/{symbol}",
                mimeType="application/json",
                text=json.dumps(tool_result.structuredContent, default=str),
            )
        ]
    )


async def resource_market_live_board(ctx: HandlerContext, arguments: Dict[str, Any]) -> ResourceReadResult:
    tool_result = await tool_market_get_live_board(ctx, arguments)
    return ResourceReadResult(
        contents=[
            ResourceContent(
                uri="market://portfolio/live-board",
                mimeType="application/json",
                text=json.dumps(tool_result.structuredContent, default=str),
            )
        ]
    )


async def resource_settings_mcp_api_keys(ctx: HandlerContext, arguments: Dict[str, Any]) -> ResourceReadResult:
    tool_result = await tool_settings_list_mcp_api_keys(ctx, arguments)
    return ResourceReadResult(
        contents=[
            ResourceContent(
                uri="settings://mcp-api-keys",
                mimeType="application/json",
                text=json.dumps(tool_result.structuredContent, default=str),
            )
        ]
    )


async def resource_overview_dashboard(ctx: HandlerContext, arguments: Dict[str, Any]) -> ResourceReadResult:
    tool_result = await tool_overview_get_dashboard(ctx, arguments)
    return ResourceReadResult(
        contents=[
            ResourceContent(
                uri="overview://dashboard/current",
                mimeType="application/json",
                text=json.dumps(tool_result.structuredContent, default=str),
            )
        ]
    )


async def resource_analytics_risk(ctx: HandlerContext, arguments: Dict[str, Any]) -> ResourceReadResult:
    tool_result = await tool_analytics_get_risk(ctx, arguments)
    return ResourceReadResult(contents=[ResourceContent(uri="analytics://risk/current", mimeType="application/json", text=json.dumps(tool_result.structuredContent, default=str))])


async def resource_analytics_allocation(ctx: HandlerContext, arguments: Dict[str, Any]) -> ResourceReadResult:
    tool_result = await tool_analytics_get_allocation(ctx, arguments)
    return ResourceReadResult(contents=[ResourceContent(uri="analytics://allocation/current", mimeType="application/json", text=json.dumps(tool_result.structuredContent, default=str))])


async def resource_analytics_efficient_frontier(ctx: HandlerContext, arguments: Dict[str, Any]) -> ResourceReadResult:
    tool_result = await tool_analytics_get_efficient_frontier(ctx, arguments)
    return ResourceReadResult(contents=[ResourceContent(uri="analytics://efficient-frontier/current", mimeType="application/json", text=json.dumps(tool_result.structuredContent, default=str))])


async def resource_analytics_monte_carlo(ctx: HandlerContext, arguments: Dict[str, Any]) -> ResourceReadResult:
    tool_result = await tool_analytics_get_monte_carlo(ctx, arguments)
    return ResourceReadResult(contents=[ResourceContent(uri="analytics://monte-carlo/current", mimeType="application/json", text=json.dumps(tool_result.structuredContent, default=str))])


async def resource_analytics_cppi(ctx: HandlerContext, arguments: Dict[str, Any]) -> ResourceReadResult:
    tool_result = await tool_analytics_get_cppi(ctx, arguments)
    return ResourceReadResult(contents=[ResourceContent(uri="analytics://cppi/current", mimeType="application/json", text=json.dumps(tool_result.structuredContent, default=str))])


async def resource_onboarding_status(ctx: HandlerContext, arguments: Dict[str, Any]) -> ResourceReadResult:
    tool_result = await tool_onboarding_get_status(ctx, arguments)
    return ResourceReadResult(contents=[ResourceContent(uri="portfolio://current/onboarding-status", mimeType="application/json", text=json.dumps(tool_result.structuredContent, default=str))])


async def resource_system_health(ctx: HandlerContext, arguments: Dict[str, Any]) -> ResourceReadResult:
    from app.api import health_check

    payload = await health_check(db=ctx.db)
    return ResourceReadResult(
        contents=[
            ResourceContent(
                uri="system://health",
                mimeType="application/json",
                text=json.dumps(payload, default=str),
            )
        ]
    )


async def prompt_portfolio_analysis_summary(ctx: HandlerContext, arguments: Dict[str, Any]) -> PromptResult:
    question = arguments.get("question", "Summarize this portfolio.")
    currency = arguments.get("currency", "USD")
    return PromptResult(
        description="Portfolio analysis summarization prompt.",
        messages=[
            PromptMessage(
                role="system",
                content={
                    "type": "text",
                    "text": (
                        "You are analyzing an investment portfolio. Use the summary and holdings resources to answer "
                        "with concrete metrics, risk notes, and next actions."
                    ),
                },
            ),
            PromptMessage(
                role="user",
                content={
                    "type": "text",
                    "text": f"Question: {question}\nPreferred currency: {currency}\nResources: portfolio://current/summary, portfolio://current/holdings",
                },
            ),
        ],
    )


async def prompt_rebalance_suggestion(ctx: HandlerContext, arguments: Dict[str, Any]) -> PromptResult:
    objective = arguments.get("objective", "Reduce concentration risk")
    return PromptResult(
        description="Rebalance recommendation prompt.",
        messages=[
            PromptMessage(
                role="system",
                content={
                    "type": "text",
                    "text": "Propose a conservative rebalance plan using diversification, concentration, and cash management constraints.",
                },
            ),
            PromptMessage(
                role="user",
                content={
                    "type": "text",
                    "text": f"Objective: {objective}\nUse the workflow tool portfolio.rebalance_workflow and summary resources before answering.",
                },
            ),
        ],
    )


async def prompt_onboarding_import_guidance(ctx: HandlerContext, arguments: Dict[str, Any]) -> PromptResult:
    source = arguments.get("source", "CSV")
    return PromptResult(
        description="Portfolio onboarding prompt.",
        messages=[
            PromptMessage(
                role="system",
                content={
                    "type": "text",
                    "text": "Guide the user through importing portfolio data with validation checks and fallback manual entry.",
                },
            ),
            PromptMessage(
                role="user",
                content={
                    "type": "text",
                    "text": f"Help me import a portfolio from {source}. Include validation steps, missing field handling, and how to recover from symbol errors.",
                },
            ),
        ],
    )


async def sampling_create_message(ctx: HandlerContext, arguments: Dict[str, Any]) -> SamplingResult:
    temperature = arguments.get("temperature", 0.2)
    system_prompt = arguments.get("systemPrompt") or "Use the portfolio tools before answering with investment analysis."
    message_count = len(arguments.get("messages", []))
    return SamplingResult(
        content={
            "type": "text",
            "text": (
                f"Sampling hint prepared for {message_count} messages. Use a grounded, analytical style and prefer tool outputs over priors. "
                f"System prompt: {system_prompt}"
            ),
        },
        modelPreferences={
            "temperature": temperature,
            "toolChoice": "auto",
            "preferredModels": ["gpt-5.4", "claude-sonnet", "gemini-2.5-pro"],
        },
    )


TOOL_HANDLERS: Dict[str, Callable[[HandlerContext, Dict[str, Any]], Any]] = {
    "tool_portfolio_get_summary": tool_portfolio_get_summary,
    "tool_portfolio_get_analysis": tool_portfolio_get_analysis,
    "tool_portfolio_get_cash_balance": tool_portfolio_get_cash_balance,
    "tool_holdings_list": tool_holdings_list,
    "tool_holdings_create": tool_holdings_create,
    "tool_holdings_open_create_form": tool_holdings_open_create_form,
    "tool_holdings_open_sell_form": tool_holdings_open_sell_form,
    "tool_holdings_open_edit_form": tool_holdings_open_edit_form,
    "tool_holdings_update": tool_holdings_update,
    "tool_holdings_sell": tool_holdings_sell,
    "tool_cash_open_transaction_form": tool_cash_open_transaction_form,
    "tool_cash_deposit": tool_cash_deposit,
    "tool_cash_withdraw": tool_cash_withdraw,
    "tool_transactions_list": tool_transactions_list,
    "tool_market_get_quote": tool_market_get_quote,
    "tool_market_get_live_board": tool_market_get_live_board,
    "tool_overview_get_dashboard": tool_overview_get_dashboard,
    "tool_analytics_get_risk": tool_analytics_get_risk,
    "tool_analytics_get_allocation": tool_analytics_get_allocation,
    "tool_analytics_get_efficient_frontier": tool_analytics_get_efficient_frontier,
    "tool_analytics_get_monte_carlo": tool_analytics_get_monte_carlo,
    "tool_analytics_get_cppi": tool_analytics_get_cppi,
    "tool_onboarding_open_manual_form": tool_onboarding_open_manual_form,
    "tool_onboarding_open_csv_import_form": tool_onboarding_open_csv_import_form,
    "tool_onboarding_import_assets": tool_onboarding_import_assets,
    "tool_onboarding_import_csv": tool_onboarding_import_csv,
    "tool_onboarding_get_status": tool_onboarding_get_status,
    "tool_settings_list_mcp_api_keys": tool_settings_list_mcp_api_keys,
    "tool_settings_open_create_mcp_api_key_form": tool_settings_open_create_mcp_api_key_form,
    "tool_settings_create_mcp_api_key": tool_settings_create_mcp_api_key,
    "tool_settings_rotate_mcp_api_key": tool_settings_rotate_mcp_api_key,
    "tool_settings_revoke_mcp_api_key": tool_settings_revoke_mcp_api_key,
    "tool_exchange_convert": tool_exchange_convert,
    "tool_portfolio_refresh_metrics": tool_portfolio_refresh_metrics,
    "tool_portfolio_rebalance_workflow": tool_portfolio_rebalance_workflow,
}


RESOURCE_HANDLERS: Dict[str, Callable[[HandlerContext, Dict[str, Any]], Any]] = {
    "resource_portfolio_summary": resource_portfolio_summary,
    "resource_portfolio_holdings": resource_portfolio_holdings,
    "resource_portfolio_cash_balance": resource_portfolio_cash_balance,
    "resource_portfolio_transactions": resource_portfolio_transactions,
    "resource_market_quote": resource_market_quote,
    "resource_market_live_board": resource_market_live_board,
    "resource_overview_dashboard": resource_overview_dashboard,
    "resource_analytics_risk": resource_analytics_risk,
    "resource_analytics_allocation": resource_analytics_allocation,
    "resource_analytics_efficient_frontier": resource_analytics_efficient_frontier,
    "resource_analytics_monte_carlo": resource_analytics_monte_carlo,
    "resource_analytics_cppi": resource_analytics_cppi,
    "resource_onboarding_status": resource_onboarding_status,
    "resource_settings_mcp_api_keys": resource_settings_mcp_api_keys,
    "resource_system_health": resource_system_health,
}


PROMPT_HANDLERS: Dict[str, Callable[[HandlerContext, Dict[str, Any]], Any]] = {
    "prompt_portfolio_analysis_summary": prompt_portfolio_analysis_summary,
    "prompt_rebalance_suggestion": prompt_rebalance_suggestion,
    "prompt_onboarding_import_guidance": prompt_onboarding_import_guidance,
}


def _normalize_completion_candidates(candidates: Iterable[str], current_value: str) -> list[str]:
    current = (current_value or "").strip().lower()
    deduped: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        value = str(candidate).strip()
        if not value:
            continue
        lowered = value.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        deduped.append(value)

    if not current:
        return deduped[:100]

    prefix_matches = [value for value in deduped if value.lower().startswith(current)]
    fuzzy_matches = [value for value in deduped if current in value.lower() and value not in prefix_matches]
    return (prefix_matches + fuzzy_matches)[:100]


async def _portfolio_ticker_candidates(ctx: HandlerContext) -> list[str]:
    from app.crud import get_portfolio_holdings, get_user_portfolio

    if not getattr(ctx.auth, "username", None):
        return []

    user = await _get_current_user(ctx)
    portfolio = await get_user_portfolio(ctx.db, user.id)
    if not portfolio:
        return []

    holdings = await get_portfolio_holdings(ctx.db, portfolio.id, skip=0, limit=None)
    return [holding.ticker for holding in holdings if getattr(holding, "is_active", True)]


async def complete_prompt_argument(ctx: HandlerContext, prompt_name: str, argument_name: str, current_value: str) -> list[str]:
    normalized_argument = argument_name.strip().lower()

    if normalized_argument == "currency":
        return _normalize_completion_candidates(["USD", "CAD"], current_value)

    if prompt_name == "portfolio.analysis.summary" and normalized_argument == "question":
        return _normalize_completion_candidates(
            [
                "Summarize concentration risk",
                "What are the largest positions?",
                "How diversified is the portfolio?",
                "Which holdings are underperforming?",
                "What changed most recently?",
            ],
            current_value,
        )

    if prompt_name == "portfolio.rebalance.suggestion" and normalized_argument == "objective":
        return _normalize_completion_candidates(
            [
                "Reduce concentration risk",
                "Raise cash",
                "Rebalance to targets",
                "Improve diversification",
                "Limit sector exposure",
            ],
            current_value,
        )

    if prompt_name == "portfolio.onboarding.import_guidance" and normalized_argument == "source":
        return _normalize_completion_candidates(["CSV", "Broker export", "Manual entry", "Spreadsheet"], current_value)

    return []


async def complete_resource_argument(ctx: HandlerContext, uri: str, argument_name: str, current_value: str) -> list[str]:
    normalized_argument = argument_name.strip().lower()
    if normalized_argument != "symbol":
        return []

    if not uri.startswith("market://quote"):
        return []

    candidates = [
        "AAPL",
        "MSFT",
        "GOOGL",
        "AMZN",
        "NVDA",
        "TSLA",
        "VOO",
        "SPY",
        "QQQ",
    ]
    candidates.extend(await _portfolio_ticker_candidates(ctx))
    return _normalize_completion_candidates(candidates, current_value)


async def notify_resource_updated(uri: str) -> int:
    return await session_store.publish_to_subscribers(
        uri,
        {
            "jsonrpc": "2.0",
            "method": "notifications/resources/updated",
            "params": {"uri": uri},
        },
    )