import { useCallback, useEffect, useRef, useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useCurrency } from '../contexts/CurrencyContext';
import { useDataCache } from '../contexts/DataCacheContext';

export function usePortfolioSnapshot() {
  const { api, portfolioId } = useAuth();
  const { currency } = useCurrency();
  const { getFromCache, fetchWithCache, invalidateCache, CACHE_TTL } = useDataCache();
  const key = `portfolio_snapshot:${portfolioId}`;
  const [data, setData] = useState(() => getFromCache(key, currency, { allowStale: true }));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const request = useRef(0);
  const cancelLoad = useCallback(() => { request.current++; }, []);

  const load = useCallback(async ({ refreshPrices = false, force = false } = {}) => {
    if (!portfolioId) return;
    const id = ++request.current;
    setLoading(true);
    setError(null);
    try {
      if (refreshPrices) {
        await api.get('/market/live', { params: { currency, refresh: true }, timeout: 20000 });
        invalidateCache(['portfolio_snapshot', 'portfolio_summary', 'portfolio_metrics', 'portfolio_analysis', 'sector_allocation']);
      }
      const snapshot = await fetchWithCache(key,
        async () => (await api.get('/portfolios/snapshot', { params: { currency }, timeout: 8000 })).data,
        CACHE_TTL.HOLDINGS, currency, { force: force || refreshPrices });
      if (id === request.current) setData(snapshot);
    } catch (err) {
      if (id === request.current) setError(err.response?.data?.detail || 'Unable to update portfolio. Previously loaded values are shown when available.');
    } finally {
      if (id === request.current) setLoading(false);
    }
  }, [api, portfolioId, currency, key, fetchWithCache, invalidateCache, CACHE_TTL]);

  useEffect(() => {
    setData(getFromCache(key, currency, { allowStale: true }));
    load();
    return cancelLoad;
  }, [key, currency, getFromCache, load, cancelLoad]);

  useEffect(() => {
    const pricesUpdated = event => {
      if (event.detail?.portfolioId === portfolioId && event.detail?.currency === currency) {
        load({ force: true });
      }
    };
    window.addEventListener('portfolio:pricesUpdated', pricesUpdated);
    return () => window.removeEventListener('portfolio:pricesUpdated', pricesUpdated);
  }, [portfolioId, currency, load]);

  return { data: data?.portfolio_id === portfolioId && data?.currency === currency ? data : null, loading, error, load };
}
