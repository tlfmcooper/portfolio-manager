import { describe, expect, it, vi } from 'vitest';
import { connectMcpApp } from './mcp-app';

function frame(search = '?mcpApp=1') {
  return { location: { search }, parent: { postMessage: vi.fn() }, addEventListener: vi.fn(), removeEventListener: vi.fn() };
}

describe('native MCP app connection', () => {
  it('initializes only when embedded and sends no browser credentials', () => {
    const window = frame();
    connectMcpApp(window);
    const [message, origin] = window.parent.postMessage.mock.calls[0];
    expect(message.method).toBe('ui/initialize');
    expect(origin).toBe('https://paios.alikone.dev');
    expect(JSON.stringify(message)).not.toMatch(/token|cookie|password/);
    const standalone = frame('');
    connectMcpApp(standalone);
    expect(standalone.parent.postMessage).not.toHaveBeenCalled();
  });
  it('accepts initialization only from the PAIOS parent', () => {
    const window = frame();
    const cleanup = connectMcpApp(window);
    const receive = window.addEventListener.mock.calls[0][1];
    const data = { jsonrpc: '2.0', id: 'portfolio:initialize', result: {} };
    receive({ origin: 'https://evil.test', source: window.parent, data });
    receive({ origin: 'https://paios.alikone.dev', source: {}, data });
    expect(window.parent.postMessage).toHaveBeenCalledTimes(1);
    receive({ origin: 'https://paios.alikone.dev', source: window.parent, data });
    expect(window.parent.postMessage.mock.calls[1][0].method).toBe('ui/notifications/initialized');
    cleanup();
    expect(window.removeEventListener).toHaveBeenCalledWith('message', receive);
  });
});
