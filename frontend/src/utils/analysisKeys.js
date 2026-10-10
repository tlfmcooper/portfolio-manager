export const analysisDefaults = {
  'monte-carlo': { scenarios: 1000, time_horizon: 252 },
  cppi: { multiplier: 3, floor: 0.8, time_horizon: 252 },
};
export function analysisParams(kind, parameters = {}) {
  const params = { ...analysisDefaults[kind], ...parameters };
  delete params.currency;
  return JSON.stringify(Object.fromEntries(Object.entries(params).filter(([, value]) => value !== undefined)
    .sort(([a], [b]) => a.localeCompare(b))));
}
export function analysisKey(portfolioId, kind, serialized, signature = 'null', valuation = '') {
  if (signature !== 'null') return `portfolio_analysis:scenario:${portfolioId}:${kind}:${signature}:${serialized}:${valuation}`;
  if (kind === 'metrics') return `portfolio_metrics:${portfolioId}`;
  if (kind === 'sector-allocation') return `sector_allocation:${portfolioId}`;
  return `portfolio_analysis:${portfolioId}:${kind}:${serialized}`;
}
