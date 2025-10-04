"""Portfolio schemas"""
from pydantic import BaseModel
from typing import List, Dict, Any
from datetime import datetime


class HoldingCreate(BaseModel):
    """Schema for creating a holding"""
    ticker: str
    weight: float  # 0.0 to 1.0


class HoldingResponse(BaseModel):
    """Schema for holding response"""
    id: int
    ticker: str
    weight: float
    created_at: datetime

    class Config:
        from_attributes = True


class PortfolioCreate(BaseModel):
    """Schema for creating a portfolio"""
    name: str
    description: Optional[str] = None
    holdings: List[HoldingCreate]


class PortfolioUpdate(BaseModel):
    """Schema for updating a portfolio"""
    name: Optional[str] = None
    description: Optional[str] = None
    holdings: Optional[List[HoldingCreate]] = None


class PortfolioResponse(BaseModel):
    """Schema for portfolio response"""
    id: int
    user_id: int
    name: str
    description: Optional[str]
    holdings: List[HoldingResponse]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PortfolioMetrics(BaseModel):
    """Schema for portfolio metrics"""
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    var_95: float
    cvar_95: float


class RiskMetrics(BaseModel):
    """Schema for risk metrics"""
    var_95: float
    var_99: float
    cvar_95: float
    cvar_99: float
    volatility: float
    max_drawdown: float
    correlation_matrix: Dict[str, Dict[str, float]]
