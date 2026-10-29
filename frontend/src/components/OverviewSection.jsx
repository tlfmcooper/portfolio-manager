import { usePortfolioScenario } from '../contexts/PortfolioScenarioContext';
import { analysisKey, analysisParams } from '../utils/analysisKeys';
import AnalysisCoverage from './AnalysisCoverage';
import React, { useState, useEffect } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { TrendingUp, TrendingDown, DollarSign, AlertTriangle, Info } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { useCurrency } from '../contexts/CurrencyContext'
import { useDataCache } from '../contexts/DataCacheContext'
import ResponsiveChartContainer from './ResponsiveChartContainer'
import { DashboardSkeleton } from './ui/Skeleton'

const OverviewSection = () => {
  const { api, portfolioId } = useAuth() // CRITICAL FIX: Get portfolioId from context
  const { currency } = useCurrency()
  const { getFromCache, fetchWithCache, CACHE_TTL } = useDataCache()
  const scenario = usePortfolioScenario();
  const signature = scenario?.signature || 'null';
  const accountView = signature === 'null';
  const metricsKey = accountView ? `account_ytd:v1:${portfolioId}:${new Date().getFullYear()}`
    : analysisKey(portfolioId, 'metrics', analysisParams('metrics'), signature, scenario?.valuation);
  const cachedPrevious = getFromCache(metricsKey, currency, { allowStale: true });
  const [data, setData] = useState(cachedPrevious)
  const [loading, setLoading] = useState(!cachedPrevious)
  const [error, setError] = useState(null)
  const [pending, setPending] = useState(0)
  const [retryRevision, setRetryRevision] = useState(0)

  useEffect(() => {
    let active = true;
    const previous = getFromCache(metricsKey, currency, { allowStale: true });
    setData(previous);
    setError(null);
    setPending(portfolioId ? 1 : 0);
    setLoading(Boolean(portfolioId) && !previous);
    if (!portfolioId) return undefined;
    fetchWithCache(metricsKey, async () => accountView
      ? (await api.get(`/analysis/portfolios/${portfolioId}/account-performance`, { params: { currency }, timeout: 60000 })).data
      : (await api.post(`/analysis/portfolios/${portfolioId}/scenario`, { ...JSON.parse(signature), kind: 'metrics', currency }, { timeout: 60000 })).data,
      CACHE_TTL.PORTFOLIO_METRICS, currency).then(result => {
        if (!active) return;
        setData(result); setPending(0); setLoading(false);
      }).catch(err => {
        if (!active || err.response?.status === 401) return;
        // Do not substitute allocation-model ratios when account history is incomplete.
        setData(null); setPending(0); setLoading(false);
        setError(err.response?.data?.detail || 'Account performance could not be loaded. Please retry.');
      });
    return () => { active = false; };
  }, [api, portfolioId, currency, signature, accountView, metricsKey, getFromCache, fetchWithCache, CACHE_TTL, retryRevision]);

  if (loading) return <DashboardSkeleton />
  if (error && !data) return <div role="alert" className="space-y-3">
    <p className="text-red-500">{error}</p>
    <button type="button" className="btn btn-primary" onClick={() => setRetryRevision(value => value + 1)}>Retry account performance</button>
  </div>
  if (!data) return null

  const performanceMetrics = data || {}
  const individualPerformance = data.individual_performance || {}

  const formatPercentage = (value) => {
    if (typeof value !== 'number') return 'N/A'
    return `${value >= 0 ? '+' : ''}${(value * 100).toFixed(2)}%`
  }

  const formatPercentagePoints = (value) => {
    if (typeof value !== 'number') return 'N/A'
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
  }

  const formatRatio = (value) => {
    if (typeof value !== 'number') return 'N/A'
    return value.toFixed(3)
  }

  const getMetricStatus = (metric, value) => {
    if (typeof value !== 'number') return 'neutral'
    
    switch (metric) {
      case 'ytd_return_percentage':
      case 'portfolio_return_annualized':
      case 'sharpe_ratio':
      case 'sortino_ratio':
      case 'calmar_ratio':
        return value > 0 ? 'positive' : 'negative'
      case 'max_drawdown':
        return value > -0.15 ? 'positive' : value > -0.25 ? 'warning' : 'negative'
      case 'portfolio_volatility_annualized':
        return value < 0.15 ? 'positive' : value < 0.25 ? 'warning' : 'negative'
      default:
        return 'neutral'
    }
  }

  const getStatusColor = (status) => {
    // This function is no longer needed since we use CSS classes
    // but keeping it for backwards compatibility
    return '';
  }

  const getStatusText = (metric, value) => {
    if (typeof value !== 'number') return 'No Data'
    
    switch (metric) {
      case 'ytd_return_percentage':
        return value > 15 ? 'Excellent Performance' : value > 8 ? 'Good Performance' : 'Below Average'
      case 'portfolio_return_annualized':
        return value > 0.15 ? 'Excellent Performance' : value > 0.08 ? 'Good Performance' : 'Below Average'
      case 'portfolio_volatility_annualized':
        return value < 0.15 ? 'Low Risk' : value < 0.25 ? 'Moderate Risk' : 'High Risk'
      case 'sharpe_ratio':
        return value > 1.5 ? 'Excellent Risk-Adj Return' : value > 1.0 ? 'Good Risk-Adj Return' : 'Poor Risk-Adj Return'
      case 'sortino_ratio':
        return value > 2 ? 'Strong Downside-Adj Return' : value > 1 ? 'Good Downside-Adj Return' : 'Poor Downside-Adj Return'
      case 'calmar_ratio':
        return value > 2 ? 'Strong Return / Drawdown' : value > 1 ? 'Good Return / Drawdown' : 'Low Return / Drawdown'
      case 'max_drawdown':
        return value > -0.10 ? 'Well Controlled' : value > -0.20 ? 'Acceptable' : 'High Drawdown'
      default:
        return 'Standard'
    }
  }

  // Dynamic tooltip generator based on metric values
  const getMetricTooltip = (key, value) => {
    if (typeof value !== 'number') return 'No data available for this metric.'
    
    switch (key) {
      case 'ytd_return_percentage':
        return `Year-to-date time-weighted account return, with external cash flows removed using an end-of-day convention. A return of ${value.toFixed(2)}% is considered ${value >= 15 ? 'excellent' : value >= 8 ? 'strong' : value >= 5 ? 'moderate' : 'modest'} performance.`

      case 'portfolio_return_annualized':
        if (accountView) return 'Geometric annualized account return, calculated from the same cash-flow-adjusted daily returns as YTD performance. Annualization is not a forecast.';
        return `Geometric return for today's modeled allocation over the common historical period, scaled to a year using 252 trading observations. This is not the account's realized annual or YTD return. Calmar divides this return by maximum drawdown; Sharpe and Sortino compare modeled returns with the risk-free rate.`
      
      case 'portfolio_volatility_annualized':
        return `Annual volatility measures the portfolio's price fluctuations. ${(value * 100).toFixed(2)}% volatility is ${value <= 0.10 ? 'low' : value <= 0.20 ? 'moderate' : 'high'} and ${value <= 0.20 ? 'appropriate' : 'elevated'} for a diversified portfolio seeking growth.`
      
      case 'sharpe_ratio':
        let sharpeInterpretation = value < 1.0 ? 'sub-optimal or poor' : value < 2.0 ? 'acceptable/good' : value < 3.0 ? 'very good' : 'excellent'
        return `The Sharpe ratio measures risk-adjusted returns by comparing excess returns to volatility. Values above 1.0 are good, above 2.0 are very good. Your ${value.toFixed(2)} ratio indicates ${sharpeInterpretation} risk-adjusted performance.`
      
      case 'sortino_ratio':
        let sortinoInterpretation = value < 1.0 ? 'modest' : value < 2.0 ? 'strong' : value < 3.0 ? 'very strong' : 'excellent'
        return `The Sortino ratio focuses on downside volatility, providing a better measure of risk-adjusted returns than Sharpe. A ratio of ${value.toFixed(2)} indicates ${sortinoInterpretation} performance with ${value >= 2.0 ? 'excellent' : value >= 1.0 ? 'good' : 'limited'} downside protection.`
      
      case 'max_drawdown':
        let drawdownInterpretation = Math.abs(value) < 0.10 ? 'relatively modest' : Math.abs(value) < 0.20 ? 'moderate' : Math.abs(value) < 0.30 ? 'significant' : 'substantial'
        return `Maximum drawdown shows the largest peak-to-trough decline. A ${(value * 100).toFixed(2)}% drawdown is ${drawdownInterpretation} and indicates ${Math.abs(value) < 0.15 ? 'good' : Math.abs(value) < 0.25 ? 'adequate' : 'challenging'} risk management through diversification.`
      
      case 'calmar_ratio':
        let calmarInterpretation = value < 1.0 ? 'modest' : value < 2.0 ? 'strong' : value < 3.0 ? 'very strong' : 'excellent'
        return `The Calmar ratio compares annual return to maximum drawdown. A ratio of ${value.toFixed(2)} indicates ${calmarInterpretation} returns relative to maximum loss, showing ${value >= 2.0 ? 'excellent' : value >= 1.0 ? 'effective' : 'basic'} risk management.`
      
      default:
        return 'Portfolio metric for analysis.'
    }
  }

  const metrics = [
    {
      key: 'ytd_return_percentage',
      label: 'YTD Return',
      value: performanceMetrics.ytd_return_percentage,
      formatter: formatPercentagePoints,
      tooltip: performanceMetrics.ytd_message,
    },
    {
      key: 'portfolio_return_annualized',
      label: accountView ? 'Account Annualized Return' : 'Modeled Annualized Return',
      value: performanceMetrics.portfolio_return_annualized,
      formatter: formatPercentage,
    },
    {
      key: 'portfolio_volatility_annualized',
      label: 'Annual Volatility',
      value: performanceMetrics.portfolio_volatility_annualized,
      formatter: formatPercentage,
    },
    {
      key: 'sharpe_ratio',
      label: 'Sharpe Ratio',
      value: performanceMetrics.sharpe_ratio,
      formatter: formatRatio,
    },
    {
      key: 'sortino_ratio',
      label: 'Sortino Ratio',
      value: performanceMetrics.sortino_ratio,
      formatter: formatRatio,
    },
    {
      key: 'max_drawdown',
      label: 'Maximum Drawdown',
      value: performanceMetrics.max_drawdown,
      formatter: formatPercentage,
    },
    {
      key: 'calmar_ratio',
      label: 'Calmar Ratio',
      value: performanceMetrics.calmar_ratio,
      formatter: formatRatio,
    }
  ].filter(metric => accountView || metric.key !== 'ytd_return_percentage')

  // Prepare chart data for individual performance
  const chartData = Object.entries(individualPerformance).map(([symbol, perf]) => ({
    symbol,
    return: (perf.return * 100) || 0,
    volatility: (perf.volatility * 100) || 0
  }))

  return (
    <div className="space-y-8">
      <AnalysisCoverage context={data?.analysis_context} />
      <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
        {accountView
          ? 'YTD return and all risk metrics use the same account history, including recorded trades, deposits and withdrawals. Values end at the last completed market session.'
          : "Allocation scenario: returns and risk ratios model today's selected weights over the historical period shown above."}
        {typeof data?.analysis_context?.risk_free_rate === 'number' && ` Sharpe and Sortino use a ${(data.analysis_context.risk_free_rate * 100).toFixed(2)}% annual risk-free rate.`}
      </p>
      {pending > 0 && <p role="status" className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>Loading remaining analytics…</p>}
      {error && <p role="alert" className="text-sm" style={{ color: 'var(--color-warning)' }}>{error}</p>}
      <div>
        {/* Metrics Grid */}
        <div className="metrics-grid">
          {metrics.map((metric) => {
            const status = getMetricStatus(metric.key, metric.value)
            const statusText = getStatusText(metric.key, metric.value)
            const tooltip = metric.tooltip || getMetricTooltip(metric.key, metric.value)
            
            return (
              <div 
                key={metric.key}
                className={`metric-card ${status}`}
                data-tooltip={tooltip}
              >
                <div className="metric-header">
                  <span className="metric-label">
                    {metric.label}
                  </span>
                  <span className="info-icon">ℹ️</span>
                </div>
                <div className="metric-value">
                  {metric.formatter(metric.value)}
                </div>
                <div className={`metric-status ${status}`}>
                  {statusText}
                </div>
              </div>
            )
          })}
        </div>

        {/* Performance Chart */}
        {chartData.length > 0 && (
          <div className="chart-container">
            <h3 style={{
              fontSize: 'var(--font-size-xl)',
              marginBottom: 'var(--space-20)',
              color: 'var(--color-text)'
            }}>
              Performance Distribution
            </h3>
            <ResponsiveChartContainer height={300} mobileHeight={250}>
              <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }} barSize={20} barGap={3}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.2} />
                <XAxis
                  dataKey="symbol"
                  tick={{ fontSize: 12, fill: '#6B7280' }}
                  stroke="#6B7280"
                />
                <YAxis
                  tick={{ fontSize: 12, fill: '#6B7280' }}
                  stroke="#6B7280"
                  label={{ value: 'Percentage (%)', angle: -90, position: 'insideLeft' }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'var(--color-charcoal-800)',
                    border: '1px solid var(--color-border)',
                    borderRadius: 'var(--radius-base)',
                    color: 'var(--color-white)'
                  }}
                  formatter={(value, name) => [
                    `${value.toFixed(2)}%`,
                    name === 'return' ? 'Annual Return' : 'Volatility'
                  ]}
                />
                <Bar isAnimationActive={false}
                  dataKey="return"
                  fill="var(--color-primary)"
                  name="return"
                  radius={[2, 2, 0, 0]}
                />
                <Bar isAnimationActive={false}
                  dataKey="volatility"
                  fill="var(--color-warning)"
                  name="volatility"
                  radius={[2, 2, 0, 0]}
                />
              </BarChart>
            </ResponsiveChartContainer>
          </div>
        )}
      </div>
    </div>
  )
}

export default OverviewSection
