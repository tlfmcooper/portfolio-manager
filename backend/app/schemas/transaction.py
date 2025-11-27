"""
Pydantic schemas for transactions.
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

from app.models.transaction import TransactionType


class TransactionBase(BaseModel):
    """Base schema for a transaction."""

    asset_id: Optional[int] = None  # Nullable for DEPOSIT/WITHDRAWAL transactions
    transaction_type: TransactionType
    quantity: Optional[float] = None  # Nullable for cash transactions
    price: float  # For asset txns: price per share; for cash txns: amount
    transaction_date: Optional[datetime] = None
    notes: Optional[str] = None
    realized_gain_loss: Optional[float] = None  # Calculated for SELL transactions


class TransactionCreate(TransactionBase):
    """Schema for creating a transaction."""

    pass


class TransactionUpdate(TransactionBase):
    """Schema for updating a transaction."""

    pass


class TransactionInDBBase(TransactionBase):
    """Base schema for a transaction in the database."""

    id: int
    portfolio_id: int

    class Config:
        from_attributes = True


class Transaction(TransactionInDBBase):
    """Schema for a transaction."""

    pass


class CashTransactionCreate(BaseModel):
    """Schema for creating a cash transaction (deposit/withdrawal)."""

    amount: float
    transaction_type: TransactionType  # Must be DEPOSIT or WITHDRAWAL
    notes: Optional[str] = None


class TransactionWithAsset(TransactionInDBBase):
    """Transaction schema with asset details included."""

    asset_ticker: Optional[str] = None
    asset_name: Optional[str] = None

    class Config:
        from_attributes = True