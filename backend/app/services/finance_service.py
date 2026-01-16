"""
Finance service for fetching asset data from Yahoo Finance and other sources.
"""
import yfinance as yf
import logging
import requests
import ast
import re
import time
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Session with connection pooling for better performance
session = requests.Session()
adapter = requests.adapters.HTTPAdapter(
    pool_connections=10,
    pool_maxsize=20,
    max_retries=0  # We'll handle retries manually
)
session.mount('https://', adapter)
session.mount('http://', adapter)


class FinanceService:
    """Service for fetching financial data from Yahoo Finance and other sources."""

    @staticmethod
    async def get_asset_info(ticker: str, asset_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Fetch comprehensive asset information based on asset type.

        Args:
            ticker: Asset ticker/symbol
            asset_type: Type of asset (stock, mutual_fund, crypto) - if None, will auto-detect

        Returns:
            Dictionary with asset information or None if not found
        """
        # Route to appropriate fetcher based on asset_type
        if asset_type == 'mutual_fund':
            return await FinanceService._get_mutual_fund_info(ticker)
        elif asset_type == 'crypto':
            return await FinanceService._get_crypto_info(ticker)
        else:
            # Default to stock/ETF via Yahoo Finance
            return await FinanceService._get_stock_info(ticker, asset_type)

    @staticmethod
    async def _get_stock_info(ticker: str, asset_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Fetch stock/ETF information from Yahoo Finance."""
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
                'asset_type': asset_type or _determine_asset_type(info),
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

            logger.info(f"Successfully fetched stock data for {ticker}")
            return cleaned_data

        except Exception as e:
            logger.error(f"Error fetching stock data for {ticker}: {str(e)}")
            return None

    @staticmethod
    async def _get_mutual_fund_info(ticker: str) -> Optional[Dict[str, Any]]:
        """Fetch mutual fund information from Barchart with retry logic."""
        max_retries = 3
        base_timeout = 20  # Increased from 10 to 20 seconds

        for attempt in range(max_retries):
            try:
                headers = {
                    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1"
                }
                regex = r"{.*}"

                URL = f"https://www.barchart.com/etfs-funds/quotes/{ticker}"

                # Calculate timeout with exponential backoff for retries
                timeout = base_timeout * (1.5 ** attempt)

                if attempt > 0:
                    wait_time = 2 ** attempt  # Exponential backoff: 2, 4, 8 seconds
                    logger.info(f"Retry attempt {attempt + 1}/{max_retries} for {ticker} after {wait_time}s delay")
                    time.sleep(wait_time)

                response = session.get(URL, headers=headers, timeout=timeout)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, "html.parser")
                mf_data_bs_element = soup.find_all("div", class_="bc-quote-overview row")

                if not mf_data_bs_element:
                    logger.warning(f"No mutual fund data found for ticker: {ticker}")
                    return None

                mf_data_bs_str = str(mf_data_bs_element[0])
                mf_data_list = re.findall(regex, mf_data_bs_str)

                if not mf_data_list:
                    logger.warning(f"Could not parse mutual fund data for ticker: {ticker}")
                    return None

                mf_data_json = mf_data_list[0]
                parsed_data = ast.literal_eval(mf_data_json)

                # Extract price information
                raw_data = parsed_data[2].get('raw', {})
                last_price = raw_data.get('lastPrice')
                previous_price = raw_data.get('previousPrice')

                # Calculate day change percentage for display purposes
                change_percent = 0.0
                change = 0.0
                if last_price and previous_price:
                    try:
                        last_price_float = float(last_price)
                        previous_price_float = float(previous_price)
                        change = last_price_float - previous_price_float
                        change_percent = (change / previous_price_float) * 100
                    except (ValueError, ZeroDivisionError):
                        pass

                # Asset data contains fields that map to Asset model + display fields
                asset_data = {
                    'ticker': ticker.upper(),
                    'name': ticker,  # Could be enhanced with more scraping
                    'asset_type': 'mutual_fund',
                    'currency': 'USD',
                    'current_price': float(last_price) if last_price else None,
                    'last_price_update': datetime.utcnow(),
                    # Additional fields for display (not stored in Asset model, filtered out before saving)
                    'change_percent': change_percent,
                    'change': change,
                    'previous_close': float(previous_price) if previous_price else None
                }

                logger.info(f"Successfully fetched mutual fund data for {ticker}: price={last_price}, prev={previous_price}, change={change_percent:.2f}%")
                return asset_data

            except requests.exceptions.Timeout as e:
                logger.warning(f"Timeout on attempt {attempt + 1}/{max_retries} for {ticker}: {str(e)}")
                if attempt == max_retries - 1:
                    logger.error(f"Failed to fetch mutual fund data for {ticker} after {max_retries} attempts")
                    return None
                # Continue to next retry attempt

            except requests.exceptions.RequestException as e:
                logger.error(f"Request error fetching mutual fund data for {ticker}: {str(e)}")
                if attempt == max_retries - 1:
                    return None
                # Continue to next retry attempt

            except Exception as e:
                logger.error(f"Error fetching mutual fund data for {ticker}: {str(e)}")
                return None

        return None

    @staticmethod
    async def _get_crypto_info(ticker: str) -> Optional[Dict[str, Any]]:
        """Fetch cryptocurrency information from Yahoo Finance or CoinGecko."""
        try:
            # Try Yahoo Finance first (e.g., BTC-USD, ETH-USD)
            crypto_ticker = ticker if '-USD' in ticker.upper() else f"{ticker.upper()}-USD"

            stock = yf.Ticker(crypto_ticker)
            info = stock.info

            if not info or 'symbol' not in info:
                logger.warning(f"No crypto data found for ticker: {ticker}")
                return None

            asset_data = {
                'ticker': ticker.upper(),
                'name': info.get('longName') or info.get('shortName') or ticker.upper(),
                'asset_type': 'crypto',
                'description': info.get('description'),
                'currency': 'USD',
                'exchange': info.get('exchange'),
                'current_price': info.get('currentPrice') or info.get('regularMarketPrice'),
                'market_cap': info.get('marketCap'),
                'last_price_update': datetime.utcnow()
            }

            # Clean up None values
            cleaned_data = {}
            for key, value in asset_data.items():
                if value is not None:
                    if key in ['current_price', 'market_cap']:
                        try:
                            cleaned_data[key] = float(value)
                        except (ValueError, TypeError):
                            pass
                    else:
                        cleaned_data[key] = value

            logger.info(f"Successfully fetched crypto data for {ticker}")
            return cleaned_data

        except Exception as e:
            logger.error(f"Error fetching crypto data for {ticker}: {str(e)}")
            return None
    
    @staticmethod
    async def get_current_price(ticker: str, asset_type: Optional[str] = None) -> Optional[float]:
        """
        Get just the current price for a ticker based on asset type.

        Args:
            ticker: Asset ticker/symbol
            asset_type: Type of asset (stock, mutual_fund, crypto)

        Returns:
            Current price or None if not found
        """
        try:
            # Get full asset info and extract price
            asset_info = await FinanceService.get_asset_info(ticker, asset_type)
            if asset_info and 'current_price' in asset_info:
                return asset_info['current_price']
            return None

        except Exception as e:
            logger.error(f"Error fetching price for {ticker}: {str(e)}")
            return None

    @staticmethod
    async def get_ohlc_data(ticker: str) -> Optional[Dict[str, Any]]:
        """
        Get OHLC (Open, High, Low, Close) data for a stock from Yahoo Finance.
        Uses the most recent trading day data.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Dictionary with OHLC data and change percentage, or None if not found
        """
        try:
            stock = yf.Ticker(ticker)

            # Get last 2 days of history to ensure we have data even if market is closed
            hist = stock.history(period='2d')

            if hist.empty:
                logger.warning(f"No OHLC data found for ticker: {ticker}")
                return None

            # Get the most recent trading day
            latest = hist.iloc[-1]
            close_price = float(latest['Close'])
            open_price = float(latest['Open'])
            high_price = float(latest['High'])
            low_price = float(latest['Low'])

            # Get previous day's close for change calculation
            previous_close = None
            change_percent = None

            if len(hist) >= 2:
                previous = hist.iloc[-2]
                previous_close = float(previous['Close'])
                change_percent = ((close_price - previous_close) / previous_close) * 100
            else:
                # If only one day available, calculate change from open to close
                change_percent = ((close_price - open_price) / open_price) * 100

            ohlc_data = {
                'ticker': ticker.upper(),
                'current_price': close_price,
                'open': open_price,
                'high': high_price,
                'low': low_price,
                'close': close_price,
                'previous_close': previous_close,
                'change_percent': change_percent,
                'change': close_price - (previous_close if previous_close else open_price),
                'last_updated': datetime.utcnow()
            }

            logger.info(f"Successfully fetched OHLC data for {ticker}: close={close_price}, change%={change_percent}")
            return ohlc_data

        except Exception as e:
            logger.error(f"Error fetching OHLC data for {ticker}: {str(e)}")
            return None

    @staticmethod
    async def calculate_ticker_performance(
        ticker: str, 
        asset_type: Optional[str] = None,
        periods: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Calculate performance metrics for a ticker over various time periods.
        
        Uses yfinance for stocks/ETFs/crypto. For mutual funds, historical data
        is not available via Barchart, so only cost-basis returns can be calculated.
        
        Args:
            ticker: Asset ticker symbol
            asset_type: Type of asset (stock, mutual_fund, crypto) - affects data source
            periods: List of periods to calculate (ytd, 1m, 3m, 1y). Defaults to all.
            
        Returns:
            Dictionary with performance metrics for each period
        """
        if periods is None:
            periods = ["ytd", "1m", "3m", "1y"]
        
        result = {
            "ticker": ticker.upper(),
            "asset_type": asset_type,
            "ytd_return": None,
            "one_month_return": None,
            "three_month_return": None,
            "one_year_return": None,
            "current_price": None,
            "historical_data_available": True,
            "data_source": "yfinance",
            "last_updated": datetime.utcnow()
        }
        
        # Mutual funds don't have historical data via Barchart
        if asset_type == "mutual_fund":
            result["historical_data_available"] = False
            result["data_source"] = "barchart"
            
            # Try to get current price from Barchart
            try:
                mf_info = await FinanceService._get_mutual_fund_info(ticker)
                if mf_info and "current_price" in mf_info:
                    result["current_price"] = mf_info["current_price"]
            except Exception as e:
                logger.warning(f"Failed to get mutual fund price for {ticker}: {e}")
            
            return result
        
        try:
            # Use yfinance for stocks, ETFs, and crypto
            stock_ticker = ticker
            if asset_type == "crypto" and "-USD" not in ticker.upper():
                stock_ticker = f"{ticker.upper()}-USD"
            
            stock = yf.Ticker(stock_ticker)
            
            # Get current price
            try:
                info = stock.info
                result["current_price"] = info.get("currentPrice") or info.get("regularMarketPrice")
            except Exception:
                pass
            
            now = datetime.now()
            
            # Calculate YTD return
            if "ytd" in periods:
                try:
                    # Get data from start of current year
                    year_start = datetime(now.year, 1, 1)
                    hist = stock.history(start=year_start, end=now)
                    
                    if not hist.empty and len(hist) >= 2:
                        start_price = float(hist.iloc[0]['Close'])
                        end_price = float(hist.iloc[-1]['Close'])
                        result["ytd_return"] = round(((end_price - start_price) / start_price) * 100, 2)
                        result["current_price"] = end_price
                except Exception as e:
                    logger.warning(f"Failed to calculate YTD for {ticker}: {e}")
            
            # Calculate 1-month return
            if "1m" in periods:
                try:
                    hist = stock.history(period="1mo")
                    if not hist.empty and len(hist) >= 2:
                        start_price = float(hist.iloc[0]['Close'])
                        end_price = float(hist.iloc[-1]['Close'])
                        result["one_month_return"] = round(((end_price - start_price) / start_price) * 100, 2)
                except Exception as e:
                    logger.warning(f"Failed to calculate 1M for {ticker}: {e}")
            
            # Calculate 3-month return
            if "3m" in periods:
                try:
                    hist = stock.history(period="3mo")
                    if not hist.empty and len(hist) >= 2:
                        start_price = float(hist.iloc[0]['Close'])
                        end_price = float(hist.iloc[-1]['Close'])
                        result["three_month_return"] = round(((end_price - start_price) / start_price) * 100, 2)
                except Exception as e:
                    logger.warning(f"Failed to calculate 3M for {ticker}: {e}")
            
            # Calculate 1-year return
            if "1y" in periods:
                try:
                    hist = stock.history(period="1y")
                    if not hist.empty and len(hist) >= 2:
                        start_price = float(hist.iloc[0]['Close'])
                        end_price = float(hist.iloc[-1]['Close'])
                        result["one_year_return"] = round(((end_price - start_price) / start_price) * 100, 2)
                except Exception as e:
                    logger.warning(f"Failed to calculate 1Y for {ticker}: {e}")
            
        except Exception as e:
            logger.error(f"Error calculating performance for {ticker}: {e}")
            result["historical_data_available"] = False
        
        return result


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
