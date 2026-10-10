import { describe, expect, it, vi } from 'vitest';

import { executeTool } from '../../src/tools/agentTools';


describe('executeTool', () => {
  it('generates structured, editable scenario cards from calculated values', async () => {
    const scenario = { comparison: vi.fn().mockResolvedValue({
      analysis_context: { weights: { AAA: 80, CASH: 20 } }, baseline_metrics: { sharpe_ratio: 1 },
      analytics: { metrics: { sharpe_ratio: 2 }, 'monte-carlo': { final_mean: 1200, simulation_paths: [{ day: 0 }] } },
    }) };
    const result = JSON.parse(await executeTool('preview_allocation_scenario', { preset: 'custom', allocations: [
      { ticker: 'aaa', percentage: 80 }, { ticker: 'CASH', percentage: 20 },
    ] }, { scenario }));
    expect(scenario.comparison).toHaveBeenCalledWith({ AAA: 80, CASH: 20 }, 'custom');
    expect(result.ui_type).toBe('allocation_scenario');
    expect(result.analytics.metrics.sharpe_ratio).toBe(2);
    expect(result.analytics['monte-carlo'].simulation_paths).toBeUndefined();
  });
  it('resets the shared scenario through the agent', async () => {
    const scenario = { reset: vi.fn() };
    await executeTool('reset_analytics', {}, { scenario });
    expect(scenario.reset).toHaveBeenCalledTimes(1);
  });
  it('returns the portfolio summary payload with YTD fields for the chatbot', async () => {
    const api = {
      get: vi.fn().mockResolvedValue({
        data: {
          id: 1,
          name: 'My Portfolio',
          total_value: 278377.53,
          total_return: 149517.52,
          total_return_percentage: 116.06,
          ytd_return_percentage: 12.34,
          ytd_gain: 15243.21,
          ytd_complete: true,
          ytd_missing_tickers: [],
          ytd_message: null,
          currency: 'USD',
        },
      }),
    };

    const result = await executeTool('get_portfolio_summary', { currency: 'USD' }, { api });

    expect(api.get).toHaveBeenCalledWith('/portfolios/summary', { params: { currency: 'USD' } });

    const parsed = JSON.parse(result);
    expect(parsed.ytd_return_percentage).toBe(12.34);
    expect(parsed.ytd_gain).toBe(15243.21);
    expect(parsed.ytd_complete).toBe(true);
  });
});
