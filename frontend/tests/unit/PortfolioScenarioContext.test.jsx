import React from 'react';
import { act, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { PortfolioScenarioProvider, usePortfolioScenario } from '../../src/contexts/PortfolioScenarioContext';
import { createDataCache } from '../../src/services/dataCache';

const mocks = vi.hoisted(() => ({ api: { post: vi.fn() }, user: { id: 1 }, currency: 'USD', reset: vi.fn(), load: vi.fn(), cache: null, current: null }));
vi.mock('../../src/contexts/AuthContext', () => ({ useAuth: () => ({ api: mocks.api, portfolioId: 1, user: mocks.user }) }));
vi.mock('../../src/contexts/CurrencyContext', () => ({ useCurrency: () => ({ currency: mocks.currency }) }));
vi.mock('../../src/contexts/AgentContext', () => ({ useAgentContext: () => ({ resetAllParams: mocks.reset, monteCarloParams: {}, cppiParams: {} }) }));
vi.mock('../../src/contexts/DataCacheContext', () => ({ useDataCache: () => mocks.cache }));
vi.mock('../../src/hooks/usePortfolioSnapshot', () => ({ usePortfolioSnapshot: () => ({ data: {
  portfolio_id: 1, currency: mocks.currency, total_value: 1000, cash_balance: 200,
  holdings: [{ ticker: 'AAA', quantity: 6, market_value: 600 }, { ticker: 'BBB', quantity: 4, market_value: 200 }],
}, load: mocks.load }) }));
function Probe() {
  mocks.current = usePortfolioScenario();
  return <p>{mocks.current.activeMode}</p>;
}
const result = { analysis_context: { portfolio_id: 1, currency: 'USD', weights: { AAA: 0, BBB: 80, CASH: 20 }, holdings: [], notes: [] }, analytics: { metrics: { sharpe_ratio: 2 } } };
beforeEach(() => {
  sessionStorage.clear(); mocks.cache = createDataCache(1); mocks.user = { id: 1 }; mocks.currency = 'USD';
  mocks.api.post.mockReset().mockResolvedValue({ data: result }); mocks.reset.mockClear(); mocks.load.mockClear();
  vi.useFakeTimers();
});
afterEach(() => vi.useRealTimers());

describe('shared what-if state', () => {
  it('switches back to current weights without clearing simulation parameters', async () => {
    render(<PortfolioScenarioProvider><Probe /></PortfolioScenarioProvider>);
    await act(async () => { await mocks.current.selectMSR(); });
    const resets = mocks.reset.mock.calls.length;
    act(() => mocks.current.resetWeights());
    expect(mocks.current.activeMode).toBe('current');
    expect(mocks.reset).toHaveBeenCalledTimes(resets);
  });
  it('debounces valid weights, recalculates all charts, and resets all overrides', async () => {
    render(<PortfolioScenarioProvider><Probe /></PortfolioScenarioProvider>);
    act(() => mocks.current.edit('AAA', '50'));
    await act(async () => vi.advanceTimersByTime(700));
    expect(mocks.current.valid).toBe(false);
    expect(mocks.current.activeMode).toBe('current');
    expect(mocks.api.post).not.toHaveBeenCalled();
    act(() => mocks.current.edit('BBB', '30'));
    await act(async () => vi.advanceTimersByTime(499));
    expect(mocks.current.activeMode).toBe('current');
    await act(async () => vi.advanceTimersByTime(1));
    expect(screen.getByText('custom')).toBeInTheDocument();
    expect(mocks.api.post).toHaveBeenCalledWith('/analysis/portfolios/1/scenario', expect.objectContaining({
      kind: 'all', preset: 'custom', weights: { weights: { AAA: 50, BBB: 30, CASH: 20 } },
    }), { timeout: 60000 });
    act(() => mocks.current.reset());
    expect(mocks.current.draft).toEqual({ AAA: 60, BBB: 20, CASH: 20 });
    expect(mocks.current.signature).toBe('null');
    expect(mocks.reset).toHaveBeenCalled();
  });
  it('discards an MSR response after reset', async () => {
    let finish;
    mocks.api.post.mockReturnValue(new Promise(resolve => { finish = resolve; }));
    render(<PortfolioScenarioProvider><Probe /></PortfolioScenarioProvider>);
    let pending;
    await act(async () => { pending = mocks.current.selectMSR(); });
    act(() => mocks.current.reset());
    await act(async () => { finish({ data: result }); await pending; });
    expect(mocks.current.activeMode).toBe('current');
    expect(mocks.current.preview).toBeNull();
  });
  it('seeds all chart caches from one MSR response and clears scenarios on account changes', async () => {
    const tree = render(<PortfolioScenarioProvider><Probe /></PortfolioScenarioProvider>);
    await act(async () => { await mocks.current.selectMSR(); });
    expect(mocks.api.post).toHaveBeenCalledTimes(1);
    expect(mocks.current.activeMode).toBe('msr');
    expect(JSON.parse(mocks.current.signature)).toEqual({ preset: 'custom', weights: { weights: result.analysis_context.weights } });
    expect(mocks.cache.getFromCache(`portfolio_analysis:scenario:1:metrics:${mocks.current.signature}:{}:${mocks.current.valuation}`, 'USD').sharpe_ratio).toBe(2);
    mocks.user = { id: 2 };
    tree.rerender(<PortfolioScenarioProvider><Probe /></PortfolioScenarioProvider>);
    expect(mocks.current.activeMode).toBe('current');
    expect(mocks.current.preview).toBeNull();
  });
});
