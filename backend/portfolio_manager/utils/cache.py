"""
Caching utilities for portfolio management.

This module provides caching functionality to improve performance
when fetching market data and calculating analytics.
"""

import os
import pickle
import hashlib
from typing import Any, Optional, Dict, Union
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
from functools import wraps


class DataCache:
    """
    Simple file-based cache for market data and analytics results.
    
    This cache helps avoid repeated API calls and expensive calculations
    by storing results on disk with configurable expiration.
    """
    
    def __init__(self, cache_dir: Optional[Union[str, Path]] = None, 
                 default_ttl: int = 3600):
        """
        Initialize the cache.
        
        Args:
            cache_dir: Directory to store cache files (default: ~/.portfolio_manager_cache)
            default_ttl: Default time-to-live in seconds (default: 1 hour)
        """
        if cache_dir is None:
            cache_dir = Path.home() / '.portfolio_manager_cache'
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_ttl = default_ttl
    
    def _get_cache_key(self, key: str) -> str:
        """Generate a safe cache key by hashing the input."""
        return hashlib.md5(key.encode()).hexdigest()
    
    def _get_cache_path(self, cache_key: str) -> Path:
        """Get the full path for a cache file."""
        return self.cache_dir / f"{cache_key}.pkl"
    
    def _is_expired(self, filepath: Path, ttl: int) -> bool:
        """Check if a cache file has expired."""
        if not filepath.exists():
            return True
        
        file_age = datetime.now() - datetime.fromtimestamp(filepath.stat().st_mtime)
        return file_age.total_seconds() > ttl
    
    def get(self, key: str, ttl: Optional[int] = None) -> Any:
        """
        Retrieve an item from the cache.
        
        Args:
            key: Cache key
            ttl: Time-to-live in seconds (uses default if None)
            
        Returns:
            Cached value or None if not found/expired
        """
        ttl = ttl or self.default_ttl
        cache_key = self._get_cache_key(key)
        cache_path = self._get_cache_path(cache_key)
        
        if self._is_expired(cache_path, ttl):
            return None
        
        try:
            with open(cache_path, 'rb') as f:
                return pickle.load(f)
        except (FileNotFoundError, pickle.PickleError, EOFError):
            return None
    
    def set(self, key: str, value: Any) -> None:
        """
        Store an item in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        cache_key = self._get_cache_key(key)
        cache_path = self._get_cache_path(cache_key)
        
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(value, f)
        except pickle.PickleError:
            # If we can't pickle it, just skip caching
            pass
    
    def clear(self) -> int:
        """
        Clear all items from the cache.
        
        Returns:
            Number of files deleted
        """
        deleted = 0
        for cache_file in self.cache_dir.glob("*.pkl"):
            try:
                cache_file.unlink()
                deleted += 1
            except FileNotFoundError:
                pass
        
        return deleted


# Global cache instance
_global_cache = DataCache()


def cached(ttl: int = 3600, key_prefix: str = ""):
    """
    Decorator to cache function results.
    
    Args:
        ttl: Time-to-live in seconds
        key_prefix: Prefix to add to cache keys
        
    Example:
        @cached(ttl=1800, key_prefix="price_data")
        def get_stock_price(symbol, date):
            # Expensive API call
            return fetch_price_from_api(symbol, date)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            key_parts = [key_prefix, func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = "|".join(filter(None, key_parts))
            
            # Try to get from cache
            result = _global_cache.get(cache_key, ttl)
            if result is not None:
                return result
            
            # Not in cache, compute result
            result = func(*args, **kwargs)
            
            # Store in cache
            _global_cache.set(cache_key, result)
            
            return result
        
        return wrapper
    return decorator


def cached_analytics(analytics_type: str, ttl: int = 1800):
    """
    Decorator for caching analytics methods.
    
    Args:
        analytics_type: Type of analytics ('performance', 'risk', etc.)
        ttl: Time-to-live in seconds
        
    Example:
        class PerformanceAnalytics:
            @cached_analytics('performance', ttl=3600)
            def sharpe_ratio(self, risk_free_rate=0.02):
                # Expensive calculation
                return self._calculate_sharpe_ratio(risk_free_rate)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # For now, just call the function directly
            # Full analytics caching can be implemented later
            return func(self, *args, **kwargs)
        
        return wrapper
    return decorator


def cached_price_fetcher(fetch_func):
    """
    Wrapper to add caching to price fetching functions.
    
    Args:
        fetch_func: Function that fetches price data
        
    Returns:
        Wrapped function with caching
    """
    @wraps(fetch_func)
    def wrapper(self, symbol, start_date=None, end_date=None, interval='1d'):
        # Create cache key
        cache_key = f"price_data|{symbol}|{start_date}|{end_date}|{interval}"
        
        # Try cache first
        cached_data = _global_cache.get(cache_key, 3600)  # 1 hour TTL
        if cached_data is not None:
            return cached_data
        
        # Fetch from source
        data = fetch_func(self, symbol, start_date, end_date, interval)
        
        # Cache the result
        if data is not None and not data.empty:
            _global_cache.set(cache_key, data)
        
        return data
    
    return wrapper


# Utility functions for cache management
def get_cache_stats() -> Dict[str, Union[int, str]]:
    """Get statistics about the global cache."""
    cache_files = list(_global_cache.cache_dir.glob("*.pkl"))
    total_size = sum(f.stat().st_size for f in cache_files)
    
    # Convert to human readable
    def human_size(bytes_size):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_size < 1024:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024
        return f"{bytes_size:.1f} TB"
    
    return {
        "num_files": len(cache_files),
        "total_size_bytes": total_size,
        "total_size_human": human_size(total_size),
        "cache_dir": str(_global_cache.cache_dir)
    }


def clear_cache() -> int:
    """Clear all cached data."""
    return _global_cache.clear()


def clear_expired_cache(max_age_days: int = 7) -> int:
    """
    Clear cache entries older than specified age.
    
    Args:
        max_age_days: Maximum age in days
        
    Returns:
        Number of files deleted
    """
    cutoff_time = datetime.now() - timedelta(days=max_age_days)
    deleted = 0
    
    for cache_file in _global_cache.cache_dir.glob("*.pkl"):
        try:
            file_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
            if file_time < cutoff_time:
                cache_file.unlink()
                deleted += 1
        except (FileNotFoundError, OSError):
            pass
    
    return deleted
