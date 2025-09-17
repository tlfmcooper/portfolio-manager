"""
Holding schemas for API request/response models.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, validator


class HoldingBase(BaseModel):
    """Base holding schema with common fields."""
    quantity: float = Field(..., gt=0, description="Number of shares/units held")
    average_cost: float = Field(..., gt=0, description="Average cost per share/unit")
    target_allocation: Optional[float] = Field(None, ge=0, le=100, description="Target allocation percentage")
    notes: Optional[str] = Field(None, max_length=500, description="Notes about the holding")


class HoldingCreate(HoldingBase):
    """Schema for creating a new holding."""
    asset_ticker: str = Field(..., description="Asset ticker symbol")
    
    @validator("asset_ticker")
    def validate_ticker(cls, v):
        """Validate ticker symbol."""
        return v.upper().strip()


class HoldingUpdate(BaseModel):
    """Schema for updating holding information."""
    quantity: Optional[float] = Field(None, gt=0)
    average_cost: Optional[float] = Field(None, gt=0)
    target_allocation: Optional[float] = Field(None, ge=0, le=100)
    notes: Optional[str] = Field(None, max_length=500)


class HoldingInDB(HoldingBase):
    """Schema for holding data stored in database."""
    id: int
    portfolio_id: int
    asset_id: int
    current_price: Optional[float] = None
    cost_basis: Optional[float] = None
    market_value: Optional[float] = None
    unrealized_gain_loss: Optional[float] = None
    unrealized_gain_loss_percentage: Optional[float] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
