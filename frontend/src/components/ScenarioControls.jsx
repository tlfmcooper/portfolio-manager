import React from 'react';
import { Link } from 'react-router-dom';
import { usePortfolioScenario } from '../contexts/PortfolioScenarioContext';
import ScenarioComparisonCard from './ScenarioComparisonCard';

export default function ScenarioControls() {
  const scenario = usePortfolioScenario();
  if (!scenario?.snapshot) return null;
  const { mode, activeMode, busy, error, reset, selectMSR, valid, coverage } = scenario;
  const style = { backgroundColor: 'var(--color-surface)', color: 'var(--color-text)', borderColor: 'var(--color-border)' };
  return <section aria-label="Analytics weight scenario" className="rounded-xl border p-4 mb-5 space-y-2" style={style}>
    <div className="flex flex-wrap gap-3 items-center justify-between">
      <div><p className="font-semibold">Analytics weights: {activeMode === 'current' ? 'Current portfolio' : activeMode === 'msr' ? 'Maximum Sharpe ratio' : 'Custom targets'}</p>
        <p className="text-xs mt-1" style={{ color: 'var(--color-text-secondary)' }}>What-if analysis • Actual holdings and account balances stay unchanged</p></div>
      <div className="flex flex-wrap gap-2">
        <button type="button" aria-pressed={mode === 'current'} onClick={scenario.resetWeights} className="rounded border px-3 py-2 text-sm" style={style}>Use current weights</button>
        <button type="button" aria-pressed={mode === 'msr'} disabled={busy} onClick={() => selectMSR().catch(() => {})} className="rounded border px-3 py-2 text-sm disabled:opacity-50" style={mode === 'msr' ? { ...style, borderColor: 'var(--color-primary)' } : style}>{busy ? 'Calculating MSR…' : 'Use MSR weights'}</button>
        <Link to="/dashboard/portfolio#allocation-planner" className="rounded border px-3 py-2 text-sm" style={style}>Edit target weights</Link>
        <button type="button" onClick={reset} className="rounded px-3 py-2 text-sm" style={{ backgroundColor: 'var(--color-primary)', color: 'var(--color-btn-primary-text)' }}>Reset all analytics</button>
      </div>
    </div>
    <p className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>MSR optimizes investments with sufficient history, preserves cash, and keeps unavailable holdings fixed.</p>
    {!valid && <p role="status" className="text-sm">Targets must total 100%. Charts retain the last valid allocation while you edit.</p>}
    {error && <p role="alert" className="text-sm">{error}</p>}
    {scenario.mcpProposal && <div><ScenarioComparisonCard data={scenario.mcpProposal} /><button type="button" className="text-xs underline mt-2" onClick={scenario.dismissProposal}>Dismiss proposal</button></div>}
    {coverage && <p className="text-xs">History coverage: {coverage.coverage_percentage.toFixed(1)}% • {coverage.observations} common observations{coverage.holdings.filter(h => !h.available && h.weight_percentage > 0).length > 0 ? ` • Missing: ${coverage.holdings.filter(h => !h.available && h.weight_percentage > 0).map(h => h.ticker).join(', ')}` : ''}</p>}
  </section>;
}
