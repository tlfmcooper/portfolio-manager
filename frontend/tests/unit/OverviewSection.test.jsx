import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import OverviewSection from '../../src/components/OverviewSection';

const mocks = vi.hoisted(() => {
  const apiGet = vi.fn();
  const apiPost = vi.fn();
  return { apiGet, apiPost, scenario: null, api: { get: apiGet, post: apiPost }, cache: {
    CACHE_TTL: { PORTFOLIO_METRICS: 120000 },
    getFromCache: vi.fn(() => null), fetchWithCache: (_key, fn) => fn(),
  } };
});
vi.mock('../../src/contexts/AuthContext', () => ({ useAuth: () => ({ api: mocks.api, portfolioId: 1 }) }));
vi.mock('../../src/contexts/CurrencyContext', () => ({ useCurrency: () => ({ currency: 'USD' }) }));
vi.mock('../../src/contexts/DataCacheContext', () => ({ useDataCache: () => mocks.cache }));
vi.mock('../../src/contexts/PortfolioScenarioContext', () => ({ usePortfolioScenario: () => mocks.scenario }));

const account = { ytd_return_percentage: 37.44, portfolio_return_annualized: .4569,
  portfolio_volatility_annualized: .2725, sharpe_ratio: 1.461, sortino_ratio: 2.349,
  max_drawdown: -.1505, calmar_ratio: 3.035, performance_basis: 'account_ytd',
  analysis_context: { method: 'account_ytd', coverage_percentage: 100, observations: 213,
    history_start: '2026-01-01', history_end: '2026-10-26', risk_free_rate: .042, holdings: [], notes: [] } };

describe('OverviewSection', () => {
  beforeEach(() => {
    mocks.scenario = null;
    mocks.apiGet.mockReset(); mocks.apiPost.mockReset();
    mocks.cache.getFromCache.mockReset().mockReturnValue(null);
  });

  it('uses one account YTD series for return and every ratio', async () => {
    mocks.apiGet.mockResolvedValue({ data: account });
    render(<OverviewSection />);
    expect(await screen.findByText('+37.44%')).toBeInTheDocument();
    expect(screen.getByText('Account Annualized Return')).toBeInTheDocument();
    expect(screen.getByText('+45.69%')).toBeInTheDocument();
    expect(screen.getByText('1.461')).toBeInTheDocument();
    expect(screen.getByText(/Account YTD performance • 213 daily returns/)).toBeInTheDocument();
    expect(screen.queryByText('Modeled Annualized Return')).not.toBeInTheDocument();
    expect(mocks.apiGet).toHaveBeenCalledTimes(1);
    expect(mocks.apiGet).toHaveBeenCalledWith('/analysis/portfolios/1/account-performance', expect.any(Object));
  });

  it('discloses incomplete account history without substituting modeled ratios', async () => {
    mocks.apiGet.mockRejectedValue({ response: { status: 422, data: { detail: 'Account YTD performance unavailable: Missing history for OLD' } } });
    render(<OverviewSection />);
    expect(await screen.findByRole('alert')).toHaveTextContent('Missing history for OLD');
    expect(screen.queryByText('Sharpe Ratio')).not.toBeInTheDocument();
    expect(mocks.apiPost).not.toHaveBeenCalled();
  });

  it('keeps account results visible during a refresh', () => {
    mocks.cache.getFromCache.mockImplementation(key => key.startsWith('account_ytd:') ? account : { sharpe_ratio: -.084 });
    mocks.apiGet.mockImplementation(() => new Promise(() => {}));
    render(<OverviewSection />);
    expect(screen.getByText('+37.44%')).toBeInTheDocument();
    expect(screen.getByText('1.461')).toBeInTheDocument();
    expect(screen.queryByText('-0.084')).not.toBeInTheDocument();
  });

  it('keeps allocation scenarios separate from account YTD', async () => {
    mocks.scenario = { signature: JSON.stringify({ preset: 'custom', weights: { weights: { AAA: 100 } } }) };
    mocks.apiPost.mockResolvedValue({ data: { portfolio_return_annualized: .0189, sharpe_ratio: -.084 } });
    render(<OverviewSection />);
    expect(await screen.findByText('Modeled Annualized Return')).toBeInTheDocument();
    expect(screen.getByText('-0.084')).toBeInTheDocument();
    expect(screen.queryByText('YTD Return')).not.toBeInTheDocument();
    expect(mocks.apiGet).not.toHaveBeenCalled();
  });
});
