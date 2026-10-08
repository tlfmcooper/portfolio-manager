import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createDataCache } from '../../src/services/dataCache';
import { usePortfolioAnalysis } from '../../src/hooks/usePortfolioAnalysis';

const mocks = vi.hoisted(() => ({ api: { get: vi.fn() }, cache: null }));
vi.mock('../../src/contexts/AuthContext', () => ({ useAuth: () => ({ api: mocks.api, portfolioId: 1 }) }));
vi.mock('../../src/contexts/DataCacheContext', () => ({ useDataCache: () => mocks.cache }));
beforeEach(() => {
  sessionStorage.clear();
  mocks.api.get.mockReset();
  mocks.cache = { ...createDataCache(1), CACHE_TTL: { PORTFOLIO_METRICS: 120000 } };
});

describe('analytics navigation', () => {
  it('renders Overview metrics in Risk without another server request', () => {
    const metrics = { sharpe_ratio: 2, value_at_risk_95: -0.03 };
    mocks.cache.setInCache('portfolio_metrics:1', metrics, 120000, 'USD');
    const { result } = renderHook(() => usePortfolioAnalysis('metrics', 'USD'));
    expect(result.current.data).toEqual(metrics);
    expect(result.current.loading).toBe(false);
    expect(mocks.api.get).not.toHaveBeenCalled();
  });

  it('rejoins a pending calculation after leaving and returning', async () => {
    let finish;
    mocks.api.get.mockReturnValue(new Promise(resolve => { finish = resolve; }));
    const first = renderHook(() => usePortfolioAnalysis('efficient-frontier', 'USD'));
    await waitFor(() => expect(mocks.api.get).toHaveBeenCalledTimes(1));
    first.unmount();
    const second = renderHook(() => usePortfolioAnalysis('efficient-frontier', 'USD'));
    await act(async () => { finish({ data: { frontier_points: [1] } }); });
    expect(second.result.current.data.frontier_points).toEqual([1]);
    expect(mocks.api.get).toHaveBeenCalledTimes(1);
    second.unmount();
    const third = renderHook(() => usePortfolioAnalysis('efficient-frontier', 'USD'));
    expect(third.result.current.loading).toBe(false);
    expect(third.result.current.data.frontier_points).toEqual([1]);
    expect(mocks.api.get).toHaveBeenCalledTimes(1);
  });

  it('keeps the last calculation visible while an expired cache is refreshed', async () => {
    mocks.cache.setInCache('portfolio_metrics:1', { sharpe_ratio: 2 }, -1, 'USD');
    let finish;
    mocks.api.get.mockReturnValue(new Promise(resolve => { finish = resolve; }));
    const { result } = renderHook(() => usePortfolioAnalysis('metrics', 'USD'));
    expect(result.current.data.sharpe_ratio).toBe(2);
    expect(result.current.loading).toBe(false);
    expect(result.current.updating).toBe(true);
    await waitFor(() => expect(mocks.api.get).toHaveBeenCalledTimes(1));
    await act(async () => { finish({ data: { sharpe_ratio: 3 } }); });
    expect(result.current.data.sharpe_ratio).toBe(3);
    expect(result.current.updating).toBe(false);
  });

  it('separates currencies and simulation parameters without showing the old result', async () => {
    mocks.api.get.mockResolvedValueOnce({ data: { final_mean: 120 } });
    const { result, rerender } = renderHook(({ currency, scenarios }) =>
      usePortfolioAnalysis('monte-carlo', currency, { scenarios }),
    { initialProps: { currency: 'USD', scenarios: 100 } });
    await waitFor(() => expect(result.current.data?.final_mean).toBe(120));
    let finish;
    mocks.api.get.mockReturnValue(new Promise(resolve => { finish = resolve; }));
    rerender({ currency: 'CAD', scenarios: 200 });
    expect(result.current.data).toBeNull();
    await waitFor(() => expect(mocks.api.get).toHaveBeenCalledWith('/analysis/portfolios/1/monte-carlo', {
      params: { currency: 'CAD', scenarios: 200, time_horizon: 252 },
    }));
    await act(async () => { finish({ data: { final_mean: 160 } }); });
    expect(result.current.data.final_mean).toBe(160);
    rerender({ currency: 'USD', scenarios: 100 });
    expect(result.current.data.final_mean).toBe(120);
    expect(mocks.api.get).toHaveBeenCalledTimes(2);
  });
});
