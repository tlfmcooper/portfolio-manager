import { describe, expect, it, vi } from 'vitest';
import { connectMcpApp } from '../../src/mcp-app';

describe('MCP scenario results', () => {
  it('only forwards initialized tool results from the trusted parent', () => {
    let receive;
    const parent = { postMessage: vi.fn() };
    const target = { parent, location: { search: '?mcpApp=1' }, CustomEvent,
      addEventListener: (_event, fn) => { receive = fn; }, removeEventListener: vi.fn(), dispatchEvent: vi.fn() };
    connectMcpApp(target);
    const data = { jsonrpc: '2.0', method: 'ui/notifications/tool-result', params: { structuredContent: { ui_type: 'allocation_scenario' } } };
    receive({ source: parent, origin: 'https://paios.alikone.dev', data });
    expect(target.dispatchEvent).not.toHaveBeenCalled();
    receive({ source: parent, origin: 'https://paios.alikone.dev', data: { jsonrpc: '2.0', id: 'portfolio:initialize', result: {} } });
    receive({ source: parent, origin: 'https://untrusted.example', data });
    expect(target.dispatchEvent).not.toHaveBeenCalled();
    receive({ source: parent, origin: 'https://paios.alikone.dev', data });
    expect(target.dispatchEvent).toHaveBeenCalledTimes(1);
    expect(target.dispatchEvent.mock.calls[0][0].type).toBe('portfolio:scenario-proposal');
  });
});
