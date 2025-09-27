"""
Asset model for financial instruments.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from typing import TYPE_CHECKING

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.holding import Holding


class Asset(Base):
    """Asset model for financial instruments (stocks, bonds, ETFs, etc.)."""

    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(20), unique=True, index=True, nullable=False)
    name = Column(String(200), nullable=True)
    asset_type = Column(String(50), nullable=True)  # stock, bond, etf, crypto, etc.
    sector = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    currency = Column(String(3), default="USD", nullable=False)
    exchange = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Market data (optional cached values)
    current_price = Column(Float, nullable=True)
    market_cap = Column(Float, nullable=True)
    dividend_yield = Column(Float, nullable=True)
    pe_ratio = Column(Float, nullable=True)
    beta = Column(Float, nullable=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    last_price_update = Column(DateTime(timezone=True), nullable=True)

    # Relationship to holdings
    holdings = relationship(
        "Holding", back_populates="asset", cascade="all, delete-orphan"
    )

    # Relationship to transactions
    transactions = relationship(
        "Transaction", back_populates="asset", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Asset(id={self.id}, ticker='{self.ticker}', name='{self.name}')>"

    @property
    def display_name(self) -> str:
        """Get the display name for the asset."""
        return f"{self.ticker} - {self.name}" if self.name else self.ticker
