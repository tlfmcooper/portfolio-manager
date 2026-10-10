import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { useAuth } from './AuthContext';
import { useCurrency } from './CurrencyContext';
import { useDataCache } from './DataCacheContext';
import { useAgentContext } from './AgentContext';
import { usePortfolioSnapshot } from '../hooks/usePortfolioSnapshot';
import { currentTargets, savedTargets, validTargets } from '../utils/portfolioPlanning';
import { analysisParams, analysisKey } from '../utils/analysisKeys';

const PortfolioScenarioContext = createContext(null);
// Also permits isolated analysis components to retain their existing default behavior.
export const usePortfolioScenario = () => useContext(PortfolioScenarioContext);

function percentages(weights) {
  const rounded = Object.fromEntries(Object.entries(weights).map(([ticker, value]) => [ticker, Math.round(value * 100) / 100]));
  const delta = Math.round((100 - Object.values(rounded).reduce((a, b) => a + b, 0)) * 100) / 100;
  const largest = Object.keys(rounded).sort((a, b) => rounded[b] - rounded[a])[0];
  if (largest) rounded[largest] = Math.round((rounded[largest] + delta) * 100) / 100;
  return rounded;
}

export function PortfolioScenarioProvider({ children }) {
  const { api, portfolioId, user } = useAuth();
  const { currency } = useCurrency();
  const { fetchWithCache, getFromCache, setInCache } = useDataCache();
  const { resetAllParams, monteCarloParams, cppiParams } = useAgentContext();
  const { data: snapshot, load: loadSnapshot } = usePortfolioSnapshot();
  const owner = `${user?.id ?? 'anonymous'}:${portfolioId ?? ''}`;
  const [state, setState] = useState({ owner, mode: 'current', activeMode: 'current', draft: null, weights: null });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [preview, setPreview] = useState(null);
  const [mcpProposal, setMcpProposal] = useState(null);
  const requestId = useRef(0);
  const currentOwner = useRef(owner);
  currentOwner.current = owner;
  const currentCurrency = useRef(currency);
  currentCurrency.current = currency;
  const effective = state.owner === owner ? state : { mode: 'current', activeMode: 'current', draft: null, weights: null };
  const actual = snapshot ? currentTargets(snapshot) : {};
  const valuation = JSON.stringify(snapshot ? [snapshot.total_value, snapshot.cash_balance,
    snapshot.holdings.map(h => [h.ticker, h.quantity, h.market_value])] : []);
  const draft = effective.draft || actual;
  const valid = validTargets(draft);
  const draftSignature = JSON.stringify(draft);
  const universe = snapshot?.holdings.map(h => `${h.ticker}:${h.quantity}`).sort().join('|');
  const previousUniverse = useRef();
  const simulationParams = JSON.stringify({ mc: monteCarloParams, cppi: cppiParams });
  const allParams = { scenarios: monteCarloParams.scenarios ?? 1000, time_horizon: monteCarloParams.time_horizon ?? 252,
    multiplier: cppiParams.multiplier ?? 3, floor: cppiParams.floor ?? .8, cppi_time_horizon: cppiParams.time_horizon ?? 252 };
  const cacheBundle = (result, signature) => {
    setInCache(`portfolio_analysis:scenario:${portfolioId}:${signature}:${simulationParams}:${valuation}`, result, 600000, currency);
    for (const [kind, data] of Object.entries(result.analytics)) {
      if (data.error) continue;
      const params = kind === 'monte-carlo' ? monteCarloParams : kind === 'cppi' ? cppiParams : {};
      const filtered = Object.fromEntries(Object.entries(params).filter(([name]) =>
        kind === 'monte-carlo' ? ['scenarios', 'time_horizon'].includes(name) : ['multiplier', 'floor', 'time_horizon'].includes(name)));
      setInCache(analysisKey(portfolioId, kind, analysisParams(kind, filtered), signature, valuation), data, 600000, currency);
    }
  };

  const resetWeights = useCallback(() => {
    requestId.current++;
    setState({ owner, mode: 'current', activeMode: 'current', draft: null, weights: null });
    setBusy(false); setError(null); setPreview(null); setMcpProposal(null);
  }, [owner]);
  const reset = useCallback(() => { resetWeights(); resetAllParams(); }, [resetWeights, resetAllParams]);

  useEffect(() => {
    if (previousUniverse.current !== undefined && universe !== undefined && previousUniverse.current !== universe) reset();
    if (universe !== undefined) previousUniverse.current = universe;
  }, [universe, reset]);
  useEffect(() => { reset(); }, [owner, reset]); // Account-scoped, ephemeral what-if state.
  useEffect(() => {
    const changed = () => { reset(); loadSnapshot({ force: true }); };
    window.addEventListener('portfolio:holdingsUpdated', changed);
    return () => window.removeEventListener('portfolio:holdingsUpdated', changed);
  }, [reset, loadSnapshot]);

  const edit = useCallback((ticker, value) => {
    requestId.current++;
    setBusy(false); setError(null); setPreview(null);
    setState(prev => ({ ...(prev.owner === owner ? prev : { owner, activeMode: 'current', weights: null }),
      mode: 'custom', draft: { ...(prev.owner === owner && prev.draft ? prev.draft : actual), [ticker]: value } }));
  }, [owner, draftSignature]);

  const applyWeights = useCallback(weights => {
    const normalized = Object.fromEntries(Object.entries(weights).map(([ticker, value]) => [ticker, Number(value)]));
    if (!validTargets(weights) || Object.keys(weights).some(ticker => !(ticker in actual))) throw new Error('Use current portfolio tickers and percentages totaling 100%, including CASH.');
    requestId.current++;
    setBusy(false); setError(null); setPreview(null);
    setState({ owner, mode: 'custom', activeMode: 'custom', draft: normalized, weights: normalized });
  }, [owner, JSON.stringify(actual)]);

  useEffect(() => {
    if (effective.mode !== 'custom' || !valid) return undefined;
    const timer = setTimeout(() => {
      const weights = Object.fromEntries(Object.entries(JSON.parse(draftSignature)).map(([ticker, value]) => [ticker, Number(value)]));
      setState(prev => prev.owner === owner ? { ...prev, weights, activeMode: 'custom' } : prev);
    }, 500);
    return () => clearTimeout(timer);
  }, [owner, effective.mode, valid, draftSignature]);

  const selectMSR = useCallback(async () => {
    const id = ++requestId.current;
    const scope = owner;
    const scopeCurrency = currency;
    setBusy(true); setError(null);
    try {
      const response = await fetchWithCache(`portfolio_analysis:scenario:${portfolioId}:msr:${valuation}:${simulationParams}`,
        async () => (await api.post(`/analysis/portfolios/${portfolioId}/scenario`, { preset: 'msr', kind: 'all', currency, ...allParams }, { timeout: 60000 })).data,
        600000, currency);
      if (id !== requestId.current || currentOwner.current !== scope || currentCurrency.current !== scopeCurrency) return;
      const weights = percentages(response.analysis_context.weights);
      const resolved = response.analysis_context.weights;
      cacheBundle(response, JSON.stringify({ preset: 'custom', weights: { weights: resolved } }));
      setState({ owner: scope, mode: 'msr', activeMode: 'msr', draft: weights, weights: resolved });
      setPreview(response);
      return response;
    } catch (err) {
      if (id === requestId.current && currentOwner.current === scope) setError(typeof err.response?.data?.detail === 'string' ? err.response.data.detail : 'Unable to calculate MSR weights. Please retry.');
      throw err;
    } finally { if (id === requestId.current) setBusy(false); }
  }, [api, portfolioId, currency, owner, fetchWithCache, setInCache, valuation, simulationParams]);

  const scenarioRequest = effective.activeMode === 'current' ? null
    : { preset: 'custom', weights: { weights: effective.weights } };
  const signature = JSON.stringify(scenarioRequest);
  useEffect(() => {
    if (signature === 'null' || !portfolioId) return undefined;
    let active = true;
    const key = `portfolio_analysis:scenario:${portfolioId}:${signature}:${simulationParams}:${valuation}`;
    fetchWithCache(key, async () => (await api.post(`/analysis/portfolios/${portfolioId}/scenario`,
      { ...JSON.parse(signature), ...allParams, currency, kind: 'all' }, { timeout: 60000 })).data, 600000, currency)
      .then(result => {
        if (!active) return;
        setPreview(result);
        cacheBundle(result, signature);
      }).catch(err => { if (active) setError(typeof err.response?.data?.detail === 'string' ? err.response.data.detail : 'Unable to refresh scenario analytics.'); });
    return () => { active = false; };
  }, [api, portfolioId, currency, signature, simulationParams, valuation, owner, fetchWithCache, setInCache]);
  useEffect(() => {
    if (effective.activeMode === 'msr' && preview && preview.analysis_context.currency !== currency) selectMSR().catch(() => {});
  }, [currency, effective.activeMode, preview, selectMSR]);
  const comparison = async (weights, preset = 'custom') => (await api.post(`/analysis/portfolios/${portfolioId}/scenario`,
    { preset, ...(preset === 'custom' ? { weights: { weights } } : {}), kind: 'all', currency }, { timeout: 60000 })).data;
  const coverage = preview?.analysis_context || getFromCache(`portfolio_metrics:${portfolioId}`, currency, { allowStale: true })?.analysis_context;
  useEffect(() => {
    const receive = event => {
      const proposal = event.detail;
      if (proposal?.analysis_context?.portfolio_id !== portfolioId || proposal.analysis_context.currency !== currency) return;
      if (!validTargets(proposal.analysis_context.weights) || !Array.isArray(proposal.analysis_context.holdings)
        || !Array.isArray(proposal.analysis_context.notes) || !proposal.analysis_context.notes.every(note => typeof note === 'string')
        || !Number.isFinite(proposal.analysis_context.coverage_percentage) || !Number.isFinite(proposal.analysis_context.observations)) return;
      setMcpProposal(proposal);
    };
    window.addEventListener('portfolio:scenario-proposal', receive);
    return () => window.removeEventListener('portfolio:scenario-proposal', receive);
  }, [portfolioId, currency]);
  const value = { snapshot, draft, actual, valid, mode: effective.mode, activeMode: effective.activeMode,
    scenarioRequest, signature, valuation, busy, error, coverage, preview, edit, applyWeights, selectMSR, reset, resetWeights,
    comparison, mcpProposal, dismissProposal: () => setMcpProposal(null),
    loadSaved: () => { const weights = savedTargets(snapshot); if (weights) applyWeights(weights); } };
  return <PortfolioScenarioContext.Provider value={value}>{children}</PortfolioScenarioContext.Provider>;
}
