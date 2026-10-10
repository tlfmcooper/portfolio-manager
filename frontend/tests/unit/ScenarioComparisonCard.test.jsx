import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import ScenarioComparisonCard from '../../src/components/ScenarioComparisonCard';
const mocks = vi.hoisted(() => ({ applyWeights: vi.fn(), reset: vi.fn() }));
vi.mock('../../src/contexts/PortfolioScenarioContext', () => ({ usePortfolioScenario: () => mocks }));
const data = { analysis_context: { weights: { AAA: 80, CASH: 20 }, coverage_percentage: 100, notes: [] },
  analytics: { metrics: { portfolio_return_annualized: .1, portfolio_volatility_annualized: .2, sharpe_ratio: 2 } },
  baseline_metrics: { portfolio_return_annualized: .05, portfolio_volatility_annualized: .3, sharpe_ratio: 1 } };
beforeEach(() => { mocks.applyWeights.mockClear(); mocks.reset.mockClear(); });
it('shows calculated comparisons and validates editable proposals before applying or resetting', () => {
  render(<ScenarioComparisonCard data={data} />);
  expect(screen.getByText('10.00%')).toBeInTheDocument();
  expect(screen.getByText('5.00%')).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('Proposed allocation for AAA'), { target: { value: '70' } });
  expect(screen.getByRole('button', { name: 'Apply what-if weights' })).toBeDisabled();
  fireEvent.change(screen.getByLabelText('Proposed allocation for CASH'), { target: { value: '30' } });
  fireEvent.click(screen.getByRole('button', { name: 'Apply what-if weights' }));
  expect(mocks.applyWeights).toHaveBeenCalledWith({ AAA: '70', CASH: '30' });
  fireEvent.click(screen.getByRole('button', { name: 'Reset to actual' }));
  expect(mocks.reset).toHaveBeenCalledTimes(1);
});
