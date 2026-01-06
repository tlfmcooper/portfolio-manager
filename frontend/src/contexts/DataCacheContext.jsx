/**
 * DataCacheContext - In-memory data caching for the current session
 * 
 * Provides centralized caching for frequently accessed data like portfolio
 * metrics, holdings, and allocations. Reduces redundant API calls when
 * navigating between pages.
 */

import React, { createContext, useContext, useState, useCallback, useRef, useEffect } from 'react';

const DataCacheContext = createContext(null);

// Cache expiry times in milliseconds
const CACHE_TTL = {
  PORTFOLIO_METRICS: 2 * 60 * 1000, // 2 minutes
  HOLDINGS: 1 * 60 * 1000,          // 1 minute
  ALLOCATION: 2 * 60 * 1000,        // 2 minutes
  DASHBOARD: 1 * 60 * 1000,         // 1 minute
  MARKET_DATA: 30 * 1000,           // 30 seconds
};

export const DataCacheProvider = ({ children }) => {
  const [cache, setCache] = useState({});
  const pendingRequests = useRef({});

  // Clear cache on logout
  useEffect(() => {
    const handleLogout = () => {
      console.log('[DataCache] Clearing cache on logout');
      setCache({});
      pendingRequests.current = {};
    };

    const handleSessionExpired = () => {
      console.log('[DataCache] Clearing cache on session expiry');
      setCache({});
      pendingRequests.current = {};
    };

    window.addEventListener('auth:logout', handleLogout);
    window.addEventListener('auth:sessionExpired', handleSessionExpired);
    
    return () => {
      window.removeEventListener('auth:logout', handleLogout);
      window.removeEventListener('auth:sessionExpired', handleSessionExpired);
    };
  }, []);

  /**
   * Get a cache key with currency
   */
  const getCacheKey = useCallback((key, currency = null) => {
    return currency ? `${key}_${currency}` : key;
  }, []);

  /**
   * Check if a cache entry is still valid
   */
  const isCacheValid = useCallback((entry) => {
    if (!entry) return false;
    const now = Date.now();
    return now - entry.timestamp < entry.ttl;
  }, []);

  /**
   * Get data from cache
   */
  const getFromCache = useCallback((key, currency = null) => {
    const cacheKey = getCacheKey(key, currency);
    const entry = cache[cacheKey];
    
    if (isCacheValid(entry)) {
      console.log(`[DataCache] Cache hit for ${cacheKey}`);
      return entry.data;
    }
    
    console.log(`[DataCache] Cache miss for ${cacheKey}`);
    return null;
  }, [cache, getCacheKey, isCacheValid]);

  /**
   * Set data in cache
   */
  const setInCache = useCallback((key, data, ttl, currency = null) => {
    const cacheKey = getCacheKey(key, currency);
    console.log(`[DataCache] Caching ${cacheKey} (TTL: ${ttl / 1000}s)`);
    
    setCache(prev => ({
      ...prev,
      [cacheKey]: {
        data,
        timestamp: Date.now(),
        ttl,
      }
    }));
  }, [getCacheKey]);

  /**
   * Fetch with cache - prevents duplicate in-flight requests
   * @param {string} key - Cache key
   * @param {Function} fetchFn - Async function to fetch data
   * @param {number} ttl - Time to live in ms
   * @param {string} currency - Optional currency for cache key
   */
  const fetchWithCache = useCallback(async (key, fetchFn, ttl, currency = null) => {
    const cacheKey = getCacheKey(key, currency);
    
    // Check cache first
    const cached = getFromCache(key, currency);
    if (cached) {
      return cached;
    }

    // Check if there's already a pending request
    if (pendingRequests.current[cacheKey]) {
      console.log(`[DataCache] Deduplicating request for ${cacheKey}`);
      return pendingRequests.current[cacheKey];
    }

    // Make the request and store the promise
    const requestPromise = (async () => {
      try {
        const data = await fetchFn();
        setInCache(key, data, ttl, currency);
        return data;
      } finally {
        // Clean up pending request
        delete pendingRequests.current[cacheKey];
      }
    })();

    pendingRequests.current[cacheKey] = requestPromise;
    return requestPromise;
  }, [getCacheKey, getFromCache, setInCache]);

  /**
   * Invalidate specific cache entries
   */
  const invalidateCache = useCallback((keys) => {
    const keysToInvalidate = Array.isArray(keys) ? keys : [keys];
    console.log(`[DataCache] Invalidating: ${keysToInvalidate.join(', ')}`);
    
    setCache(prev => {
      const next = { ...prev };
      Object.keys(next).forEach(cacheKey => {
        if (keysToInvalidate.some(k => cacheKey.startsWith(k))) {
          delete next[cacheKey];
        }
      });
      return next;
    });
  }, []);

  /**
   * Clear all cache
   */
  const clearCache = useCallback(() => {
    console.log('[DataCache] Clearing all cache');
    setCache({});
    pendingRequests.current = {};
  }, []);

  /**
   * Prefetch data - load data in background
   */
  const prefetch = useCallback(async (key, fetchFn, ttl, currency = null) => {
    const cached = getFromCache(key, currency);
    if (!cached) {
      // Prefetch in background, don't await
      fetchWithCache(key, fetchFn, ttl, currency).catch(err => {
        console.log(`[DataCache] Prefetch failed for ${key}:`, err.message);
      });
    }
  }, [getFromCache, fetchWithCache]);

  const value = {
    getFromCache,
    setInCache,
    fetchWithCache,
    invalidateCache,
    clearCache,
    prefetch,
    CACHE_TTL,
  };

  return (
    <DataCacheContext.Provider value={value}>
      {children}
    </DataCacheContext.Provider>
  );
};

export const useDataCache = () => {
  const context = useContext(DataCacheContext);
  if (!context) {
    throw new Error('useDataCache must be used within a DataCacheProvider');
  }
  return context;
};

export default DataCacheContext;
