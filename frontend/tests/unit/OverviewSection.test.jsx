import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import OverviewSection from '../../src/components/OverviewSection';

const mocks = vi.hoisted(() => {
  const apiGet = vi.fn();
  return { apiGet, api: { get: apiGet }, cache: {
    CACHE_TTL: { PORTFOLIO_METRICS: 120000 },
    getFromCache: vi.fn(() => null),
    fetchWithCache: (_key, fetchFn) => fetchFn(),
    invalidateCache: vi.fn(),
  } };
});

vi.mock('../../src/contexts/AuthContext', () => ({
  useAuth: () => ({
    api: mocks.api,
    portfolioId: 1,
  }),
}));

vi.mock('../../src/contexts/CurrencyContext', () => ({
  useCurrency: () => ({
    currency: 'USD',
  }),
}));

vi.mock('../../src/contexts/DataCacheContext', () => ({
  useDataCache: () => mocks.cache,
}));

describe('OverviewSection', () => {
  beforeEach(() => {
    mocks.apiGet.mockReset();
    mocks.cache.getFromCache.mockReset().mockReturnValue(null);
    mocks.cache.invalidateCache.mockClear();
  });

  it('distinguishes account YTD from the modeled return underlying risk ratios', async () => {
    mocks.apiGet.mockImplementation((url) => {
      if (url.includes('/analysis/portfolios/1/metrics')) {
        return Promise.resolve({
          data: {
            portfolio_return_annualized: 0.8569,
            portfolio_volatility_annualized: 0.3278,
            sharpe_ratio: 2.386,
            sortino_ratio: 3.583,
            max_drawdown: -0.3001,
            calmar_ratio: 2.855,
            individual_performance: {},
          },
        });
      }

      return Promise.resolve({
        data: {
          ytd_return_percentage: 12.34,
          ytd_complete: true,
          ytd_message: null,
        },
      });
    });

    render(<OverviewSection />);

    expect(await screen.findByText('YTD Return')).toBeInTheDocument();
    expect(screen.getByText('+12.34%')).toBeInTheDocument();
    expect(screen.queryByText('Annual Return')).not.toBeInTheDocument();
    expect(screen.getByText('Modeled Annualized Return')).toBeInTheDocument();
    expect(screen.getByText('+85.69%')).toBeInTheDocument();
    expect(screen.getByText(/YTD return is calculated separately/)).toBeInTheDocument();
    expect(screen.getByText('Strong Downside-Adj Return')).toBeInTheDocument();
    expect(screen.getByText('Strong Return / Drawdown')).toBeInTheDocument();
  });

  it('shows N/A when portfolio YTD is unavailable', async () => {
    mocks.apiGet.mockImplementation((url) => {
      if (url.includes('/analysis/portfolios/1/metrics')) {
        return Promise.resolve({
          data: {
            portfolio_volatility_annualized: 0.3278,
            sharpe_ratio: 2.386,
            sortino_ratio: 3.583,
            max_drawdown: -0.3001,
            calmar_ratio: 2.855,
            individual_performance: {},
          },
        });
      }

      return Promise.resolve({
        data: {
          ytd_return_percentage: null,
          ytd_complete: false,
          ytd_message: 'Exact YTD return is unavailable.',
        },
      });
    });

    render(<OverviewSection />);

    expect(await screen.findByText('YTD Return')).toBeInTheDocument();
    await waitFor(() => expect(screen.getAllByText('N/A').length).toBeGreaterThan(0));
  });
  it('renders a summary while historical analytics are still pending', async () => {
    mocks.apiGet.mockImplementation(url => url.includes('/metrics')
      ? new Promise(() => {})
      : Promise.resolve({ data: { ytd_return_percentage: 8, ytd_complete: true } }));
    render(<OverviewSection />);
    expect(await screen.findByText('+8.00%')).toBeInTheDocument();
  });

  it('keeps cached metrics visible while a return visit refreshes them', () => {
    mocks.cache.getFromCache.mockImplementation(key => key.startsWith('portfolio_metrics')
      ? { sharpe_ratio: 2, portfolio_volatility_annualized: 0.3 }
      : { ytd_return_percentage: 8, ytd_complete: true });
    mocks.apiGet.mockImplementation(() => new Promise(() => {}));
    render(<OverviewSection />);
    expect(screen.getByText('+8.00%')).toBeInTheDocument();
    expect(screen.getByText('2.000')).toBeInTheDocument();
    expect(screen.getByText('Loading remaining analytics…')).toBeInTheDocument();
  });

  it('invalidates the snapshot and announces prices after receiving the summary', async () => {
    mocks.apiGet.mockResolvedValue({ data: { ytd_return_percentage: 8, ytd_complete: true } });
    const updates = vi.fn();
    window.addEventListener('portfolio:pricesUpdated', updates);
    try {
      render(<OverviewSection />);
      await waitFor(() => expect(updates).toHaveBeenCalledTimes(1));
      expect(mocks.cache.invalidateCache).toHaveBeenCalledWith(['portfolio_snapshot:1']);
      expect(updates.mock.calls[0][0].detail).toEqual({ portfolioId: 1, currency: 'USD' });
    } finally {
      window.removeEventListener('portfolio:pricesUpdated', updates);
    }
  });

});
