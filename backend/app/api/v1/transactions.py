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
from app.models.user import User
from app.models.transaction import TransactionType
from app.utils.dependencies import get_current_active_user
from app.crud.portfolio_extended import update_portfolio_cash_balance, get_portfolio_cash_balance
from app.crud.transaction import create_cash_transaction, get_total_realized_gains, get_realized_gains_by_asset

router = APIRouter()


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
        # Create transaction
        print(f"[DEPOSIT] Creating transaction...")
        transaction = await create_cash_transaction(
            db=db,
            portfolio_id=portfolio_id,
            transaction_type=TransactionType.DEPOSIT,
            amount=cash_in.amount,
            notes=cash_in.notes
        )
        print(f"[DEPOSIT] Transaction created: {transaction.id}")

        # Update portfolio cash balance
        print(f"[DEPOSIT] Updating portfolio balance...")
        updated_portfolio = await update_portfolio_cash_balance(
            db=db,
            portfolio_id=portfolio_id,
            amount=cash_in.amount,
            operation="add"
        )
        print(f"[DEPOSIT] Balance updated. New balance: {updated_portfolio.cash_balance if updated_portfolio else 'None'}")

        if not updated_portfolio:
            raise HTTPException(status_code=404, detail="Portfolio not found during update")

        print(f"[DEPOSIT] SUCCESS - Deposit completed")
        return {
            "message": "Cash deposited successfully",
            "transaction_id": transaction.id,
            "amount": cash_in.amount,
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

    # Check sufficient balance
    if portfolio.cash_balance < cash_in.amount:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient cash balance. Available: {portfolio.cash_balance}, Requested: {cash_in.amount}"
        )

    # Create transaction
    transaction = await create_cash_transaction(
        db=db,
        portfolio_id=portfolio_id,
        transaction_type=TransactionType.WITHDRAWAL,
        amount=cash_in.amount,
        notes=cash_in.notes
    )

    # Update portfolio cash balance
    updated_portfolio = await update_portfolio_cash_balance(
        db=db,
        portfolio_id=portfolio_id,
        amount=cash_in.amount,
        operation="subtract"
    )

    if not updated_portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found during update")

    return {
        "message": "Cash withdrawn successfully",
        "transaction_id": transaction.id,
        "amount": cash_in.amount,
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
