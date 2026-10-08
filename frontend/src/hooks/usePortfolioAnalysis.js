import { useEffect, useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useDataCache } from '../contexts/DataCacheContext';

const defaults = {
  'monte-carlo': { scenarios: 1000, time_horizon: 252 },
  cppi: { multiplier: 3, floor: 0.8, time_horizon: 252 },
};

export function usePortfolioAnalysis(kind, currency, parameters = {}) {
  const { api, portfolioId } = useAuth();
  const { getFromCache, fetchWithCache, CACHE_TTL } = useDataCache();
  const params = { ...defaults[kind], ...parameters };
  delete params.currency;
  const serialized = JSON.stringify(Object.fromEntries(Object.entries(params)
    .filter(([, value]) => value !== undefined).sort(([a], [b]) => a.localeCompare(b))));
  const key = kind === 'metrics' ? `portfolio_metrics:${portfolioId}`
    : `portfolio_analysis:${portfolioId}:${kind}:${serialized}`;
  const cached = portfolioId ? getFromCache(key, currency, { allowStale: true }) : null;
  const [state, setState] = useState(() => ({ key, currency, data: cached, loading: !cached, updating: false, error: null }));

  useEffect(() => {
    let active = true;
    const current = portfolioId ? getFromCache(key, currency) : null;
    const shown = current || (portfolioId ? getFromCache(key, currency, { allowStale: true }) : null);
    setState({ key, currency, data: shown, loading: !!portfolioId && !shown, updating: !!portfolioId && !current, error: null });
    if (!portfolioId || current) return () => { active = false; };
    const ttl = kind === 'metrics' ? CACHE_TTL.PORTFOLIO_METRICS : kind === 'efficient-frontier' ? 900000 : 600000;
    fetchWithCache(key, async () => (await api.get(`/analysis/portfolios/${portfolioId}/${kind}`, {
      params: { ...JSON.parse(serialized), currency },
    })).data, ttl, currency).then(data => {
      if (active) setState({ key, currency, data, loading: false, updating: false, error: null });
    }).catch(error => {
      if (active) setState({ key, currency, data: shown, loading: false, updating: false,
        error: typeof error.response?.data?.detail === 'string' ? error.response.data.detail : 'Unable to load portfolio analytics. Please retry.' });
    });
    return () => { active = false; };
  }, [api, portfolioId, kind, currency, serialized, key, getFromCache, fetchWithCache, CACHE_TTL]);

  // Changing currency or parameters must never render the previous calculation.
  return state.key === key && state.currency === currency ? state
    : { data: cached, loading: !!portfolioId && !cached, updating: false, error: null };
}
