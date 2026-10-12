// The same native application runs on its own origin inside the MCP host.
// Browser credentials stay in this origin; no tokens are sent to the host.
let requestedRoute;

export function getMcpRequestedRoute() {
  return requestedRoute;
}

export function isTrustedMcpParent(origin) {
  if (['https://portfolio.alikone.dev', 'https://paios.alikone.dev', 'http://localhost:8000', 'http://127.0.0.1:8000', 'https://chatgpt.com', 'https://claude.ai'].includes(origin)) return true;
  try {
    const url = new URL(origin);
    if (url.username || url.password || url.port || url.search || url.hash || (url.pathname && url.pathname !== '/')) return false;
    const codex = url.hostname === 'web-sandbox.oaiusercontent.com' || url.hostname.endsWith('.web-sandbox.oaiusercontent.com');
    if (codex && ['https:', 'codex-sandbox:'].includes(url.protocol)) return true;
    return url.protocol === 'https:' && url.hostname.endsWith('.claudemcpcontent.com');
  } catch { return false; }
}

export function connectMcpApp(windowObject = window) {
  if (windowObject.parent === windowObject || new URLSearchParams(windowObject.location.search).get('mcpApp') !== '1') return () => {};
  if (!windowObject.location.hash) windowObject.location.hash = '/dashboard';
  let hostOrigin;
  const initializeId = 'portfolio:initialize';
  let initialized = false;
  const receive = event => {
    if (event.source !== windowObject.parent || !isTrustedMcpParent(event.origin) || (hostOrigin && event.origin !== hostOrigin)) return;
    if (event.data?.jsonrpc === '2.0' && event.data.id === initializeId && event.data.result) {
      hostOrigin = event.origin;
      initialized = true;
      windowObject.parent.postMessage({ jsonrpc: '2.0', method: 'ui/notifications/initialized' }, hostOrigin);
    }
    if (initialized && event.data?.jsonrpc === '2.0' && event.data.method === 'ui/notifications/tool-result') {
      const proposal = event.data.params?.structuredContent;
      if (proposal?.ui_type === 'allocation_scenario') windowObject.dispatchEvent(new windowObject.CustomEvent('portfolio:scenario-proposal', { detail: proposal }));
      // The analytic tool result opens the same native app as open_app. Select
      // its native chart directly instead of leaving the host to rebuild one.
      if (Array.isArray(proposal?.simulation_paths) && Number.isFinite(proposal.final_mean) && Number.isFinite(proposal.time_horizon)) {
        requestedRoute = '/dashboard/analytics?view=monte-carlo';
        windowObject.location.hash = requestedRoute;
      }
    }
  };
  windowObject.addEventListener('message', receive);
  windowObject.parent.postMessage({ jsonrpc: '2.0', id: initializeId, method: 'ui/initialize', params: {
    protocolVersion: '2026-01-26', appInfo: { name: 'Portfolio', version: '1.0.0' }, appCapabilities: {},
  } }, '*');
  return () => windowObject.removeEventListener('message', receive);
}
