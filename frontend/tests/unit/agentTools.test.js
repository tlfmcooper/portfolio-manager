import { describe, expect, it, vi } from 'vitest';

import { executeTool } from '../../src/tools/agentTools';


describe('executeTool', () => {
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