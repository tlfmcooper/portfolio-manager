"""
Finance service for fetching asset data from Yahoo Finance.
"""
import yfinance as yf
import logging
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class FinanceService:
    """Service for fetching financial data from Yahoo Finance."""
    
    @staticmethod
    async def get_asset_info(ticker: str) -> Optional[Dict[str, Any]]:
        """
        Fetch comprehensive asset information from Yahoo Finance.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Dictionary with asset information or None if not found
        """
        try:
            # Create yfinance ticker object
            stock = yf.Ticker(ticker.upper())
            
            # Get basic info
            info = stock.info
            
            if not info or 'symbol' not in info:
                logger.warning(f"No data found for ticker: {ticker}")
                return None
            
            # Extract relevant information
            asset_data = {
                'ticker': ticker.upper(),
                'name': info.get('longName') or info.get('shortName'),
                'asset_type': _determine_asset_type(info),
                'sector': info.get('sector'),
                'industry': info.get('industry'),
                'description': info.get('longBusinessSummary'),
                'currency': info.get('currency', 'USD'),
                'exchange': info.get('exchange'),
                'current_price': info.get('currentPrice') or info.get('regularMarketPrice'),
                'market_cap': info.get('marketCap'),
                'dividend_yield': info.get('dividendYield'),
                'pe_ratio': info.get('trailingPE') or info.get('forwardPE'),
                'beta': info.get('beta'),
                'last_price_update': datetime.utcnow()
            }
            
            # Clean up None values and convert to appropriate types
            cleaned_data = {}
            for key, value in asset_data.items():
                if value is not None:
                    if key in ['current_price', 'market_cap', 'dividend_yield', 'pe_ratio', 'beta']:
                        try:
                            cleaned_data[key] = float(value)
                        except (ValueError, TypeError):
                            pass
                    else:
                        cleaned_data[key] = value
                        
            logger.info(f"Successfully fetched data for {ticker}")
            return cleaned_data
            
        except Exception as e:
            logger.error(f"Error fetching data for {ticker}: {str(e)}")
            return None
    
    @staticmethod
    async def get_current_price(ticker: str) -> Optional[float]:
        """
        Get just the current price for a ticker.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Current price or None if not found
        """
        try:
            stock = yf.Ticker(ticker.upper())
            info = stock.info
            
            price = info.get('currentPrice') or info.get('regularMarketPrice')
            return float(price) if price else None
            
        except Exception as e:
            logger.error(f"Error fetching price for {ticker}: {str(e)}")
            return None


def _determine_asset_type(info: Dict[str, Any]) -> str:
    """
    Determine asset type based on Yahoo Finance info.
    
    Args:
        info: Yahoo Finance info dictionary
        
    Returns:
        Asset type string
    """
    quote_type = info.get('quoteType', '').lower()
    
    if quote_type == 'equity':
        return 'stock'
    elif quote_type == 'etf':
        return 'etf'
    elif quote_type == 'mutualfund':
        return 'mutual_fund'
    elif quote_type == 'cryptocurrency':
        return 'crypto'
    elif 'bond' in quote_type:
        return 'bond'
    else:
        return 'stock'  # Default to stock
