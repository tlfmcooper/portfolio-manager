"""
CRUD operations for transactions.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime

from app.models.transaction import Transaction, TransactionType
from app.schemas.transaction import TransactionCreate, TransactionUpdate


async def get_transaction(
    db: AsyncSession, transaction_id: int
) -> Optional[Transaction]:
    """Get a transaction by ID."""
    return await db.get(Transaction, transaction_id)


async def get_transactions_by_portfolio(
    db: AsyncSession, portfolio_id: int, skip: int = 0, limit: int = 100
) -> List[Transaction]:
    """Get all transactions for a portfolio, ordered by date descending."""
    result = await db.execute(
        select(Transaction)
        .options(selectinload(Transaction.asset))
        .where(Transaction.portfolio_id == portfolio_id)
        .order_by(desc(Transaction.transaction_date))
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


async def create_cash_transaction(
    db: AsyncSession,
    *,
    portfolio_id: int,
    transaction_type: TransactionType,
    amount: float,
    notes: Optional[str] = None
) -> Transaction:
    """
    Create a cash transaction (DEPOSIT or WITHDRAWAL).

    Args:
        db: Database session
        portfolio_id: Portfolio ID
        transaction_type: DEPOSIT or WITHDRAWAL
        amount: Amount of cash (positive value)
        notes: Optional notes

    Returns:
        Created transaction
    """
    if transaction_type not in [TransactionType.DEPOSIT, TransactionType.WITHDRAWAL]:
        raise ValueError("Transaction type must be DEPOSIT or WITHDRAWAL")

    db_obj = Transaction(
        portfolio_id=portfolio_id,
        asset_id=None,  # No asset for cash transactions
        transaction_type=transaction_type,
        quantity=None,  # No quantity for cash transactions
        price=amount,  # Store amount in price field
        transaction_date=datetime.utcnow(),
        notes=notes,
        realized_gain_loss=None
    )
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def get_buy_transactions_for_asset(
    db: AsyncSession,
    portfolio_id: int,
    asset_id: int
) -> List[Transaction]:
    """
    Get all BUY transactions for a specific asset in a portfolio, ordered by date (FIFO).
    Used for calculating cost basis when selling.

    Args:
        db: Database session
        portfolio_id: Portfolio ID
        asset_id: Asset ID

    Returns:
        List of BUY transactions ordered by date (oldest first)
    """
    result = await db.execute(
        select(Transaction)
        .where(
            Transaction.portfolio_id == portfolio_id,
            Transaction.asset_id == asset_id,
            Transaction.transaction_type == TransactionType.BUY
        )
        .order_by(Transaction.transaction_date)  # FIFO: oldest first
    )
    return result.scalars().all()


async def calculate_realized_gain_loss_fifo(
    db: AsyncSession,
    portfolio_id: int,
    asset_id: int,
    sell_quantity: float,
    sell_price: float
) -> float:
    """
    Calculate realized gain/loss for a SELL transaction using FIFO method.

    FIFO (First In, First Out) means we sell the oldest shares first.

    Args:
        db: Database session
        portfolio_id: Portfolio ID
        asset_id: Asset ID being sold
        sell_quantity: Quantity being sold
        sell_price: Price per share at sale

    Returns:
        Realized gain/loss amount
    """
    # Get all BUY transactions for this asset (oldest first)
    buy_transactions = await get_buy_transactions_for_asset(db, portfolio_id, asset_id)

    if not buy_transactions:
        # No buy history, assume cost basis is 0 (unrealistic but handles edge case)
        return sell_quantity * sell_price

    remaining_to_sell = sell_quantity
    total_cost_basis = 0.0

    # Calculate cost basis using FIFO
    for buy_txn in buy_transactions:
        if remaining_to_sell <= 0:
            break

        buy_quantity = buy_txn.quantity
        buy_price = buy_txn.price

        # How many shares from this buy transaction are we selling?
        shares_from_this_buy = min(remaining_to_sell, buy_quantity)

        # Add to cost basis
        total_cost_basis += shares_from_this_buy * buy_price

        # Update remaining
        remaining_to_sell -= shares_from_this_buy

    # Calculate realized gain/loss
    total_proceeds = sell_quantity * sell_price
    realized_gain_loss = total_proceeds - total_cost_basis

    return realized_gain_loss


async def get_total_realized_gains(
    db: AsyncSession,
    portfolio_id: int
) -> float:
    """
    Calculate total realized gains/losses for a portfolio.
    Sums up all realized_gain_loss values from SELL transactions.

    Args:
        db: Database session
        portfolio_id: Portfolio ID

    Returns:
        Total realized gain/loss
    """
    result = await db.execute(
        select(Transaction)
        .where(
            Transaction.portfolio_id == portfolio_id,
            Transaction.transaction_type == TransactionType.SELL,
            Transaction.realized_gain_loss.isnot(None)
        )
    )
    sell_transactions = result.scalars().all()

    total_realized = sum(txn.realized_gain_loss for txn in sell_transactions if txn.realized_gain_loss)
    return total_realized
