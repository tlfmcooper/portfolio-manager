import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import PortfolioWorkspace from '../../src/components/PortfolioWorkspace';
const mocks = vi.hoisted(() => ({ put: vi.fn(), load: vi.fn(), invalidate: vi.fn(), snapshot: null }));
vi.mock('../../src/contexts/AuthContext', () => ({ useAuth: () => ({ api: { put: mocks.put } }) }));
vi.mock('../../src/contexts/CurrencyContext', () => ({ useCurrency: () => ({ formatCurrency: value => `$${value.toFixed(2)}` }) }));
vi.mock('../../src/contexts/DataCacheContext', () => ({ useDataCache: () => ({ invalidateCache: mocks.invalidate }) }));
vi.mock('../../src/hooks/usePortfolioSnapshot', () => ({ usePortfolioSnapshot: () => mocks.snapshot }));
const data = { portfolio_id: 1, currency: 'USD', total_value: 1000, holdings_value: 800, cash_balance: 200, unrealized_gain_loss: 100,
  estimated_prices: 0, generated_at: '2026-10-08T10:00:00Z', holdings: [
    { ticker: 'AAA', quantity: 6, market_value: 600, current_price: 100, target_allocation: null, sector: 'Technology', price_source: 'stored_quote', price_as_of: '2026-10-08T09:00:00Z' },
    { ticker: 'BBB', quantity: 4, market_value: 200, current_price: 50, target_allocation: null, sector: 'Unclassified', price_source: 'stored_quote', price_as_of: null },
  ] };
beforeEach(() => {
  mocks.put.mockReset().mockResolvedValue({}); mocks.load.mockReset().mockResolvedValue({});
  mocks.snapshot = { data, load: mocks.load, loading: false, error: null };
});
describe('PortfolioWorkspace', () => {
  it('validates allocations, saves the plan, and refreshes the snapshot', async () => {
    render(<PortfolioWorkspace planning />);
    const input = screen.getByLabelText('Target allocation for AAA');
    fireEvent.change(input, { target: { value: '50' } });
    expect(screen.getByRole('button', { name: 'Save targets' })).toBeDisabled();
    fireEvent.change(screen.getByLabelText('Target allocation for BBB'), { target: { value: '30' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save targets' }));
    await screen.findByText('Allocation targets saved.');
    expect(mocks.put).toHaveBeenCalledWith('/portfolios/targets', { weights: { AAA: 50, BBB: 30, CASH: 20 } });
    await waitFor(() => expect(mocks.load).toHaveBeenCalledWith({ force: true }));
  });
  it('retains the snapshot during refresh errors and offers price refresh', () => {
    mocks.snapshot.error = 'Provider unavailable';
    render(<PortfolioWorkspace />);
    expect(screen.getByText('$1000.00')).toBeInTheDocument();
    expect(screen.getByRole('alert')).toHaveTextContent('Provider unavailable');
    fireEvent.click(screen.getByRole('button', { name: 'Refresh prices' }));
    expect(mocks.load).toHaveBeenCalledWith({ refreshPrices: true });
  });
  it('shows retry when no valuation is available', () => {
    mocks.snapshot.data = null; mocks.snapshot.error = 'Unavailable';
    render(<PortfolioWorkspace />);
    fireEvent.click(screen.getByRole('button', { name: 'Retry portfolio' }));
    expect(mocks.load).toHaveBeenCalledWith({ force: true });
  });
});
