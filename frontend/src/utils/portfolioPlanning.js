export function currentTargets(snapshot) {
  const weights = Object.fromEntries(snapshot.holdings.map(h => [h.ticker,
    snapshot.total_value > 0 ? Math.round(h.market_value / snapshot.total_value * 10000) / 100 : 0]));
  // Cash absorbs display-rounding differences so the saved plan totals exactly 100.
  const remaining = Math.round((100 - Object.values(weights).reduce((a, b) => a + b, 0)) * 100) / 100;
  weights.CASH = Math.max(0, remaining);
  if (remaining < 0 && snapshot.cash_balance >= 0) {
    const largest = Object.keys(weights).filter(key => key !== 'CASH').sort((a, b) => weights[b] - weights[a])[0];
    if (largest) weights[largest] = Math.round((weights[largest] + remaining) * 100) / 100;
  }
  return weights;
}

export function savedTargets(snapshot) {
  if (!snapshot.holdings.some(h => h.target_allocation !== null && h.target_allocation !== undefined)) return null;
  const weights = Object.fromEntries(snapshot.holdings.map(h => [h.ticker, h.target_allocation ?? 0]));
  weights.CASH = Math.max(0, 100 - Object.values(weights).reduce((a, b) => a + b, 0));
  return weights;
}

export function validTargets(weights) {
  const values = Object.values(weights).map(Number);
  return Object.values(weights).every(value => value !== '') && values.length > 0 && values.every(v => Number.isFinite(v) && v >= 0 && v <= 100)
    && Math.abs(values.reduce((a, b) => a + b, 0) - 100) <= 1e-6;
}

export function rebalancePreview(snapshot, weights, contribution = 0, band = 5) {
  if (!validTargets(weights) || !Number.isFinite(contribution) || contribution < 0 || snapshot.total_value + contribution <= 0) return [];
  const total = snapshot.total_value + contribution;
  const rows = [...snapshot.holdings, { ticker: 'CASH', name: 'Cash reserve', market_value: snapshot.cash_balance, current_price: null }];
  return rows.map(h => {
    const actualWeight = snapshot.total_value > 0 ? h.market_value / snapshot.total_value * 100 : 0;
    const targetWeight = Number(weights[h.ticker] ?? 0);
    const difference = total * targetWeight / 100 - h.market_value;
    return { ...h, actualWeight, targetWeight, drift: actualWeight - targetWeight,
      difference, outsideBand: Math.abs(actualWeight - targetWeight) >= band,
      units: h.ticker !== 'CASH' && h.current_price > 0 && h.price_source === 'stored_quote' && h.price_as_of ? difference / h.current_price : null };
  });
}

export function concentrationInsights(snapshot, limit = 25) {
  if (snapshot.total_value <= 0) return [];
  const messages = [];
  for (const holding of snapshot.holdings) {
    const weight = holding.market_value / snapshot.total_value * 100;
    if (weight > limit) messages.push(`${holding.ticker} represents ${weight.toFixed(1)}% of your portfolio, above your ${limit}% review threshold.`);
  }
  const unknown = snapshot.holdings.filter(h => h.sector === 'Unclassified').reduce((sum, h) => sum + h.market_value, 0);
  if (unknown > 0) messages.push(`${(unknown / snapshot.total_value * 100).toFixed(1)}% has no sector classification. Fund holdings may overlap; look-through exposure is unavailable.`);
  return messages;
}
