import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Download, RefreshCw, Target } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useCurrency } from '../contexts/CurrencyContext';
import { useDataCache } from '../contexts/DataCacheContext';
import { usePortfolioSnapshot } from '../hooks/usePortfolioSnapshot';
import { concentrationInsights, currentTargets, rebalancePreview, savedTargets, validTargets } from '../utils/portfolioPlanning';

const card = { backgroundColor: 'var(--color-surface)', borderColor: 'var(--color-border)', color: 'var(--color-text)' };
const button = { backgroundColor: 'var(--color-primary)', color: 'var(--color-btn-primary-text)' };

function AllocationPlanner({ data, onSaved }) {
  const { api } = useAuth();
  const { formatCurrency } = useCurrency();
  const [weights, setWeights] = useState(() => savedTargets(data) || currentTargets(data));
  const [contribution, setContribution] = useState('0');
  const [band, setBand] = useState(5);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);
  const [saveError, setSaveError] = useState(null);
  useEffect(() => { setContribution('0'); }, [data.currency]);
  const latestSnapshot = useRef(data);
  latestSnapshot.current = data;
  const signature = data.holdings.map(h => `${h.ticker}:${h.target_allocation ?? ''}`).join('|');
  // Refresh saved plans when they change, while preserving a draft through quote updates.
  useEffect(() => { setWeights(savedTargets(latestSnapshot.current) || currentTargets(latestSnapshot.current)); }, [signature]);
  const total = Object.values(weights).reduce((sum, value) => sum + Number(value), 0);
  const valid = validTargets(weights) && contribution !== '' && Number.isFinite(Number(contribution)) && Number(contribution) >= 0;
  const rows = useMemo(() => rebalancePreview(data, weights, Number(contribution), Number(band)), [data, weights, contribution, band]);
  const holdings = [...data.holdings, { ticker: 'CASH', name: 'Cash reserve', market_value: data.cash_balance }];
  const money = value => formatCurrency(value);
  const save = async () => {
    setSaving(true); setMessage(null); setSaveError(null);
    try {
      await api.put('/portfolios/targets', { weights: Object.fromEntries(Object.entries(weights).map(([ticker, weight]) => [ticker, Number(weight)])) });
      setMessage('Allocation targets saved.');
      await onSaved();
    } catch (error) { setSaveError(error.response?.data?.detail && typeof error.response.data.detail === 'string' ? error.response.data.detail : 'Could not save targets. Please retry.'); }
    finally { setSaving(false); }
  };
  return <section className="rounded-xl border p-[16px] sm:p-[24px] space-y-4" style={card} aria-label="Allocation planning">
    <div className="flex items-center gap-2"><Target className="h-5 w-5" /><h3 className="text-lg font-semibold">Allocation targets & rebalancing</h3></div>
    <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>Set a plan for your holdings and cash. Preview amounts using stored prices; trades are entered separately in Update Portfolio.</p>
    <div className="flex flex-wrap gap-4 items-end">
      <label className="text-sm">Planned contribution ({data.currency})<input type="number" min="0" step="0.01" value={contribution} onChange={e => setContribution(e.target.value)} className="block mt-1 rounded border p-2" style={{ ...card, width: 192, height: 40, fontSize: 16 }} /></label>
      <label className="text-sm">Drift threshold (percentage points)<input type="number" min="0.1" max="100" step="0.1" value={band} onChange={e => setBand(Math.max(0.1, Math.min(100, Number(e.target.value) || 5)))} className="block mt-1 rounded border p-2" style={{ ...card, width: 128, height: 40, fontSize: 16 }} /></label>
      <button type="button" className="rounded border px-3 py-2 text-sm" style={card} onClick={() => { setWeights(currentTargets(data)); setMessage(null); }}>Use current weights</button>
    </div>
    <p className="sm:hidden text-xs" style={{ color: 'var(--color-text-secondary)' }}>Scroll the table to see all preview columns.</p>
    <div className="overflow-x-auto" tabIndex={0} role="region" aria-label="Rebalancing table"><table className="w-full min-w-[680px] text-sm text-left">
      <caption className="sr-only">Target allocations and estimated rebalancing amounts</caption>
      <thead><tr className="border-b" style={{ borderColor: 'var(--color-border)' }}><th className="py-3 pr-4">Holding</th><th className="pr-4">Current</th><th className="pr-4">Target %</th><th className="pr-4">Drift</th><th className="pr-4">Preview amount</th><th>Approx. units</th></tr></thead>
      <tbody>{holdings.map(h => {
        const row = rows.find(r => r.ticker === h.ticker);
        return <tr key={h.ticker} className="border-b" style={{ borderColor: 'var(--color-border)' }}>
          <th scope="row" className="py-3 pr-4 whitespace-nowrap">{h.ticker}</th>
          <td className="pr-4">{data.total_value > 0 ? (h.market_value / data.total_value * 100).toFixed(1) : '0.0'}%</td>
          <td className="pr-4"><input aria-label={`Target allocation for ${h.ticker}`} type="number" min="0" max="100" step="0.01" value={weights[h.ticker] ?? 0} onChange={e => { setWeights(prev => ({ ...prev, [h.ticker]: e.target.value })); setMessage(null); }} className="rounded border p-2" style={{ ...card, width: 96, height: 40, fontSize: 16 }} /></td>
          <td className="pr-4 whitespace-nowrap" style={{ color: row?.outsideBand ? 'var(--color-warning)' : undefined }}>{row ? `${row.drift >= 0 ? '+' : ''}${row.drift.toFixed(1)} pp${row.outsideBand ? ' • Review' : ''}` : '—'}</td>
          <td className="pr-4 whitespace-nowrap">{row ? `${h.ticker === 'CASH' ? 'Reserve' : row.difference >= 0 ? 'Buy' : 'Sell'} ${money(h.ticker === 'CASH' ? (data.total_value + Number(contribution)) * row.targetWeight / 100 : Math.abs(row.difference))}` : '—'}</td>
          <td>{row?.units !== null && row?.units !== undefined ? Math.abs(row.units).toFixed(4) : '—'}</td>
        </tr>;
      })}</tbody>
    </table></div>
    <div className="flex flex-wrap items-center gap-4"><p className="text-sm" role="status">Targets total: {Number.isFinite(total) ? total.toFixed(2) : '—'}%{!validTargets(weights) ? ' — enter percentages totaling 100%.' : ''}</p><button type="button" disabled={!valid || saving} onClick={save} className="rounded px-4 py-2 text-sm font-semibold disabled:opacity-50" style={button}>{saving ? 'Saving…' : 'Save targets'}</button></div>
    {message && <p role="status" className="text-sm">{message}</p>}{saveError && <p role="alert" className="text-sm" style={{ color: 'var(--color-error)' }}>{saveError}</p>}
    <p className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>The contribution is a preview and does not change cash. Amounts assume fractional units; fees, taxes, spreads and trading restrictions are excluded. Estimates and quotes without a timestamp have no unit preview.</p>
  </section>;
}

export default function PortfolioWorkspace({ planning = false }) {
  const { data, loading, error, load } = usePortfolioSnapshot();
  const { api } = useAuth();
  const { formatCurrency } = useCurrency();
  const { invalidateCache } = useDataCache();
  const [limit, setLimit] = useState(25);
  const [exporting, setExporting] = useState(null);
  const [exportError, setExportError] = useState(null);
  const download = async kind => {
    setExporting(kind); setExportError(null);
    try {
      const response = await api.get('/portfolios/export', { params: { kind, currency: data.currency }, responseType: 'blob', timeout: 10000 });
      const url = URL.createObjectURL(response.data);
      const anchor = document.createElement('a'); anchor.href = url; anchor.download = `portfolio-${kind}.csv`;
      document.body.appendChild(anchor); anchor.click(); anchor.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch { setExportError('Could not export portfolio. Please retry.'); }
    finally { setExporting(null); }
  };
  if (!data) return <section className="rounded-xl border p-6" style={card} aria-busy={loading}>{error ? <><p role="alert">{error}</p><button type="button" className="mt-3 rounded px-3 py-2" style={button} onClick={() => load({ force: true })}>Retry portfolio</button></> : 'Loading portfolio snapshot…'}</section>;
  const money = value => formatCurrency(value);
  const insights = concentrationInsights(data, limit);
  const quoteDates = data.holdings.map(h => h.price_as_of).filter(Boolean).sort();
  return <div className="space-y-5 mb-6">
    <section className="rounded-xl border p-[16px] sm:p-[24px] space-y-4" style={card} aria-label="Portfolio snapshot" aria-busy={loading}>
      <div className="flex flex-wrap gap-3 justify-between items-center"><h3 className="text-lg font-semibold">Portfolio snapshot</h3><div className="flex flex-wrap gap-2">
        {planning && <><button type="button" disabled={!!exporting} onClick={() => download('holdings')} className="rounded border px-3 py-2 text-sm flex items-center gap-2" style={card}><Download className="h-[16px] w-[16px]" />{exporting === 'holdings' ? 'Exporting…' : 'Export holdings'}</button><button type="button" disabled={!!exporting} onClick={() => download('transactions')} className="rounded border px-3 py-2 text-sm" style={card}>{exporting === 'transactions' ? 'Exporting…' : 'Export transactions'}</button></>}
        <button type="button" disabled={loading} onClick={() => load({ refreshPrices: true })} className="rounded px-3 py-2 text-sm flex items-center gap-2 disabled:opacity-50" style={button}><RefreshCw className={`h-[16px] w-[16px] ${loading ? 'animate-spin' : ''}`} />{loading ? 'Updating…' : 'Refresh prices'}</button>
      </div></div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-[16px]">{[['Total portfolio value', data.total_value], ['Invested value', data.holdings_value], ['Cash reserve', data.cash_balance], ['Unrealized gain / loss', data.unrealized_gain_loss]].map(([label, value]) => <div key={label}><p className="text-xs sm:text-sm" style={{ color: 'var(--color-text-secondary)' }}>{label}</p><p className="text-lg sm:text-2xl font-semibold mt-1 break-words">{money(value)}</p></div>)}</div>
      <p className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>Stored prices • Snapshot {new Date(data.generated_at).toLocaleString()}{quoteDates.length ? ` • Oldest recorded quote ${new Date(quoteDates[0]).toLocaleString()}` : ' • Quote dates unavailable'}{data.holdings.some(h => !h.price_as_of && h.price_source !== 'cost_basis_estimate') && quoteDates.length ? ' • Some quote dates unavailable' : ''}{data.estimated_prices ? ` • ${data.estimated_prices} holding(s) valued at cost` : ''}</p>
      {error && <p role="alert" className="text-sm" style={{ color: 'var(--color-error)' }}>{error}</p>}{exportError && <p role="alert">{exportError}</p>}
    </section>
    {planning && <><section className="rounded-xl border p-[16px] sm:p-[24px] space-y-3" style={card} aria-label="Concentration checks"><div className="flex flex-wrap justify-between items-center gap-3"><h3 className="text-lg font-semibold">Concentration checks</h3><label className="text-sm">Review positions above <input aria-label="Concentration threshold" type="number" min="1" max="100" value={limit} onChange={e => setLimit(Math.max(1, Math.min(100, Number(e.target.value) || 25)))} className="rounded border p-1" style={{ ...card, width: 64, height: 36, fontSize: 16 }} /> %</label></div>{insights.length ? <ul className="list-disc pl-5 text-sm space-y-2">{insights.map(message => <li key={message}>{message}</li>)}</ul> : <p className="text-sm">No individual holding exceeds your review threshold.</p>}<p className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>Position-level checks include cash in the total and do not measure exposure inside funds.</p></section><AllocationPlanner key={data.portfolio_id} data={data} onSaved={async () => { invalidateCache(['portfolio_snapshot', 'holdings']); await load({ force: true }); }} /></>}
  </div>;
}
