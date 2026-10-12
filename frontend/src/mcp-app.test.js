import { describe, expect, it, vi } from 'vitest';
import { connectMcpApp, isTrustedMcpParent } from './mcp-app';

function frame(search = '?mcpApp=1') {
  return { location: { search }, parent: { postMessage: vi.fn() }, addEventListener: vi.fn(), removeEventListener: vi.fn() };
}

describe('native MCP app connection', () => {
  it('initializes only when embedded and sends no browser credentials', () => {
    const window = frame();
    connectMcpApp(window);
    const [message, origin] = window.parent.postMessage.mock.calls[0];
    expect(message.method).toBe('ui/initialize');
    expect(origin).toBe('*'); // Parent origin is learned from its validated response.
    expect(JSON.stringify(message)).not.toMatch(/token|cookie|password/);
    expect(window.location.hash).toBe('/dashboard');
    const standalone = frame('');
    connectMcpApp(standalone);
    expect(standalone.parent.postMessage).not.toHaveBeenCalled();
  });
  it('accepts initialization only from a trusted parent window', () => {
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
  it.each(['https://app.web-sandbox.oaiusercontent.com', 'codex-sandbox://app.web-sandbox.oaiusercontent.com', 'https://app.claudemcpcontent.com'])('connects to the MCP sandbox at %s', origin => {
    const window = frame();
    connectMcpApp(window);
    const receive = window.addEventListener.mock.calls[0][1];
    receive({ origin, source: window.parent, data: { jsonrpc: '2.0', id: 'portfolio:initialize', result: {} } });
    expect(window.parent.postMessage.mock.calls[1][1]).toBe(origin);
  });
  it.each(['https://web-sandbox.oaiusercontent.com.evil.test', 'https://evilweb-sandbox.oaiusercontent.com', 'https://user@app.web-sandbox.oaiusercontent.com', 'http://app.web-sandbox.oaiusercontent.com', 'null'])('rejects an untrusted origin %s', origin => {
    expect(isTrustedMcpParent(origin)).toBe(false);
  });
  it('pins the initialized parent origin', () => {
    const window = frame();
    connectMcpApp(window);
    const receive = window.addEventListener.mock.calls[0][1];
    const data = { jsonrpc: '2.0', id: 'portfolio:initialize', result: {} };
    receive({ origin: 'https://paios.alikone.dev', source: window.parent, data });
    receive({ origin: 'https://other.web-sandbox.oaiusercontent.com', source: window.parent, data });
    expect(window.parent.postMessage).toHaveBeenCalledTimes(2);
  });
  it('opens the native Monte Carlo view only for an initialized trusted result', () => {
    const window = frame();
    connectMcpApp(window);
    const receive = window.addEventListener.mock.calls[0][1];
    const data = { jsonrpc: '2.0', method: 'ui/notifications/tool-result', params: { structuredContent: {
      simulation_paths: [{ day: 0, mean_path: 100 }], final_mean: 120, time_horizon: 252,
    } } };
    receive({ origin: 'https://paios.alikone.dev', source: window.parent, data });
    expect(window.location.hash).toBe('/dashboard');
    receive({ origin: 'https://paios.alikone.dev', source: window.parent, data: { jsonrpc: '2.0', id: 'portfolio:initialize', result: {} } });
    receive({ origin: 'https://evil.test', source: window.parent, data });
    expect(window.location.hash).toBe('/dashboard');
    receive({ origin: 'https://paios.alikone.dev', source: window.parent, data });
    expect(window.location.hash).toBe('/dashboard/analytics?view=monte-carlo');
  });
});
