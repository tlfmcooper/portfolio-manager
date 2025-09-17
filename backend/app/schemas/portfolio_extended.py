"""
Portfolio schemas continued - Create, Update, and Response models.
"""
from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from app.schemas.portfolio import PortfolioBase


class PortfolioCreate(PortfolioBase):
    """Schema for creating a new portfolio."""
    initial_value: float = Field(default=0.0, ge=0, description="Initial portfolio value")


class PortfolioUpdate(BaseModel):
    """Schema for updating portfolio information."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    risk_tolerance: Optional[str] = None
    investment_objective: Optional[str] = None
    time_horizon: Optional[str] = None


class PortfolioInDB(PortfolioBase):
    """Schema for portfolio data stored in database."""
    id: int
    user_id: int
    initial_value: float
    total_invested: float
    total_value: float
    total_return: float
    total_return_percentage: float
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_rebalance: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class PortfolioSummary(BaseModel):
    """Schema for portfolio summary data."""
    id: int
    name: str
    total_value: float
    total_return: float
    total_return_percentage: float
    total_holdings_count: int
    diversification_score: float
    currency: str
    last_updated: datetime
    
    class Config:
        from_attributes = True
