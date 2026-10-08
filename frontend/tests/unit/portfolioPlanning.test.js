import { describe, expect, it } from 'vitest';
import { concentrationInsights, currentTargets, rebalancePreview, validTargets } from '../../src/utils/portfolioPlanning';

const snapshot = { total_value: 1000, cash_balance: 200, holdings: [
  { ticker: 'AAA', market_value: 600, current_price: 100, price_source: 'stored_quote', price_as_of: '2026-10-08', sector: 'Technology' },
  { ticker: 'BBB', market_value: 200, current_price: 50, price_source: 'cost_basis_estimate', sector: 'Unclassified' },
] };

describe('portfolio planning calculations', () => {
  it('balances purchases, sales, contribution and the cash reserve', () => {
    const rows = rebalancePreview(snapshot, { AAA: 40, BBB: 40, CASH: 20 }, 500);
    expect(rows[0].difference).toBe(0);
    expect(rows[1].difference).toBe(400);
    const buyTotal = rows.filter(r => r.ticker !== 'CASH').reduce((sum, r) => sum + r.difference, 0);
    expect(snapshot.cash_balance + 500 - buyTotal).toBe(300);
    expect(rows[1].units).toBeNull();
    expect(rows[0].outsideBand).toBe(true);
  });
  it('rejects invalid plans and negative or nonfinite contributions', () => {
    expect(validTargets({ AAA: 80, CASH: 30 })).toBe(false);
    expect(validTargets({ AAA: 80, CASH: 20.01 })).toBe(false);
    expect(validTargets({ AAA: '', CASH: 100 })).toBe(false);
    expect(validTargets({ AAA: NaN, CASH: 100 })).toBe(false);
    expect(rebalancePreview(snapshot, { AAA: 80, CASH: 20 }, -100)).toEqual([]);
    expect(rebalancePreview(snapshot, { AAA: 80, CASH: 20 }, Infinity)).toEqual([]);
  });
  it('handles empty portfolios and conserves target rounding', () => {
    expect(currentTargets({ total_value: 0, cash_balance: 0, holdings: [] })).toEqual({ CASH: 100 });
    expect(validTargets(currentTargets({ total_value: 6, cash_balance: 0, holdings: Array.from({ length: 6 }, (_, i) => ({ ticker: `A${i}`, market_value: 1 })) }))).toBe(true);
  });
  it('flags concentration and missing fund exposure without inventing diversification', () => {
    const alerts = concentrationInsights(snapshot, 25);
    expect(alerts).toHaveLength(2);
    expect(alerts[0]).toContain('AAA represents 60.0%');
    expect(alerts[1]).toContain('look-through exposure is unavailable');
  });
});
