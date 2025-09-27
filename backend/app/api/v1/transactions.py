"""
API endpoints for transactions.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app import crud
from app.schemas.transaction import Transaction, TransactionCreate, TransactionUpdate
from app.core.database import get_db

router = APIRouter()


@router.post("/portfolios/{portfolio_id}/transactions/", response_model=Transaction)
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


@router.get("/portfolios/{portfolio_id}/transactions/", response_model=List[Transaction])
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
