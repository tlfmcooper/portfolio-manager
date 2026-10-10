import { useEffect, useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useDataCache } from '../contexts/DataCacheContext';
import { usePortfolioScenario } from '../contexts/PortfolioScenarioContext';
import { analysisParams, analysisKey } from '../utils/analysisKeys';

export function usePortfolioAnalysis(kind, currency, parameters = {}) {
  const { api, portfolioId } = useAuth();
  const { getFromCache, fetchWithCache, CACHE_TTL } = useDataCache();
  const scenario = usePortfolioScenario();
  const signature = scenario?.signature || 'null';
  const serialized = analysisParams(kind, parameters);
  const key = analysisKey(portfolioId, kind, serialized, signature, scenario?.valuation);
  const cached = portfolioId ? getFromCache(key, currency, { allowStale: true }) : null;
  const [state, setState] = useState(() => ({ key, currency, data: cached, loading: !cached, updating: false, error: null }));

  useEffect(() => {
    let active = true;
    const current = portfolioId ? getFromCache(key, currency) : null;
    const shown = current || (portfolioId ? getFromCache(key, currency, { allowStale: true }) : null);
    setState({ key, currency, data: shown, loading: !!portfolioId && !shown, updating: !!portfolioId && !current, error: null });
    if (!portfolioId || current) return () => { active = false; };
    const ttl = kind === 'metrics' ? CACHE_TTL.PORTFOLIO_METRICS : kind === 'efficient-frontier' ? 900000 : 600000;
    fetchWithCache(key, async () => signature === 'null'
      ? (await api.get(`/analysis/portfolios/${portfolioId}/${kind}`, { params: { ...JSON.parse(serialized), currency } })).data
      : (await api.post(`/analysis/portfolios/${portfolioId}/scenario`, {
        ...JSON.parse(signature), ...JSON.parse(serialized), kind, currency,
      }, { timeout: 60000 })).data, ttl, currency).then(data => {
      if (active) setState({ key, currency, data, loading: false, updating: false, error: null });
    }).catch(error => {
      if (active) setState({ key, currency, data: shown, loading: false, updating: false,
        error: typeof error.response?.data?.detail === 'string' ? error.response.data.detail : 'Unable to load portfolio analytics. Please retry.' });
    });
    return () => { active = false; };
  }, [api, portfolioId, kind, currency, serialized, signature, key, getFromCache, fetchWithCache, CACHE_TTL]);

  // Changing currency or parameters must never render the previous calculation.
  return state.key === key && state.currency === currency ? state
    : { data: cached, loading: !!portfolioId && !cached, updating: false, error: null };
}
