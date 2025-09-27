"""
CRUD operations for transactions.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional

from app.models.transaction import Transaction
from app.schemas.transaction import TransactionCreate, TransactionUpdate


async def get_transaction(
    db: AsyncSession, transaction_id: int
) -> Optional[Transaction]:
    """Get a transaction by ID."""
    return await db.get(Transaction, transaction_id)


async def get_transactions_by_portfolio(
    db: AsyncSession, portfolio_id: int, skip: int = 0, limit: int = 100
) -> List[Transaction]:
    """Get all transactions for a portfolio."""
    result = await db.execute(
        select(Transaction)
        .where(Transaction.portfolio_id == portfolio_id)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


async def create_transaction(
    db: AsyncSession, *, portfolio_id: int, obj_in: TransactionCreate
) -> Transaction:
    """Create a new transaction."""
    db_obj = Transaction(
        **obj_in.dict(),
        portfolio_id=portfolio_id,
    )
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def update_transaction(
    db: AsyncSession, *, db_obj: Transaction, obj_in: TransactionUpdate
) -> Transaction:
    """Update a transaction."""
    update_data = obj_in.dict(exclude_unset=True)
    for field in update_data:
        setattr(db_obj, field, update_data[field])
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def delete_transaction(db: AsyncSession, *, db_obj: Transaction) -> None:
    """Delete a transaction."""
    await db.delete(db_obj)
    await db.commit()
