"""
Pydantic schemas for transactions.
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

from app.models.transaction import TransactionType


class TransactionBase(BaseModel):
    """Base schema for a transaction."""

    asset_id: int
    transaction_type: TransactionType
    quantity: float
    price: float
    transaction_date: Optional[datetime] = None
    notes: Optional[str] = None


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