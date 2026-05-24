import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const mocks = vi.hoisted(() => ({
  apiGet: vi.fn(() => new Promise(() => {})),
}));

vi.mock('../../src/contexts/AuthContext', () => ({
  useAuth: () => ({
    api: { get: mocks.apiGet },
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
});
