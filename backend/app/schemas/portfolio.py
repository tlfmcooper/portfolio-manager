"""
Portfolio schemas for API request/response models.
"""
from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field, validator


class PortfolioBase(BaseModel):
    """Base portfolio schema with common fields."""
    name: str = Field(..., min_length=1, max_length=100, description="Portfolio name")
    description: Optional[str] = Field(None, max_length=500, description="Portfolio description")
    currency: str = Field(default="USD", description="Portfolio currency")
    risk_tolerance: Optional[str] = Field(None, description="Risk tolerance level")
    investment_objective: Optional[str] = Field(None, description="Investment objective")
    time_horizon: Optional[str] = Field(None, description="Investment time horizon")
    
    @validator("currency")
    def validate_currency(cls, v):
        """Validate currency code."""
        if len(v) != 3:
            raise ValueError("Currency must be a 3-letter code")
        return v.upper()
    
    @validator("risk_tolerance")
    def validate_risk_tolerance(cls, v):
        """Validate risk tolerance."""
        if v and v not in ["conservative", "moderate", "aggressive"]:
            raise ValueError("Risk tolerance must be conservative, moderate, or aggressive")
        return v
    
    @validator("investment_objective")
    def validate_investment_objective(cls, v):
        """Validate investment objective."""
        if v and v not in ["growth", "income", "balanced"]:
            raise ValueError("Investment objective must be growth, income, or balanced")
        return v
    
    @validator("time_horizon")
    def validate_time_horizon(cls, v):
        """Validate time horizon."""
        if v and v not in ["short", "medium", "long"]:
            raise ValueError("Time horizon must be short, medium, or long")
        return v
