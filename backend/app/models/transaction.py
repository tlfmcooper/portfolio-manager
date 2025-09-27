"""
Transaction model for recording buy/sell activities.
"""
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    Enum,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from typing import TYPE_CHECKING
import enum

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.portfolio import Portfolio
    from app.models.asset import Asset


class TransactionType(enum.Enum):
    """Enum for transaction types."""

    BUY = "BUY"
    SELL = "SELL"


class Transaction(Base):
    """Transaction model for recording buy/sell activities."""

    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    transaction_type = Column(Enum(TransactionType), nullable=False)
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    transaction_date = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    notes = Column(String, nullable=True)

    # Relationships
    portfolio = relationship("Portfolio", back_populates="transactions")
    asset = relationship("Asset", back_populates="transactions")

    def __repr__(self) -> str:
        return f"<Transaction(id={self.id}, type='{self.transaction_type}', quantity={self.quantity}, price={self.price})>"