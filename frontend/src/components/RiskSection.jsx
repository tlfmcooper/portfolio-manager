import React from 'react'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts'
import { AlertTriangle, Info } from 'lucide-react'

const RiskSection = ({ data }) => {
  if (!data) return null

  const riskAnalytics = data.risk_analytics || {}

  const formatPercentage = (value) => {
    if (typeof value !== 'number') return 'N/A'
    return `${value >= 0 ? '+' : ''}${(value * 100).toFixed(2)}%`
  }

  const getRiskColor = (metricType, value) => {
    if (typeof value !== 'number') return 'text-gray-500'
    
    switch (metricType) {
      case 'var_95':
      case 'var_99':
        return Math.abs(value) < 0.03 ? 'text-yellow-600' : 'text-red-600'
      case 'cvar':
        return Math.abs(value) < 0.05 ? 'text-red-600' : 'text-red-700'
      case 'semideviation':
        return value < 0.1 ? 'text-blue-600' : 'text-yellow-600'
      default:
        return 'text-gray-600'
    }
  }

  const getRiskStatus = (metricType, value) => {
    if (typeof value !== 'number') return 'No Data'
    
    switch (metricType) {
      case 'var_95':
        return '5% Probability'
      case 'var_99':
        return '1% Probability'
      case 'cvar':
        return 'Tail Risk'
      case 'semideviation':
        return 'Downside Volatility'
      default:
        return 'Risk Metric'
    }
  }

  const getTooltipText = (metricType) => {
    switch (metricType) {
      case 'var_95':
        return 'Value at Risk (95%) indicates there\'s only a 5% chance of losing more than this amount in any given period.'
      case 'var_99':
        return 'Value at Risk (99%) shows the potential loss in extreme scenarios (1% probability).'
      case 'cvar':
        return 'Conditional VaR shows the expected loss when VaR is exceeded. This represents the average loss in worst-case scenarios.'
      case 'semideviation':
        return 'Semideviation measures downside volatility only, focusing on negative returns rather than total volatility.'
      default:
        return 'Risk metric for portfolio analysis.'
    }
  }

  const riskMetrics = [
    {
      key: 'var_95',
      label: 'VaR (95%)',
      value: riskAnalytics.var_95,
      type: 'warning'
    },
    {
      key: 'var_99',
      label: 'VaR (99%)',
      value: riskAnalytics.var_99,
      type: 'negative'
    },
    {
      key: 'cvar',
      label: 'CVaR (Expected Shortfall)',
      value: riskAnalytics.cvar,
      type: 'negative'
    },
    {
      key: 'semideviation',
      label: 'Semideviation',
      value: riskAnalytics.semideviation,
      type: 'neutral'
    }
  ]

  // Prepare data for risk distribution chart
  const chartData = [
    {
      name: 'VaR 95%',
      value: Math.abs((riskAnalytics.var_95 || 0) * 100),
      color: '#F59E0B'
    },
    {
      name: 'VaR 99%',
      value: Math.abs((riskAnalytics.var_99 || 0) * 100),
      color: '#EF4444'
    },
    {
      name: 'CVaR',
      value: Math.abs((riskAnalytics.cvar || 0) * 100),
      color: '#DC2626'
    },
    {
      name: 'Semideviation',
      value: (riskAnalytics.semideviation || 0) * 100,
      color: '#3B82F6'
    }
  ]

  const COLORS = ['#F59E0B', '#EF4444', '#DC2626', '#3B82F6']

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0]
      return (
        <div className="bg-gray-900 text-white p-3 rounded-lg border border-gray-700">
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
        <h2 className="text-2xl font-bold mb-6">Risk Analytics</h2>
        
        {/* Risk Metrics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {riskMetrics.map((metric) => {
            const colorClass = getRiskColor(metric.key, metric.value)
            const status = getRiskStatus(metric.key, metric.value)
            const tooltip = getTooltipText(metric.key)
            
            return (
              <div 
                key={metric.key}
                className={`bg-white dark:bg-gray-800 rounded-lg shadow-sm border-l-4 p-6 hover:shadow-md transition-all duration-200 ${
                  metric.type === 'warning' ? 'border-l-yellow-500' :
                  metric.type === 'negative' ? 'border-l-red-500' :
                  'border-l-blue-500'
                }`}
              >
                <div className="flex justify-between items-start mb-3">
                  <span className="text-sm font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    {metric.label}
                  </span>
                  <div className="group relative">
                    <Info className="h-4 w-4 text-gray-400 cursor-help" />
                    <div className="absolute right-0 top-6 w-64 p-3 bg-gray-900 text-white text-xs rounded-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-10">
                      {tooltip}
                    </div>
                  </div>
                </div>
                <div className={`text-3xl font-bold mb-2 ${colorClass}`}>
                  {formatPercentage(metric.value)}
                </div>
                <div className={`text-xs font-medium uppercase tracking-wider ${colorClass}`}>
                  {status}
                </div>
              </div>
            )
          })}
        </div>

        {/* Risk Distribution Chart */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">
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
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-6">
          <div className="flex items-start">
            <AlertTriangle className="h-6 w-6 text-blue-600 dark:text-blue-400 mt-1 mr-3 flex-shrink-0" />
            <div>
              <h4 className="text-lg font-semibold text-blue-900 dark:text-blue-100 mb-2">
                Risk Analysis Summary
              </h4>
              <div className="text-blue-800 dark:text-blue-200 space-y-2">
                <p>
                  Your portfolio shows a <strong>VaR (95%) of {formatPercentage(riskAnalytics.var_95)}</strong>, 
                  meaning there's only a 5% chance of losing more than this amount in any given period.
                </p>
                <p>
                  The <strong>Expected Shortfall (CVaR) of {formatPercentage(riskAnalytics.cvar)}</strong> represents 
                  the average loss in worst-case scenarios beyond the 95% threshold.
                </p>
                <p>
                  Portfolio volatility is <strong>{formatPercentage(riskAnalytics.portfolio_volatility)}</strong> annualized, 
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
