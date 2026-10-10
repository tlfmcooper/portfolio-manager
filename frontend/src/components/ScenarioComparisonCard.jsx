import React, { useState } from 'react';
import { usePortfolioScenario } from '../contexts/PortfolioScenarioContext';
import { validTargets } from '../utils/portfolioPlanning';

export default function ScenarioComparisonCard({ data }) {
  const scenario = usePortfolioScenario();
  const context = data.analysis_context;
  const [weights, setWeights] = useState(context.weights);
  const [message, setMessage] = useState(null);
  const selected = data.analytics?.metrics || {};
  const baseline = data.baseline_metrics || {};
  const total = Object.values(weights).reduce((sum, value) => sum + Number(value), 0);
  const metrics = [['Annualized return', 'portfolio_return_annualized', true], ['Annualized volatility', 'portfolio_volatility_annualized', true], ['Sharpe ratio', 'sharpe_ratio', false]];
  const format = (value, percent) => typeof value === 'number' ? `${(value * (percent ? 100 : 1)).toFixed(2)}${percent ? '%' : ''}` : 'Unavailable';
  return <section aria-label="Allocation scenario proposal" className="mt-3 rounded-lg border p-3 text-xs space-y-3" style={{ borderColor: 'var(--color-border)' }}>
    <h4 className="font-semibold">Editable allocation scenario</h4>
    <p>Historical coverage: {context.coverage_percentage.toFixed(1)}%. Changing this draft updates dashboard analytics when applied.</p>
    <table className="w-full"><thead><tr><th className="text-left">Metric</th><th>Actual</th><th>Proposed</th></tr></thead><tbody>{metrics.map(([label, key, percent]) => <tr key={key}><th className="text-left font-normal py-1">{label}</th><td className="text-right">{format(baseline[key], percent)}</td><td className="text-right">{format(selected[key], percent)}</td></tr>)}</tbody></table>
    <div className="grid grid-cols-2 gap-2">{Object.entries(weights).map(([ticker, weight]) => <label key={ticker}>{ticker} %<input aria-label={`Proposed allocation for ${ticker}`} type="number" min="0" max="100" step="any" value={weight} onChange={e => { setWeights(prev => ({ ...prev, [ticker]: e.target.value })); setMessage('Draft changed; comparison above describes the original proposal. Apply to recalculate.'); }} className="mt-1 block rounded border p-1 w-full" style={{ backgroundColor: 'var(--color-surface)', borderColor: 'var(--color-border)' }} /></label>)}</div>
    <p>Total: {total.toFixed(2)}%</p>
    <div className="flex gap-2"><button type="button" disabled={!scenario || !validTargets(weights)} onClick={() => { try { scenario.applyWeights(weights); setMessage('Applied to all dashboard analytics. Actual holdings are unchanged.'); } catch (error) { setMessage(error.message); } }} className="rounded border p-2 disabled:opacity-50">Apply what-if weights</button><button type="button" onClick={() => { scenario?.reset(); setMessage('Analytics reset to actual weights.'); }} className="rounded border p-2">Reset to actual</button></div>
    {message && <p role="status">{message}</p>}
    {Object.entries(data.analytics || {}).filter(([, result]) => result.error).map(([kind, result]) => <p key={kind}>{kind}: {result.error}</p>)}
    {context.notes.map(note => <p key={note}>{note}</p>)}
  </section>;
}
