"""
Core Portfolio class for managing investment portfolios.
"""

from typing import Dict, List, Optional, Union
from datetime import datetime, date
import pandas as pd
import numpy as np
from pydantic import BaseModel, Field, field_validator, ConfigDict

from .asset import Asset


class Portfolio(BaseModel):
    """
    A comprehensive portfolio management class.
    
    This class represents an investment portfolio containing multiple assets
    with their respective weights and provides methods for analysis.
    
    Attributes:
        name: Name of the portfolio
        assets: Dictionary mapping asset symbols to Asset objects
        weights: Dictionary mapping asset symbols to their portfolio weights
        cash: Cash position in the portfolio
        base_currency: Base currency for the portfolio (default: USD)
        created_date: Date when portfolio was created
    """
    
    name: str = Field(..., description="Name of the portfolio")
    assets: Dict[str, Asset] = Field(default_factory=dict, description="Portfolio assets")
    weights: Dict[str, float] = Field(default_factory=dict, description="Asset weights")
    cash: float = Field(default=0.0, ge=0, description="Cash position")
    base_currency: str = Field(default="USD", description="Base currency")
    created_date: datetime = Field(default_factory=datetime.now)
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    @field_validator('weights')
    @classmethod
    def validate_weights(cls, v):
        """Ensure weights sum to 1 or less (allowing for cash)."""
        if v and abs(sum(v.values()) - 1.0) > 1e-6 and sum(v.values()) > 1.0:
            raise ValueError("Asset weights cannot sum to more than 1.0")
        return v
    
    def add_asset(self, symbol: str, asset: Asset, weight: float, price_data: Optional[pd.DataFrame] = None) -> None:
        """
        Add an asset to the portfolio.
        
        Args:
            symbol: Asset symbol/ticker
            asset: Asset object
            weight: Portfolio weight for this asset (0.0 to 1.0)
            price_data: Optional DataFrame containing price data for this asset
        
        Raises:
            ValueError: If weight is invalid or total weights exceed 1.0
        """
        if not 0 <= weight <= 1:
            raise ValueError("Weight must be between 0 and 1")
        
        # Get current weight sum excluding the symbol we're adding/updating
        current_weights = {k: v for k, v in self.weights.items() if k != symbol}
        current_weight_sum = sum(current_weights.values())
        
        if current_weight_sum + weight > 1.0 + 1e-6:  # Add small tolerance
            raise ValueError(
                f"Adding weight {weight} would exceed maximum weight of 1.0. "
                f"Current sum: {current_weight_sum}"
            )
        
        # Set price data if provided
        if price_data is not None:
            asset.set_price_data(price_data)
            
        self.assets[symbol] = asset
        self.weights[symbol] = weight
    
    def remove_asset(self, symbol: str) -> None:
        """Remove an asset from the portfolio."""
        if symbol in self.assets:
            del self.assets[symbol]
            del self.weights[symbol]
    
    def rebalance(self, new_weights: Dict[str, float]) -> None:
        """
        Rebalance portfolio with new weights.
        
        Args:
            new_weights: Dictionary mapping symbols to new weights
            
        Raises:
            ValueError: If weights are invalid or assets don't exist
        """
        # Validate that all symbols exist in portfolio
        for symbol in new_weights:
            if symbol not in self.assets:
                raise ValueError(f"Asset {symbol} not found in portfolio")
        
        # Validate weights
        if abs(sum(new_weights.values()) - 1.0) > 1e-6:
            raise ValueError("New weights must sum to 1.0")
        
        self.weights.update(new_weights)
    
    def get_total_value(self, prices: Optional[Dict[str, float]] = None) -> float:
        """
        Calculate total portfolio value.
        
        Args:
            prices: Optional dictionary of current prices. If None, uses last available price.
            
        Returns:
            Total portfolio value in base currency
        """
        total_value = self.cash
        
        for symbol, weight in self.weights.items():
            asset = self.assets[symbol]
            if prices and symbol in prices:
                price = prices[symbol]
            else:
                price = asset.get_current_price()
            
            if price is not None:
                # Assuming unit portfolio value of 1.0 for weight calculation
                total_value += weight * price
        
        return total_value
    
    def get_portfolio_returns(self, start_date: Optional[date] = None, 
                            end_date: Optional[date] = None) -> pd.Series:
        """
        Calculate portfolio returns over a period.
        
        Args:
            start_date: Start date for calculation
            end_date: End date for calculation
            
        Returns:
            Series of portfolio returns
            
        Raises:
            ValueError: If no assets have price data
        """
        if not self.assets:
            return pd.Series(dtype=float)
        
        # Check if we have price data for all assets
        missing_data = [symbol for symbol, asset in self.assets.items() 
                       if asset.price_data is None or asset.price_data.empty]
        
        if missing_data:
            raise ValueError(
                f"Missing price data for assets: {', '.join(missing_data)}. "
                "Please set price data using set_assets_price_data() before calculating returns."
            )
        
        # Get returns for each asset
        asset_returns = {}
        for symbol, asset in self.assets.items():
            try:
                returns = asset.get_returns(start_date, end_date)
                if not returns.empty:
                    asset_returns[symbol] = returns
            except Exception as e:
                raise ValueError(f"Error calculating returns for {symbol}: {str(e)}")
        
        if not asset_returns:
            raise ValueError("No valid returns data could be calculated. "
                           "Check if the date range contains valid price data.")
        
        # Combine into DataFrame
        try:
            returns_df = pd.DataFrame(asset_returns)
        except Exception as e:
            raise ValueError(f"Error combining asset returns: {str(e)}")
        
        # Calculate weighted portfolio returns
        try:
            portfolio_returns = pd.Series(0.0, index=returns_df.index)
            for symbol in returns_df.columns:
                if symbol in self.weights:
                    portfolio_returns += self.weights[symbol] * returns_df[symbol]
            return portfolio_returns
        except Exception as e:
            raise ValueError(f"Error calculating weighted returns: {str(e)}")
    
    def set_assets_price_data(self, price_data: Dict[str, pd.DataFrame]) -> None:
        """
        Set price data for all assets in the portfolio.
        
        Args:
            price_data: Dictionary mapping asset symbols to their price DataFrames.
                       The DataFrames must have a 'Close' column.
                       
        Raises:
            ValueError: If price data is missing for any asset in the portfolio
        """
        # First verify all assets have corresponding price data
        missing_symbols = [symbol for symbol in self.assets if symbol not in price_data]
        if missing_symbols:
            raise ValueError(f"Missing price data for assets: {', '.join(missing_symbols)}")
            
        # Set price data for each asset
        for symbol, data in price_data.items():
            if symbol in self.assets:
                try:
                    self.assets[symbol].set_price_data(data)
                except Exception as e:
                    raise ValueError(f"Error setting price data for {symbol}: {str(e)}")
        
        # Verify all assets now have price data
        missing_data = [symbol for symbol, asset in self.assets.items() 
                       if not hasattr(asset, 'price_data') or asset.price_data is None or asset.price_data.empty]
        
        if missing_data:
            raise ValueError(f"Failed to set price data for assets: {', '.join(missing_data)}")
    
    def ensure_price_data(self) -> bool:
        """
        Ensure all assets in the portfolio have price data.
        
        Returns:
            bool: True if all assets have price data, False otherwise
        """
        for asset in self.assets.values():
            if asset.price_data is None or asset.price_data.empty:
                return False
        return True
    
    def summary(self) -> Dict:
        """
        Generate portfolio summary.
        
        Returns:
            Dictionary containing portfolio summary statistics
        """
        return {
            "name": self.name,
            "num_assets": len(self.assets),
            "cash_position": self.cash,
            "base_currency": self.base_currency,
            "total_weight": sum(self.weights.values()),
            "created_date": self.created_date,
            "assets": list(self.assets.keys()),
            "weights": self.weights.copy(),
            "has_price_data": self.ensure_price_data(),
        }
    
    def __str__(self) -> str:
        """String representation of the portfolio."""
        return f"Portfolio(name='{self.name}', assets={len(self.assets)}, value={self.get_total_value():.2f})"
    
    def __repr__(self) -> str:
        """Detailed string representation."""
        assets_with_data = [
            f"{symbol}: {'✓' if hasattr(asset, 'price_data') and asset.price_data is not None and not asset.price_data.empty else '✗'}" 
            for symbol, asset in self.assets.items()
        ]
        return (
            f"Portfolio(name='{self.name}', assets={list(self.assets.keys())}, "
            f"weights={self.weights}, cash={self.cash}, "
            f"price_data_status={{ {' | '.join(assets_with_data)} }}"
        )
