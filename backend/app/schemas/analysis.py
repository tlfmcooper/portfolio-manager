"""
Analysis schemas for portfolio and holding performance API responses.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field


class HoldingPerformance(BaseModel):
    """Performance metrics for a single holding."""
    ticker: str = Field(..., description="Asset ticker symbol")
    name: Optional[str] = Field(None, description="Asset name")
    asset_type: Optional[str] = Field(None, description="Type of asset (stock, mutual_fund, crypto)")
    current_price: Optional[float] = Field(None, description="Current price")
    quantity: Optional[float] = Field(None, description="Quantity held")
    market_value: Optional[float] = Field(None, description="Current market value")
    cost_basis: Optional[float] = Field(None, description="Total cost basis")
    
    # Period returns (from external price data)
    ytd_return: Optional[float] = Field(None, description="Year-to-date return percentage")
    one_month_return: Optional[float] = Field(None, description="1-month return percentage")
    three_month_return: Optional[float] = Field(None, description="3-month return percentage")
    one_year_return: Optional[float] = Field(None, description="1-year return percentage")
    
    # Cost basis return (always available)
    gain_loss: Optional[float] = Field(None, description="Unrealized gain/loss amount")
    gain_loss_percent: Optional[float] = Field(None, description="Unrealized gain/loss percentage")
    
    # Metadata
    historical_data_available: bool = Field(True, description="Whether historical price data is available for this asset")
    data_source: Optional[str] = Field(None, description="Source of price data (yfinance, barchart, etc.)")
    last_updated: Optional[datetime] = Field(None, description="When the data was last fetched")
    
    class Config:
        from_attributes = True


class BatchHoldingPerformance(BaseModel):
    """Response for batch holding performance request."""
    holdings: List[HoldingPerformance] = Field(..., description="List of holding performances")
    total_count: int = Field(..., description="Total number of holdings")
    currency: str = Field(..., description="Display currency")
    cached: bool = Field(False, description="Whether the data was served from cache")
    

class PortfolioAnalysisQuery(BaseModel):
    """Query parameters for portfolio analysis."""
    query_type: Literal[
        "largest_holding",
        "smallest_holding",
        "top_performers",
        "worst_performers",
        "holdings_summary",
        "sector_breakdown"
    ] = Field(..., description="Type of analysis to perform")
    limit: Optional[int] = Field(5, ge=1, le=50, description="Number of results to return for list queries")
    period: Optional[Literal["ytd", "1m", "3m", "1y"]] = Field("ytd", description="Time period for performance calculations")
    currency: Optional[str] = Field(None, description="Display currency (USD or CAD)")


class HoldingSummary(BaseModel):
    """Summary info for a holding."""
    ticker: str
    name: Optional[str]
    market_value: float
    quantity: float
    weight_percent: float = Field(..., description="Percentage of total portfolio value")
    gain_loss_percent: Optional[float]
    ytd_return: Optional[float] = None
    historical_data_available: bool = True


class PortfolioAnalysisResponse(BaseModel):
    """Response for portfolio analysis endpoint."""
    query_type: str
    result: Any = Field(..., description="Analysis result - structure depends on query_type")
    currency: str
    period: Optional[str] = None
    total_portfolio_value: Optional[float] = None
    holdings_count: Optional[int] = None
    message: Optional[str] = Field(None, description="Additional context or notes about the analysis")
