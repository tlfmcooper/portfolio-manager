"""
API endpoints for transactions.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app import crud
from app.schemas.transaction import (
    Transaction,
    TransactionCreate,
    TransactionUpdate,
    CashTransactionCreate,
    TransactionWithAsset
)
from app.core.database import get_db
from app.core.redis_client import get_redis_client
from app.models.user import User
from app.models.transaction import TransactionType
from app.utils.dependencies import get_current_active_user
from app.crud.portfolio_extended import update_portfolio_cash_balance, get_portfolio_cash_balance
from app.crud.transaction import create_cash_transaction, get_total_realized_gains, get_realized_gains_by_asset
from app.services.exchange_rate_service import get_exchange_rate_service

router = APIRouter()


async def invalidate_dashboard_cache(portfolio_id: int):
    """Invalidate dashboard cache for all currencies after cash transactions."""
    redis_client = await get_redis_client()
    try:
        # Invalidate cache for both USD and CAD views
        for currency in ["USD", "CAD"]:
            cache_key = f"dashboard:overview:{portfolio_id}:{currency}"
            await redis_client.delete(cache_key)
        print(f"[CACHE] Invalidated dashboard cache for portfolio {portfolio_id}")
    except Exception as e:
        print(f"[CACHE] Failed to invalidate cache: {e}")
        pass  # Continue even if cache invalidation fails


@router.post("/{portfolio_id}/transactions/", response_model=Transaction)
async def create_transaction(
    portfolio_id: int,
    *, 
    db: AsyncSession = Depends(get_db),
    transaction_in: TransactionCreate
):
    """Create new transaction."""
    transaction = await crud.transaction.create_transaction(
        db=db, portfolio_id=portfolio_id, obj_in=transaction_in
    )
    return transaction


@router.get("/{portfolio_id}/transactions/", response_model=List[Transaction])
async def read_transactions(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
):
    """Retrieve transactions for a portfolio."""
    transactions = await crud.transaction.get_transactions_by_portfolio(
        db=db, portfolio_id=portfolio_id, skip=skip, limit=limit
    )
    return transactions


@router.get("/transactions/{transaction_id}", response_model=Transaction)
async def read_transaction(
    transaction_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve transaction by ID."""
    transaction = await crud.transaction.get_transaction(db=db, transaction_id=transaction_id)
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction


@router.put("/transactions/{transaction_id}", response_model=Transaction)
async def update_transaction(
    transaction_id: int,
    *, 
    db: AsyncSession = Depends(get_db),
    transaction_in: TransactionUpdate,
):
    """Update a transaction."""
    transaction = await crud.transaction.get_transaction(db=db, transaction_id=transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    transaction = await crud.transaction.update_transaction(
        db=db, db_obj=transaction, obj_in=transaction_in
    )
    return transaction


@router.delete("/transactions/{transaction_id}", response_model=Transaction)
async def delete_transaction(
    transaction_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a transaction."""
    transaction = await crud.transaction.get_transaction(db=db, transaction_id=transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    await crud.transaction.delete_transaction(db=db, db_obj=transaction)
    return transaction


@router.post("/{portfolio_id}/cash/deposit")
async def deposit_cash(
    portfolio_id: int,
    cash_in: CashTransactionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Deposit cash into portfolio.

    This creates a DEPOSIT transaction and increases the portfolio's cash balance.
    """
    print(f"[DEPOSIT] Starting deposit for portfolio {portfolio_id}, amount: {cash_in.amount}")

    try:
        # Verify portfolio belongs to user
        print(f"[DEPOSIT] Fetching portfolio for user {current_user.id}")
        portfolio = await crud.portfolio.get_user_portfolio(db, current_user.id)
        print(f"[DEPOSIT] Portfolio fetched: {portfolio.id if portfolio else 'None'}")

        if not portfolio or portfolio.id != portfolio_id:
            raise HTTPException(status_code=404, detail="Portfolio not found")
    except Exception as e:
        print(f"[DEPOSIT ERROR] Failed to fetch portfolio: {type(e).__name__}: {str(e)}")
        raise

    if cash_in.amount <= 0:
        raise HTTPException(status_code=400, detail="Deposit amount must be positive")

    if cash_in.transaction_type != TransactionType.DEPOSIT:
        raise HTTPException(status_code=400, detail="Transaction type must be DEPOSIT")

    try:
        # Determine the currency of the deposit and convert if needed
        deposit_currency = (cash_in.currency or portfolio.currency).upper()
        portfolio_currency = portfolio.currency.upper()
        original_amount = cash_in.amount

        # Convert to portfolio currency if different
        if deposit_currency != portfolio_currency:
            exchange_service = get_exchange_rate_service()
            exchange_rate = await exchange_service.get_exchange_rate(deposit_currency, portfolio_currency)
            converted_amount = original_amount * exchange_rate
            print(f"[DEPOSIT] Converting {original_amount} {deposit_currency} -> {converted_amount:.2f} {portfolio_currency} (rate: {exchange_rate})")
        else:
            converted_amount = original_amount
            exchange_rate = 1.0

        # Create transaction (record original amount and currency)
        print(f"[DEPOSIT] Creating transaction...")
        transaction = await create_cash_transaction(
            db=db,
            portfolio_id=portfolio_id,
            transaction_type=TransactionType.DEPOSIT,
            amount=original_amount,
            notes=f"{cash_in.notes or ''} [Currency: {deposit_currency}]".strip()
        )
        print(f"[DEPOSIT] Transaction created: {transaction.id}")

        # Update portfolio cash balance (using converted amount)
        print(f"[DEPOSIT] Updating portfolio balance...")
        updated_portfolio = await update_portfolio_cash_balance(
            db=db,
            portfolio_id=portfolio_id,
            amount=converted_amount,
            operation="add"
        )
        print(f"[DEPOSIT] Balance updated. New balance: {updated_portfolio.cash_balance if updated_portfolio else 'None'}")

        if not updated_portfolio:
            raise HTTPException(status_code=404, detail="Portfolio not found during update")

        # Invalidate dashboard cache
        await invalidate_dashboard_cache(portfolio_id)

        print(f"[DEPOSIT] SUCCESS - Deposit completed")
        return {
            "message": "Cash deposited successfully",
            "transaction_id": transaction.id,
            "amount_original": original_amount,
            "amount_original_currency": deposit_currency,
            "amount_converted": converted_amount,
            "amount_converted_currency": portfolio_currency,
            "exchange_rate": exchange_rate,
            "new_balance": updated_portfolio.cash_balance
        }
    except Exception as e:
        print(f"[DEPOSIT ERROR] Transaction/update failed: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


@router.post("/{portfolio_id}/cash/withdrawal")
async def withdraw_cash(
    portfolio_id: int,
    cash_in: CashTransactionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Withdraw cash from portfolio.

    This creates a WITHDRAWAL transaction and decreases the portfolio's cash balance.
    Validates that sufficient cash is available.
    """
    # Verify portfolio belongs to user
    portfolio = await crud.portfolio.get_user_portfolio(db, current_user.id)
    if not portfolio or portfolio.id != portfolio_id:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    if cash_in.amount <= 0:
        raise HTTPException(status_code=400, detail="Withdrawal amount must be positive")

    if cash_in.transaction_type != TransactionType.WITHDRAWAL:
        raise HTTPException(status_code=400, detail="Transaction type must be WITHDRAWAL")

    # Determine the currency of the withdrawal and convert if needed
    withdrawal_currency = (cash_in.currency or portfolio.currency).upper()
    portfolio_currency = portfolio.currency.upper()
    original_amount = cash_in.amount

    # Convert to portfolio currency if different
    if withdrawal_currency != portfolio_currency:
        exchange_service = get_exchange_rate_service()
        exchange_rate = await exchange_service.get_exchange_rate(withdrawal_currency, portfolio_currency)
        converted_amount = original_amount * exchange_rate
    else:
        converted_amount = original_amount
        exchange_rate = 1.0

    # Check sufficient balance (in portfolio currency)
    if portfolio.cash_balance < converted_amount:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient cash balance. Available: {portfolio.cash_balance} {portfolio_currency}, Requested: {converted_amount:.2f} {portfolio_currency} ({original_amount} {withdrawal_currency})"
        )

    # Create transaction (record original amount and currency)
    transaction = await create_cash_transaction(
        db=db,
        portfolio_id=portfolio_id,
        transaction_type=TransactionType.WITHDRAWAL,
        amount=original_amount,
        notes=f"{cash_in.notes or ''} [Currency: {withdrawal_currency}]".strip()
    )

    # Update portfolio cash balance (using converted amount)
    updated_portfolio = await update_portfolio_cash_balance(
        db=db,
        portfolio_id=portfolio_id,
        amount=converted_amount,
        operation="subtract"
    )

    if not updated_portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found during update")

    # Invalidate dashboard cache
    await invalidate_dashboard_cache(portfolio_id)

    return {
        "message": "Cash withdrawn successfully",
        "transaction_id": transaction.id,
        "amount_original": original_amount,
        "amount_original_currency": withdrawal_currency,
        "amount_converted": converted_amount,
        "amount_converted_currency": portfolio_currency,
        "exchange_rate": exchange_rate,
        "new_balance": updated_portfolio.cash_balance
    }


@router.get("/{portfolio_id}/cash/balance")
async def get_cash_balance(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    currency: Optional[str] = Query(None, description="Currency to display balance in")
):
    """
    Get portfolio cash balance.

    Optionally convert to specified currency.
    """
    # Verify portfolio belongs to user
    portfolio = await crud.portfolio.get_user_portfolio(db, current_user.id)
    if not portfolio or portfolio.id != portfolio_id:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    balance_info = await get_portfolio_cash_balance(
        db=db,
        portfolio_id=portfolio_id,
        display_currency=currency
    )

    return balance_info


@router.get("/{portfolio_id}/realized-gains")
async def get_realized_gains(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get total realized gains/losses from all SELL transactions.

    Calculated using FIFO cost basis method.
    """
    # Verify portfolio belongs to user
    portfolio = await crud.portfolio.get_user_portfolio(db, current_user.id)
    if not portfolio or portfolio.id != portfolio_id:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    total_realized = await get_total_realized_gains(db, portfolio_id)

    return {
        "portfolio_id": portfolio_id,
        "total_realized_gains": total_realized,
        "currency": portfolio.currency
    }


@router.get("/{portfolio_id}/realized-gains/detailed")
async def get_realized_gains_detailed(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get detailed realized gains/losses by asset.

    Returns breakdown showing:
    - Ticker symbol
    - Asset name
    - Quantity sold
    - Cost basis
    - Sale proceeds
    - Realized gain/loss

    Calculated using FIFO cost basis method.
    """
    # Verify portfolio belongs to user
    portfolio = await crud.portfolio.get_user_portfolio(db, current_user.id)
    if not portfolio or portfolio.id != portfolio_id:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    realized_gains = await get_realized_gains_by_asset(db, portfolio_id)

    return {
        "portfolio_id": portfolio_id,
        "currency": portfolio.currency,
        "realized_gains": realized_gains,
        "total": sum(item["realized_gain_loss"] for item in realized_gains)
    }
