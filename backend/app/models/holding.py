"""
Holding model for individual asset positions within portfolios.
"""

from sqlalchemy import (
    Column,
    Integer,
    Float,
    DateTime,
    ForeignKey,
    Text,
    Boolean,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from typing import TYPE_CHECKING

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.portfolio import Portfolio
    from app.models.asset import Asset


class Holding(Base):
    """Holding model for individual asset positions within a portfolio."""

    __tablename__ = "holdings"
    __table_args__ = (
        UniqueConstraint("portfolio_id", "ticker", name="unique_portfolio_ticker"),
    )

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False, index=True)
    ticker = Column(String(20), index=True, nullable=False)  # aggregate by ticker

    # Position details
    quantity = Column(Float, nullable=False)
    average_cost = Column(Float, nullable=False)
    current_price = Column(Float, nullable=True)
    target_allocation = Column(Float, nullable=True)  # Target percentage (0-100)

    # Values (calculated or cached)
    cost_basis = Column(Float, nullable=True)  # quantity * average_cost
    market_value = Column(Float, nullable=True)  # quantity * current_price
    unrealized_gain_loss = Column(Float, nullable=True)
    unrealized_gain_loss_percentage = Column(Float, nullable=True)

    # Metadata
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

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

    # Relationships
    portfolio = relationship("Portfolio", back_populates="holdings")
    asset = relationship("Asset", back_populates="holdings")

    def __repr__(self) -> str:
        return f"<Holding(id={self.id}, portfolio_id={self.portfolio_id}, asset_id={self.asset_id}, quantity={self.quantity})>"

    @property
    def total_cost(self) -> float:
        """Calculate total cost basis."""
        return self.quantity * self.average_cost

    @property
    def current_value(self) -> float:
        """Calculate current market value."""
        if self.current_price is None:
            return self.total_cost  # Fallback to cost if no current price
        return self.quantity * self.current_price

    @property
    def gain_loss(self) -> float:
        """Calculate unrealized gain/loss."""
        return self.current_value - self.total_cost

    @property
    def gain_loss_percentage(self) -> float:
        """Calculate unrealized gain/loss percentage."""
        if self.total_cost == 0:
            return 0.0
        return (self.gain_loss / self.total_cost) * 100
