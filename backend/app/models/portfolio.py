"""
Portfolio model for user investment portfolios.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from typing import TYPE_CHECKING

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.holding import Holding


class Portfolio(Base):
    """Portfolio model for managing user investment portfolios."""
    
    __tablename__ = "portfolios"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    name = Column(String(100), default="My Portfolio", nullable=False)
    description = Column(Text, nullable=True)
    initial_value = Column(Float, default=0.0, nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Portfolio settings
    risk_tolerance = Column(String(20), nullable=True)  # conservative, moderate, aggressive
    investment_objective = Column(String(50), nullable=True)  # growth, income, balanced
    time_horizon = Column(String(20), nullable=True)  # short, medium, long
    
    # Performance tracking
    total_invested = Column(Float, default=0.0, nullable=False)
    total_value = Column(Float, default=0.0, nullable=False)
    total_return = Column(Float, default=0.0, nullable=False)
    total_return_percentage = Column(Float, default=0.0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_rebalance = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="portfolio")
    holdings = relationship("Holding", back_populates="portfolio", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Portfolio(id={self.id}, name='{self.name}', user_id={self.user_id})>"
    
    @property
    def total_holdings_count(self) -> int:
        """Get the total number of holdings in the portfolio."""
        return len(self.holdings) if self.holdings else 0
    
    @property
    def diversification_score(self) -> float:
        """Calculate a simple diversification score based on number of holdings."""
        if not self.holdings:
            return 0.0
        # Simple calculation - can be made more sophisticated
        return min(1.0, len(self.holdings) / 10)  # Max score at 10+ holdings
