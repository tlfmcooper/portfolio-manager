import React, { useState, useEffect } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { TrendingUp, TrendingDown, DollarSign, AlertTriangle, Info } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'

const OverviewSection = () => {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const { api } = useAuth()

  useEffect(() => {
    const fetchData = async () => {
      try {
        // TODO: Replace with dynamic portfolio ID
        const response = await api.get('/analysis/portfolios/1/analysis/metrics')
        console.log('API Response:', response.data)
        console.log('Individual Performance:', response.data?.individual_performance)
        setData(response.data)
      } catch (err) {
        setError('Failed to fetch overview data')
        console.error('API Error:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [api])

  if (loading) return <div>Loading...</div>
  if (error) return <div className="text-red-500">{error}</div>
  if (!data) return null

  const performanceMetrics = data || {}
  const individualPerformance = data.individual_performance || {}

  const formatPercentage = (value) => {
    if (typeof value !== 'number') return 'N/A'
    return `${value >= 0 ? '+' : ''}${(value * 100).toFixed(2)}%`
  }

  const formatRatio = (value) => {
    if (typeof value !== 'number') return 'N/A'
    return value.toFixed(3)
  }

  const getMetricStatus = (metric, value) => {
    if (typeof value !== 'number') return 'neutral'
    
    switch (metric) {
      case 'portfolio_return_annualized':
      case 'sharpe_ratio':
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
      case 'portfolio_return_annualized':
        return value > 0.15 ? 'Excellent Performance' : value > 0.08 ? 'Good Performance' : 'Below Average'
      case 'portfolio_volatility_annualized':
        return value < 0.15 ? 'Low Risk' : value < 0.25 ? 'Moderate Risk' : 'High Risk'
      case 'sharpe_ratio':
        return value > 1.5 ? 'Excellent Risk-Adj Return' : value > 1.0 ? 'Good Risk-Adj Return' : 'Poor Risk-Adj Return'
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
      case 'portfolio_return_annualized':
        return `The annualized return represents the geometric average amount of money earned by the portfolio each year. A return of ${(value * 100).toFixed(2)}% is considered ${value >= 0.15 ? 'excellent' : value >= 0.10 ? 'strong' : value >= 0.05 ? 'moderate' : 'modest'} performance, especially when risk-adjusted.`
      
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
      key: 'portfolio_return_annualized',
      label: 'Annual Return',
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
  ]

  // Prepare chart data for individual performance
  const chartData = Object.entries(individualPerformance).map(([symbol, perf]) => ({
    symbol,
    return: (perf.return * 100) || 0,
    volatility: (perf.volatility * 100) || 0
  }))

  return (
    <div className="space-y-8">
      <div>
        {/* Metrics Grid */}
        <div className="metrics-grid">
          {metrics.map((metric) => {
            const status = getMetricStatus(metric.key, metric.value)
            const statusText = getStatusText(metric.key, metric.value)
            const tooltip = getMetricTooltip(metric.key, metric.value)
            
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
            <div className="h-96">
              <ResponsiveContainer width="100%" height="100%">
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
                  <Bar 
                    dataKey="return" 
                    fill="var(--color-primary)" 
                    name="return"
                    radius={[2, 2, 0, 0]}
                  />
                  <Bar 
                    dataKey="volatility" 
                    fill="var(--color-warning)" 
                    name="volatility"
                    radius={[2, 2, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default OverviewSection
