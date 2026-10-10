import React from 'react';

export default function AnalysisCoverage({ context }) {
  if (!context) return null;
  const missing = context.holdings.filter(h => !h.available && h.weight_percentage > 0);
  return <aside aria-label="Historical data coverage" className="rounded border p-3 text-xs space-y-1" style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-secondary)' }}>
    <p>Modeled allocation: {context.coverage_percentage.toFixed(1)}% • {context.observations} common observations • {context.history_start} to {context.history_end}</p>
    {missing.length > 0 && <p role="status">Partial portfolio analysis. Excluded: {missing.map(h => `${h.ticker} (${h.weight_percentage.toFixed(1)}%: ${h.reason})`).join('; ')}. Simulations start with the covered portion of portfolio value.</p>}
    {context.notes.map(note => <p key={note}>{note}</p>)}
  </aside>;
}
