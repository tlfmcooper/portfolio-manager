"""
Asset schemas for API request/response models.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, validator


class AssetBase(BaseModel):
    """Base asset schema with common fields."""
    ticker: str = Field(..., min_length=1, max_length=20, description="Asset ticker symbol")
    name: Optional[str] = Field(None, max_length=200, description="Asset name")
    asset_type: Optional[str] = Field(None, max_length=50, description="Asset type")
    sector: Optional[str] = Field(None, max_length=100, description="Asset sector")
    industry: Optional[str] = Field(None, max_length=100, description="Asset industry")
    currency: str = Field(default="USD", description="Asset currency")
    exchange: Optional[str] = Field(None, max_length=50, description="Exchange")
    
    @validator("ticker")
    def validate_ticker(cls, v):
        """Validate ticker symbol."""
        return v.upper().strip()
    
    @validator("currency")
    def validate_currency(cls, v):
        """Validate currency code."""
        if len(v) != 3:
            raise ValueError("Currency must be a 3-letter code")
        return v.upper()


class AssetCreate(AssetBase):
    """Schema for creating a new asset."""
    pass


class AssetUpdate(BaseModel):
    """Schema for updating asset information."""
    name: Optional[str] = Field(None, max_length=200)
    asset_type: Optional[str] = Field(None, max_length=50)
    sector: Optional[str] = Field(None, max_length=100)
    industry: Optional[str] = Field(None, max_length=100)
    current_price: Optional[float] = Field(None, ge=0)
    market_cap: Optional[float] = Field(None, ge=0)
    dividend_yield: Optional[float] = Field(None, ge=0)
    pe_ratio: Optional[float] = Field(None, ge=0)
    beta: Optional[float] = None
