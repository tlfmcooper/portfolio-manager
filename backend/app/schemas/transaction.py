"""
Transaction schemas for API request/response models.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class TransactionBase(BaseModel):
    ticker: str = Field(
        ..., min_length=1, max_length=20, description="Asset ticker symbol"
    )
    type: str = Field(..., description="Transaction type: buy or sell")
    quantity: float = Field(..., gt=0, description="Number of shares/units")
    price: float = Field(..., gt=0, description="Price per share/unit")
    date: Optional[datetime] = None
    portfolio_id: int


class TransactionCreate(TransactionBase):
    pass


class TransactionInDB(TransactionBase):
    id: int
    date: Optional[datetime] = None

    class Config:
        from_attributes = True
