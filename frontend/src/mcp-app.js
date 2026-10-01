// The same native application runs on its own origin inside the MCP host.
// Browser credentials stay in this origin; no tokens are sent to the host.
export function connectMcpApp(windowObject = window) {
  if (windowObject.parent === windowObject || !new URLSearchParams(windowObject.location.search).has('mcpApp')) return () => {};
  const hostOrigin = 'https://paios.alikone.dev';
  const initializeId = 'portfolio:initialize';
  const receive = event => {
    if (event.source !== windowObject.parent || event.origin !== hostOrigin) return;
    if (event.data?.jsonrpc === '2.0' && event.data.id === initializeId && event.data.result) {
      windowObject.parent.postMessage({ jsonrpc: '2.0', method: 'ui/notifications/initialized' }, hostOrigin);
    }
  };
  windowObject.addEventListener('message', receive);
  windowObject.parent.postMessage({ jsonrpc: '2.0', id: initializeId, method: 'ui/initialize', params: {
    protocolVersion: '2026-01-26', appInfo: { name: 'Portfolio', version: '1.0.0' }, appCapabilities: {},
  } }, hostOrigin);
  return () => windowObject.removeEventListener('message', receive);
}
