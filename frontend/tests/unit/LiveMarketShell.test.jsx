import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const mocks = vi.hoisted(() => {
  const apiGet = vi.fn(() => new Promise(() => {}));
  return {
    api: { get: apiGet },
    apiGet,
  };
});

vi.mock('../../src/contexts/AuthContext', () => ({
  useAuth: () => ({
    api: mocks.api,
    user: { username: 'tester', display_name: 'Tester' },
    logout: vi.fn(),
  }),
}));

vi.mock('../../src/contexts/CurrencyContext', () => ({
  useCurrency: () => ({
    currency: 'USD',
    formatCurrency: (value) => `$${Number(value || 0).toFixed(2)}`,
  }),
}));

vi.mock('../../src/contexts/ThemeContext', () => ({
  useTheme: () => ({
    theme: 'light',
    resolvedTheme: 'light',
    isDark: false,
    toggleTheme: vi.fn(),
  }),
}));

vi.mock('../../src/components/PortfolioChatWidget', () => ({
  default: () => null,
}));

vi.mock('../../src/components/LiveStockChart', () => ({
  default: ({ selectedStock, chartData }) => (
    <div>Live chart for {selectedStock}: {chartData.length} point(s)</div>
  ),
}));

import DashboardLayout from '../../src/pages/DashboardLayout';
import LiveMarket from '../../src/pages/LiveMarket';

describe('live market route shell', () => {
  beforeEach(() => {
    localStorage.removeItem('live_market_USD');
    mocks.apiGet.mockClear();
  });

  it('renders the dashboard shell while live market data is still loading', async () => {
    render(
      <MemoryRouter initialEntries={['/dashboard/live-market']}>
        <Routes>
          <Route path="/dashboard" element={<DashboardLayout />}>
            <Route path="live-market" element={<LiveMarket />} />
          </Route>
        </Routes>
      </MemoryRouter>
    );

    expect(await screen.findByText('Strategic Multi-Asset Portfolio')).toBeInTheDocument();
    expect(screen.getByText(/Welcome back, Tester/)).toBeInTheDocument();
  });

  it('does not mark MAU.TO as missing live data when the live endpoint returns a quote', async () => {
    mocks.apiGet.mockImplementation((url) => {
      if (url === '/market/live') {
        return Promise.resolve({
          data: {
            holdings: [
              {
                id: 1,
                ticker: 'MAU.TO',
                quantity: 145,
                average_cost: 7,
                current_price: 11.07,
                market_value: 1605.15,
                change_percent: 6.77,
                change: 0.7,
                asset: { name: 'Montage Gold Corp.' },
              },
            ],
            cash_balance: 0,
            updated_at: new Date().toISOString(),
          },
        });
      }
      if (url === '/market/ytd') {
        return Promise.resolve({ data: { ytd_data: [{ ticker: 'MAU.TO', ytd_return: 54.91 }] } });
      }
      return new Promise(() => {});
    });

    render(
      <MemoryRouter initialEntries={['/dashboard/live-market']}>
        <Routes>
          <Route path="/dashboard" element={<DashboardLayout />}>
            <Route path="live-market" element={<LiveMarket />} />
          </Route>
        </Routes>
      </MemoryRouter>
    );

    expect((await screen.findAllByText('MAU.TO')).length).toBeGreaterThan(0);
    expect((await screen.findAllByText('+6.77%')).length).toBeGreaterThan(0);
    expect(await screen.findByText('Live chart for MAU.TO: 1 point(s)')).toBeInTheDocument();
    expect(screen.queryByText(/No live data/i)).not.toBeInTheDocument();
  });

  it('renders a polling-backed chart for crypto holdings', async () => {
    mocks.apiGet.mockImplementation((url) => {
      if (url === '/market/live') {
        return Promise.resolve({
          data: {
            holdings: [
              {
                id: 1,
                ticker: 'SOL',
                chart_source: 'polling',
                quantity: 2,
                average_cost: 100,
                current_price: 148.25,
                market_value: 296.5,
                change_percent: 1.25,
                change: 1.83,
                asset: { name: 'Solana USD' },
              },
            ],
            cash_balance: 0,
            updated_at: new Date().toISOString(),
          },
        });
      }
      if (url === '/market/ytd') {
        return Promise.resolve({ data: { ytd_data: [{ ticker: 'SOL', ytd_return: 10.5 }] } });
      }
      return new Promise(() => {});
    });

    render(
      <MemoryRouter initialEntries={['/dashboard/live-market']}>
        <Routes>
          <Route path="/dashboard" element={<DashboardLayout />}>
            <Route path="live-market" element={<LiveMarket />} />
          </Route>
        </Routes>
      </MemoryRouter>
    );

    expect(await screen.findByText('Live chart for SOL: 1 point(s)')).toBeInTheDocument();
  });
});
