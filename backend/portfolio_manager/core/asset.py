"""
Asset class for representing individual financial instruments.
"""

from typing import Dict, List, Optional, Union
from datetime import datetime, date
import pandas as pd
import numpy as np
from pydantic import BaseModel, Field, field_validator, ConfigDict
from enum import Enum


class AssetType(str, Enum):
    """Enumeration of supported asset types."""
    STOCK = "stock"
    BOND = "bond"
    ETF = "etf"
    MUTUAL_FUND = "mutual_fund"
    COMMODITY = "commodity"
    CRYPTOCURRENCY = "cryptocurrency"
    CASH = "cash"
    OTHER = "other"


class Asset(BaseModel):
    """
    Represents a financial asset/instrument.
    
    This class encapsulates information about a financial asset including
    its identifying information, price history, and metadata.
    
    Attributes:
        symbol: Asset symbol/ticker
        name: Full name of the asset
        asset_type: Type of asset (stock, bond, etc.)
        currency: Trading currency
        exchange: Exchange where asset is traded
        price_data: Historical price data
        metadata: Additional asset information
    """
    
    symbol: str = Field(..., description="Asset symbol/ticker")
    name: str = Field(..., description="Full asset name")
    asset_type: AssetType = Field(default=AssetType.STOCK, description="Asset type")
    currency: str = Field(default="USD", description="Trading currency")
    exchange: Optional[str] = Field(None, description="Trading exchange")
    price_data: Optional[pd.DataFrame] = Field(None, description="Historical price data")
    metadata: Dict = Field(default_factory=dict, description="Additional metadata")
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    @field_validator('symbol')
    @classmethod
    def symbol_must_not_be_empty(cls, v):
        """Ensure symbol is not empty."""
        if not v or not v.strip():
            raise ValueError('Symbol cannot be empty')
        return v.strip().upper()
    
    def set_price_data(self, data: pd.DataFrame) -> None:
        """
        Set historical price data for the asset.
        
        Args:
            data: DataFrame with price data (must have 'Close' column)
            
        Raises:
            ValueError: If data format is invalid
        """
        required_columns = ['Close']
        if not all(col in data.columns for col in required_columns):
            raise ValueError(f"Price data must contain columns: {required_columns}")
        
        self.price_data = data.copy()
    
    def get_current_price(self) -> Optional[float]:
        """
        Get the most recent price.
        
        Returns:
            Most recent closing price or None if no data available
        """
        if self.price_data is None or self.price_data.empty:
            return None
        
        return float(self.price_data['Close'].iloc[-1])
    
    def get_price_at_date(self, target_date: Union[str, date, datetime]) -> Optional[float]:
        """
        Get price at specific date.
        
        Args:
            target_date: Date to get price for
            
        Returns:
            Price at specified date or None if not available
        """
        if self.price_data is None or self.price_data.empty:
            return None
        
        if isinstance(target_date, str):
            target_date = pd.to_datetime(target_date).date()
        elif isinstance(target_date, datetime):
            target_date = target_date.date()
        
        # Find the closest date
        price_dates = pd.to_datetime(self.price_data.index).date
        closest_idx = np.argmin(np.abs([(d - target_date).days for d in price_dates]))
        
        return float(self.price_data['Close'].iloc[closest_idx])
    
    def get_returns(self, start_date: Optional[date] = None, 
                   end_date: Optional[date] = None, 
                   frequency: str = 'daily') -> pd.Series:
        """
        Calculate returns for the asset.
        
        Args:
            start_date: Start date for returns calculation
            end_date: End date for returns calculation  
            frequency: Return frequency ('daily', 'weekly', 'monthly')
            
        Returns:
            Series of returns
        """
        if self.price_data is None or self.price_data.empty:
            return pd.Series(dtype=float)
        
        prices = self.price_data['Close'].copy()
        
        # Filter by date range if provided
        if start_date:
            prices = prices[prices.index >= pd.to_datetime(start_date)]
        if end_date:
            prices = prices[prices.index <= pd.to_datetime(end_date)]
        
        if len(prices) < 2:
            return pd.Series(dtype=float)
        
        # Calculate returns
        returns = prices.pct_change().dropna()
        
        # Resample if needed
        if frequency == 'weekly':
            returns = returns.resample('W').apply(lambda x: (1 + x).prod() - 1)
        elif frequency == 'monthly':
            returns = returns.resample('M').apply(lambda x: (1 + x).prod() - 1)
        
        return returns
    
    def get_volatility(self, window: int = 252, 
                      start_date: Optional[date] = None,
                      end_date: Optional[date] = None) -> float:
        """
        Calculate asset volatility (annualized).
        
        Args:
            window: Number of periods for volatility calculation
            start_date: Start date for calculation
            end_date: End date for calculation
            
        Returns:
            Annualized volatility
        """
        returns = self.get_returns(start_date, end_date)
        if returns.empty:
            return 0.0
        
        return float(returns.std() * np.sqrt(window))
    
    def get_sharpe_ratio(self, risk_free_rate: float = 0.02,
                        start_date: Optional[date] = None,
                        end_date: Optional[date] = None) -> float:
        """
        Calculate Sharpe ratio.
        
        Args:
            risk_free_rate: Annual risk-free rate
            start_date: Start date for calculation
            end_date: End date for calculation
            
        Returns:
            Sharpe ratio
        """
        returns = self.get_returns(start_date, end_date)
        if returns.empty:
            return 0.0
        
        excess_returns = returns.mean() * 252 - risk_free_rate
        volatility = self.get_volatility(start_date=start_date, end_date=end_date)
        
        if volatility == 0:
            return 0.0
        
        return excess_returns / volatility
    
    def summary(self) -> Dict:
        """
        Generate asset summary.
        
        Returns:
            Dictionary with asset summary information
        """
        summary_dict = {
            "symbol": self.symbol,
            "name": self.name,
            "asset_type": self.asset_type,
            "currency": self.currency,
            "exchange": self.exchange,
            "current_price": self.get_current_price(),
            "has_price_data": self.price_data is not None and not self.price_data.empty,
        }
        
        if self.price_data is not None and not self.price_data.empty:
            summary_dict.update({
                "data_start": self.price_data.index[0],
                "data_end": self.price_data.index[-1],
                "num_observations": len(self.price_data),
                "volatility": self.get_volatility(),
                "sharpe_ratio": self.get_sharpe_ratio(),
            })
        
        return summary_dict
    
    def __str__(self) -> str:
        """String representation."""
        return f"Asset(symbol='{self.symbol}', name='{self.name}', type={self.asset_type})"
    
    def __repr__(self) -> str:
        """Detailed representation."""
        return (f"Asset(symbol='{self.symbol}', name='{self.name}', "
                f"type={self.asset_type}, currency='{self.currency}')")
