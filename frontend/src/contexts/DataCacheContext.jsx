/** Session-scoped cache with stable callbacks and request deduplication. */
import React, { createContext, useContext, useMemo, useEffect } from 'react';
import { useAuth } from './AuthContext';
import { createDataCache } from '../services/dataCache';

const DataCacheContext = createContext(null);
const CACHE_TTL = Object.freeze({
  PORTFOLIO_METRICS: 120000, HOLDINGS: 60000, ALLOCATION: 120000,
  DASHBOARD: 60000, MARKET_DATA: 30000,
});

export const DataCacheProvider = ({ children }) => {
  const { user } = useAuth();
  const cache = useMemo(() => createDataCache(user?.id), [user?.id]);
  useEffect(() => {
    const clear = () => cache.clearCache();
    window.addEventListener('auth:logout', clear);
    window.addEventListener('auth:sessionExpired', clear);
    return () => {
      window.removeEventListener('auth:logout', clear);
      window.removeEventListener('auth:sessionExpired', clear);
      cache.dispose();
    };
  }, [cache]);
  const value = useMemo(() => ({ ...cache, CACHE_TTL }), [cache]);
  return <DataCacheContext.Provider value={value}>{children}</DataCacheContext.Provider>;
};

export const useDataCache = () => {
  const context = useContext(DataCacheContext);
  if (!context) throw new Error('useDataCache must be used within a DataCacheProvider');
  return context;
};
export default DataCacheContext;
