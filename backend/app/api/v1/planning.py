"""Authenticated valuation, allocation planning and complete CSV export."""
import csv
import io
import re
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.crud import get_user_portfolio
from app.models import User, Transaction
from app.schemas.planning import AllocationTargets
from app.services.portfolio_snapshot import build_portfolio_snapshot
from app.utils.dependencies import get_current_active_user
from app.services.cache_invalidation import invalidate_portfolio_cache

router = APIRouter()


async def owned_portfolio(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_active_user)):
    portfolio = await get_user_portfolio(db, user.id)
    if not portfolio:
        raise HTTPException(404, "Portfolio not found")
    return portfolio


@router.get("/snapshot")
async def snapshot(
    currency: Literal["USD", "CAD"] | None = Query(None),
    portfolio=Depends(owned_portfolio),
):
    try:
        return await build_portfolio_snapshot(portfolio, currency or portfolio.currency.upper())
    except (ValueError, TimeoutError) as exc:
        raise HTTPException(503, "Exchange rate unavailable. Try your portfolio's base currency or retry.") from exc


@router.put("/targets")
async def save_targets(
    targets: AllocationTargets,
    portfolio=Depends(owned_portfolio),
    db: AsyncSession = Depends(get_db),
):
    active = {h.ticker: h for h in portfolio.holdings if h.is_active and h.quantity > 0}
    unknown = set(targets.weights) - set(active) - {"CASH"}
    if unknown:
        raise HTTPException(422, "Targets must reference your current holdings")
    for ticker, holding in active.items():
        holding.target_allocation = targets.weights.get(ticker, 0.0)
    await db.commit()
    await invalidate_portfolio_cache(portfolio.id)
    return {"weights": targets.weights, "message": "Allocation targets saved"}


def csv_cell(value):
    """Prevent formula execution when exported text is opened in a spreadsheet."""
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


@router.get("/export")
async def export_portfolio(
    kind: Literal["holdings", "transactions"] = Query("holdings"),
    currency: Literal["USD", "CAD"] | None = Query(None),
    portfolio=Depends(owned_portfolio),
    db: AsyncSession = Depends(get_db),
):
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    if kind == "holdings":
        data = await snapshot(currency=currency, portfolio=portfolio)
        fields = ["ticker", "name", "asset_currency", "quantity", "current_price", "market_value",
                  "cost_basis", "unrealized_gain_loss", "target_allocation", "price_as_of", "price_source"]
        writer.writerow([*fields, "display_currency"])
        for row in data["holdings"]:
            writer.writerow([*(csv_cell(row.get(field)) for field in fields), data["currency"]])
        cash_target = None
        if any(row["target_allocation"] is not None for row in data["holdings"]):
            cash_target = max(0.0, 100 - sum(row["target_allocation"] or 0 for row in data["holdings"]))
        writer.writerow(["CASH", "Cash balance", portfolio.currency, "", "", data["cash_balance"], "", "", cash_target, "", "cash_balance", data["currency"]])
    else:
        result = await db.execute(select(Transaction).options(selectinload(Transaction.asset))
                                  .where(Transaction.portfolio_id == portfolio.id)
                                  .order_by(Transaction.transaction_date, Transaction.id))
        writer.writerow(["id", "date", "type", "ticker", "quantity", "price", "total_amount", "currency", "notes"])
        for tx in result.scalars():
            cash_currency = re.search(r"\[Currency:\s*([A-Za-z]{3})\]", tx.notes or "")
            writer.writerow([csv_cell(value) for value in [tx.id, tx.transaction_date.isoformat(),
                tx.transaction_type.value, tx.asset.ticker if tx.asset else "", tx.quantity,
                tx.price, tx.price * (tx.quantity if tx.quantity is not None else 1),
                tx.asset.currency if tx.asset else (cash_currency.group(1).upper() if cash_currency else portfolio.currency), tx.notes]])
    return Response("\ufeff" + output.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="portfolio-{kind}.csv"',
                             "Cache-Control": "no-store"})
