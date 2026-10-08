import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createDataCache } from '../../src/services/dataCache';
import { usePortfolioSnapshot } from '../../src/hooks/usePortfolioSnapshot';

const mocks = vi.hoisted(() => ({ api: { get: vi.fn() }, cache: null }));
vi.mock('../../src/contexts/AuthContext', () => ({ useAuth: () => ({ api: mocks.api, portfolioId: 1 }) }));
vi.mock('../../src/contexts/CurrencyContext', () => ({ useCurrency: () => ({ currency: 'USD' }) }));
vi.mock('../../src/contexts/DataCacheContext', () => ({ useDataCache: () => mocks.cache }));
const snapshot = value => ({ portfolio_id: 1, currency: 'USD', total_value: value, holdings: [], cash_balance: 0 });

beforeEach(() => {
  sessionStorage.clear();
  mocks.api.get.mockReset();
  mocks.cache = { ...createDataCache(1), CACHE_TTL: { HOLDINGS: 60000 } };
});

describe('snapshot synchronization after live quotes', () => {
  it('replaces a cached overview valuation after a live-market update', async () => {
    mocks.cache.setInCache('portfolio_snapshot:1', snapshot(315000), 60000, 'USD');
    mocks.api.get.mockResolvedValue({ data: snapshot(431000) });
    const { result } = renderHook(() => usePortfolioSnapshot());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.data.total_value).toBe(315000);
    expect(mocks.api.get).not.toHaveBeenCalled();
    act(() => {
      // Both market and summary publishers invalidate before announcing newer quotes.
      mocks.cache.invalidateCache('portfolio_snapshot:1');
      window.dispatchEvent(new CustomEvent('portfolio:pricesUpdated', { detail: { portfolioId: 1, currency: 'USD' } }));
    });
    await waitFor(() => expect(result.current.data.total_value).toBe(431000));
    expect(mocks.api.get).toHaveBeenCalledWith('/portfolios/snapshot', { params: { currency: 'USD' }, timeout: 8000 });
  });

  it('ignores quote updates for another portfolio or currency', async () => {
    mocks.cache.setInCache('portfolio_snapshot:1', snapshot(315000), 60000, 'USD');
    const { result } = renderHook(() => usePortfolioSnapshot());
    await waitFor(() => expect(result.current.loading).toBe(false));
    act(() => {
      window.dispatchEvent(new CustomEvent('portfolio:pricesUpdated', { detail: { portfolioId: 2, currency: 'USD' } }));
      window.dispatchEvent(new CustomEvent('portfolio:pricesUpdated', { detail: { portfolioId: 1, currency: 'CAD' } }));
    });
    expect(mocks.api.get).not.toHaveBeenCalled();
    expect(result.current.data.total_value).toBe(315000);
  });
});
