import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import OverviewSection from '../../src/components/OverviewSection';

const mocks = vi.hoisted(() => ({
  apiGet: vi.fn(),
}));

vi.mock('../../src/contexts/AuthContext', () => ({
  useAuth: () => ({
    api: { get: mocks.apiGet },
    portfolioId: 1,
  }),
}));

vi.mock('../../src/contexts/CurrencyContext', () => ({
  useCurrency: () => ({
    currency: 'USD',
  }),
}));

vi.mock('../../src/contexts/DataCacheContext', () => ({
  useDataCache: () => ({
    CACHE_TTL: { PORTFOLIO_METRICS: 120000 },
    fetchWithCache: (_key, fetchFn) => fetchFn(),
  }),
}));

describe('OverviewSection', () => {
  beforeEach(() => {
    mocks.apiGet.mockReset();
  });

  it('shows YTD return instead of annual return on the first metric card', async () => {
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
    await waitFor(() => expect(screen.getByText('N/A')).toBeInTheDocument());
  });
});
