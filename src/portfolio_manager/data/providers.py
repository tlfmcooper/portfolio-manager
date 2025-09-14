"""
Data providers for fetching financial market data.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union
from datetime import datetime, date, timedelta
import pandas as pd
import numpy as np
import yfinance as yf
import requests
from pydantic import BaseModel, Field

from ..core.asset import Asset, AssetType
from ..utils.cache import cached_price_fetcher


class DataProvider(ABC):
    """
    Abstract base class for data providers.
    
    Defines the interface that all data providers must implement.
    """
    
    @abstractmethod
    def get_price_data(self, symbol: str, 
                      start_date: Optional[date] = None,
                      end_date: Optional[date] = None,
                      interval: str = '1d') -> pd.DataFrame:
        """
        Get historical price data for a symbol.
        
        Args:
            symbol: Asset symbol/ticker
            start_date: Start date for data
            end_date: End date for data
            interval: Data interval ('1d', '1wk', '1mo', etc.)
            
        Returns:
            DataFrame with OHLCV data
        """
        pass
    
    @abstractmethod
    def get_asset_info(self, symbol: str) -> Dict:
        """
        Get asset information/metadata.
        
        Args:
            symbol: Asset symbol/ticker
            
        Returns:
            Dictionary with asset information
        """
        pass


class YFinanceProvider(DataProvider):
    """
    Yahoo Finance data provider using yfinance library.
    
    Provides access to Yahoo Finance data for stocks, ETFs, and other instruments.
    """
    
    def __init__(self, session: Optional[requests.Session] = None):
        """
        Initialize YFinance provider.
        
        Args:
            session: Optional requests session (deprecated - YF handles sessions internally)
        """
        # Let YFinance handle its own session management
        self.session = None
    
    @cached_price_fetcher
    def get_price_data(self, symbol: str, 
                      start_date: Optional[date] = None,
                      end_date: Optional[date] = None,
                      interval: str = '1d') -> pd.DataFrame:
        """
        Get historical price data from Yahoo Finance with caching.
        
        Args:
            symbol: Asset symbol/ticker
            start_date: Start date for data
            end_date: End date for data
            interval: Data interval
            
        Returns:
            DataFrame with OHLCV data
        """
        try:
            ticker = yf.Ticker(symbol)  # Let YF handle its own session
            
            # Set default dates if not provided
            if end_date is None:
                end_date = date.today()
            if start_date is None:
                start_date = end_date - timedelta(days=365)
            
            # Download data
            data = ticker.history(
                start=start_date,
                end=end_date,
                interval=interval,
                auto_adjust=True,
                prepost=True
            )
            
            if data.empty:
                raise ValueError(f"No data found for symbol {symbol}")
            
            # Ensure required columns exist
            required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            for col in required_columns:
                if col not in data.columns:
                    data[col] = np.nan
            
            return data[required_columns]
            
        except Exception as e:
            raise ValueError(f"Failed to fetch data for {symbol}: {str(e)}")
    
    def get_asset_info(self, symbol: str) -> Dict:
        """
        Get asset information from Yahoo Finance.
        
        Args:
            symbol: Asset symbol/ticker
            
        Returns:
            Dictionary with asset information
        """
        try:
            ticker = yf.Ticker(symbol)  # Let YF handle its own session
            info = ticker.info
            
            # Extract relevant information
            asset_info = {
                'symbol': symbol.upper(),
                'name': info.get('longName', info.get('shortName', symbol)),
                'currency': info.get('currency', 'USD'),
                'exchange': info.get('exchange', ''),
                'sector': info.get('sector', ''),
                'industry': info.get('industry', ''),
                'market_cap': info.get('marketCap'),
                'beta': info.get('beta'),
                'pe_ratio': info.get('trailingPE'),
                'dividend_yield': info.get('dividendYield'),
                'website': info.get('website', ''),
                'description': info.get('longBusinessSummary', ''),
                'asset_type': self._determine_asset_type(info),
                'last_updated': datetime.now()
            }
            
            return asset_info
            
        except Exception as e:
            raise ValueError(f"Failed to get info for {symbol}: {str(e)}")
    
    def _determine_asset_type(self, info: Dict) -> AssetType:
        """
        Determine asset type from Yahoo Finance info.
        
        Args:
            info: Yahoo Finance info dictionary
            
        Returns:
            AssetType enum value
        """
        quote_type = info.get('quoteType', '').lower()
        
        if quote_type == 'equity':
            return AssetType.STOCK
        elif quote_type == 'etf':
            return AssetType.ETF
        elif quote_type == 'mutualfund':
            return AssetType.MUTUAL_FUND
        elif quote_type == 'cryptocurrency':
            return AssetType.CRYPTOCURRENCY
        else:
            return AssetType.OTHER
    
    def create_asset(self, symbol: str, 
                    start_date: Optional[date] = None,
                    end_date: Optional[date] = None) -> Asset:
        """
        Create an Asset object with data from Yahoo Finance.
        
        Args:
            symbol: Asset symbol/ticker
            start_date: Start date for historical data
            end_date: End date for historical data
            
        Returns:
            Asset object with price data
        """
        # Get asset information
        info = self.get_asset_info(symbol)
        
        # Get price data
        price_data = self.get_price_data(symbol, start_date, end_date)
        
        # Create Asset object
        asset = Asset(
            symbol=info['symbol'],
            name=info['name'],
            asset_type=info['asset_type'],
            currency=info['currency'],
            exchange=info['exchange'],
            metadata=info
        )
        
        # Set price data
        asset.set_price_data(price_data)
        
        return asset
    
    def get_multiple_assets(self, symbols: List[str],
                           start_date: Optional[date] = None,
                           end_date: Optional[date] = None) -> List[Asset]:
        """
        Create multiple Asset objects efficiently.
        
        Args:
            symbols: List of asset symbols
            start_date: Start date for historical data
            end_date: End date for historical data
            
        Returns:
            List of Asset objects
        """
        assets = []
        
        for symbol in symbols:
            try:
                asset = self.create_asset(symbol, start_date, end_date)
                assets.append(asset)
            except Exception as e:
                print(f"Warning: Failed to create asset for {symbol}: {str(e)}")
                continue
        
        return assets
