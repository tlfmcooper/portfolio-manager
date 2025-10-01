import React, { useState, useEffect } from 'react'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts'
import { AlertTriangle, Info } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'

const RiskSection = () => {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const { api, portfolioId } = useAuth() // CRITICAL FIX: Get portfolioId from context

  useEffect(() => {
    const fetchData = async () => {
      if (!portfolioId) return; // Wait for portfolioId to load

      try {
        const response = await api.get(`/analysis/portfolios/${portfolioId}/analysis/metrics`) // CRITICAL FIX: Use dynamic portfolioId
        setData(response.data)
      } catch (err) {
        setError('Failed to fetch risk data')
        console.error(err)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [api, portfolioId]) // CRITICAL FIX: Add portfolioId to dependencies

  if (loading) return <div>Loading...</div>
  if (error) return <div className="text-red-500">{error}</div>
  if (!data) return null

  const riskAnalytics = data || {}

  const formatPercentage = (value) => {
    if (typeof value !== 'number') return 'N/A'
    return `${value >= 0 ? '+' : ''}${(value * 100).toFixed(2)}%`
  }

  const getRiskColor = (metricType, value) => {
    if (typeof value !== 'number') return 'text-gray-500'
    
    switch (metricType) {
      case 'value_at_risk_95':
        return Math.abs(value) < 0.03 ? 'text-yellow-600' : 'text-red-600'
      default:
        return 'text-gray-600'
    }
  }

  const getRiskStatus = (metricType, value) => {
    if (typeof value !== 'number') return 'No Data'
    
    switch (metricType) {
      case 'value_at_risk_95':
        return '5% Probability'
      case 'value_at_risk_99':
        return '1% Probability'
      case 'cvar':
        return 'Tail Risk'
      case 'semideviation':
        return 'Downside Volatility'
      default:
        return 'Risk Metric'
    }
  }

  // Dynamic tooltip generator based on risk metric values
  const getRiskTooltip = (key, value) => {
    if (typeof value !== 'number') return 'No data available for this metric.'
    
    const absValue = Math.abs(value * 100).toFixed(2)
    
    switch (key) {
      case 'value_at_risk_95':
        return `Value at Risk (95%) indicates there's only a 5% chance of losing more than ${absValue}% in any given period. This helps quantify downside risk exposure.`
      
      case 'value_at_risk_99':
        return `Value at Risk (99%) shows the potential loss in extreme scenarios (1% probability). ${(value * 100).toFixed(2)}% represents the tail risk of the portfolio.`
      
      case 'cvar':
        return `Conditional VaR shows the expected loss when VaR is exceeded. ${(value * 100).toFixed(2)}% represents the average loss in worst-case scenarios beyond the 95% threshold.`
      
      case 'semideviation':
        let semidevInterpretation = value < 0.05 ? 'low' : value < 0.10 ? 'moderate' : value < 0.15 ? 'elevated' : 'high'
        return `Semideviation measures downside volatility only, focusing on negative returns. ${(value * 100).toFixed(2)}% indicates ${semidevInterpretation} downside risk relative to total volatility.`
      
      default:
        return 'Risk metric for portfolio analysis.'
    }
  }

  const riskMetrics = [
    {
      key: 'value_at_risk_95',
      label: 'VaR (95%)',
      value: riskAnalytics.value_at_risk_95,
      type: 'warning',
    },
    {
      key: 'value_at_risk_99',
      label: 'VaR (99%)',
      value: riskAnalytics.value_at_risk_99,
      type: 'negative',
    },
    {
      key: 'cvar',
      label: 'CVaR (Expected Shortfall)',
      value: riskAnalytics.cvar,
      type: 'negative',
    },
    {
      key: 'semideviation',
      label: 'Semideviation',
      value: riskAnalytics.semideviation,
      type: 'neutral',
    }
  ]

  // Prepare data for risk distribution chart
  const chartData = [
    {
      name: 'VaR 95%',
      value: Math.abs((riskAnalytics.value_at_risk_95 || 0) * 100),
      color: 'var(--color-warning)'
    },
    {
      name: 'VaR 99%',
      value: Math.abs((riskAnalytics.value_at_risk_99 || 0) * 100),
      color: 'var(--color-error)'
    },
    {
      name: 'CVaR',
      value: Math.abs((riskAnalytics.cvar || 0) * 100),
      color: 'var(--color-red-500)'
    },
    {
      name: 'Semideviation',
      value: (riskAnalytics.semideviation || 0) * 100,
      color: 'var(--color-primary)'
    }
  ]

  const COLORS = [
    'var(--color-warning)', 
    'var(--color-error)', 
    'var(--color-red-500)', 
    'var(--color-primary)'
  ]

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0]
      return (
        <div 
          className="p-3 rounded-lg border"
          style={{
            backgroundColor: 'var(--color-charcoal-800)',
            color: 'var(--color-white)',
            borderColor: 'var(--color-border)'
          }}
        >
          <p className="font-medium">{data.name}</p>
          <p className="text-sm">{data.value.toFixed(2)}%</p>
        </div>
      )
    }
    return null
  }

  return (
    <div className="space-y-8">
      <div>
        {/* Risk Metrics Grid */}
        <div className="metrics-grid">
          {riskMetrics.map((metric) => {
            const status = getRiskStatus(metric.key, metric.value)
            const tooltip = getRiskTooltip(metric.key, metric.value)
            
            return (
              <div 
                key={metric.key}
                className={`metric-card ${metric.type}`}
                data-tooltip={tooltip}
              >
                <div className="metric-header">
                  <span className="metric-label">
                    {metric.label}
                  </span>
                  <span className="info-icon">ℹ️</span>
                </div>
                <div className="metric-value">
                  {formatPercentage(metric.value)}
                </div>
                <div className={`metric-status ${metric.type}`}>
                  {status}
                </div>
              </div>
            )
          })}
        </div>

        {/* Risk Distribution Chart */}
        <div className="chart-container">
          <h3 style={{ 
            fontSize: 'var(--font-size-xl)', 
            marginBottom: 'var(--space-20)',
            color: 'var(--color-text)'
          }}>
            Risk Distribution
          </h3>
          <div className="h-96">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={chartData}
                  cx="50%"
                  cy="50%"
                  outerRadius={120}
                  fill="#8884d8"
                  dataKey="value"
                  label={({ name, value }) => `${name}: ${value.toFixed(1)}%`}
                  labelLine={false}
                >
                  {chartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
                <Legend 
                  verticalAlign="bottom" 
                  height={36}
                  formatter={(value, entry) => (
                    <span style={{ color: entry.color }}>
                      {value}
                    </span>
                  )}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Risk Analysis Summary */}
        <div 
          className="border rounded-lg p-6"
          style={{
            backgroundColor: 'var(--color-bg-2)',
            borderColor: 'var(--color-border)'
          }}
        >
          <div className="flex items-start">
            <AlertTriangle 
              className="h-6 w-6 mt-1 mr-3 flex-shrink-0" 
              style={{ color: 'var(--color-primary)' }}
            />
            <div>
              <h4 
                className="text-lg font-semibold mb-2"
                style={{ color: 'var(--color-text)' }}
              >
                Risk Analysis Summary
              </h4>
              <div 
                className="space-y-2"
                style={{ color: 'var(--color-text)' }}
              >
                <p>
                  Your portfolio shows a <strong>VaR (95%) of {formatPercentage(riskAnalytics.value_at_risk_95)}</strong>, 
                  meaning there's only a 5% chance of losing more than this amount in any given period.
                </p>
                <p>
                  The <strong>Expected Shortfall (CVaR) of {formatPercentage(riskAnalytics.cvar)}</strong> represents 
                  the average loss in worst-case scenarios beyond the 95% threshold.
                </p>
                <p>
                  Portfolio volatility is <strong>{formatPercentage(riskAnalytics.portfolio_volatility_annualized)}</strong> annualized, 
                  with downside semideviation of <strong>{formatPercentage(riskAnalytics.semideviation)}</strong>.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default RiskSection
