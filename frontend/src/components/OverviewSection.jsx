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
        setData(response.data)
      } catch (err) {
        setError('Failed to fetch overview data')
        console.error(err)
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
    switch (status) {
      case 'positive': return 'text-green-600'
      case 'negative': return 'text-red-600'
      case 'warning': return 'text-yellow-600'
      default: return 'text-blue-600'
    }
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

  const metrics = [
    {
      key: 'portfolio_return_annualized',
      label: 'Annual Return',
      value: performanceMetrics.portfolio_return_annualized,
      formatter: formatPercentage,
      tooltip: 'The annualized return represents the geometric average amount of money earned by the portfolio each year.'
    },
    {
      key: 'portfolio_volatility_annualized',
      label: 'Annual Volatility',
      value: performanceMetrics.portfolio_volatility_annualized,
      formatter: formatPercentage,
      tooltip: 'Annual volatility measures the portfolio\'s price fluctuations over time.'
    },
    {
      key: 'sharpe_ratio',
      label: 'Sharpe Ratio',
      value: performanceMetrics.sharpe_ratio,
      formatter: formatRatio,
      tooltip: 'The Sharpe ratio measures risk-adjusted returns. Values above 1.0 are good, above 2.0 are very good.'
    },
    {
      key: 'sortino_ratio',
      label: 'Sortino Ratio',
      value: performanceMetrics.sortino_ratio,
      formatter: formatRatio,
      tooltip: 'The Sortino ratio focuses on downside volatility, providing a better measure of risk-adjusted returns.'
    },
    {
      key: 'max_drawdown',
      label: 'Maximum Drawdown',
      value: performanceMetrics.max_drawdown,
      formatter: formatPercentage,
      tooltip: 'Maximum drawdown shows the largest peak-to-trough decline in portfolio value.'
    },
    {
      key: 'calmar_ratio',
      label: 'Calmar Ratio',
      value: performanceMetrics.calmar_ratio,
      formatter: formatRatio,
      tooltip: 'The Calmar ratio compares annual return to maximum drawdown.'
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
        <h2 className="text-2xl font-bold mb-6">Performance Overview</h2>
        
        {/* Metrics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
          {metrics.map((metric) => {
            const status = getMetricStatus(metric.key, metric.value)
            const statusColor = getStatusColor(status)
            const statusText = getStatusText(metric.key, metric.value)
            
            return (
              <div 
                key={metric.key}
                className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6 hover:shadow-md transition-shadow duration-200"
              >
                <div className="flex justify-between items-start mb-3">
                  <span className="text-sm font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    {metric.label}
                  </span>
                  <div className="group relative">
                    <Info className="h-4 w-4 text-gray-400 cursor-help" />
                    <div className="absolute right-0 top-6 w-64 p-3 bg-gray-900 text-white text-xs rounded-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-10">
                      {metric.tooltip}
                    </div>
                  </div>
                </div>
                <div className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
                  {metric.formatter(metric.value)}
                </div>
                <div className={`text-xs font-medium uppercase tracking-wider ${statusColor}`}>
                  {statusText}
                </div>
              </div>
            )
          })}
        </div>

        {/* Performance Chart */}
        {chartData.length > 0 && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
            <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">
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
                      backgroundColor: '#1F2937',
                      border: '1px solid #374151',
                      borderRadius: '8px',
                      color: '#F9FAFB'
                    }}
                    formatter={(value, name) => [
                      `${value.toFixed(2)}%`, 
                      name === 'return' ? 'Annual Return' : 'Volatility'
                    ]}
                  />
                  <Bar 
                    dataKey="return" 
                    fill="#3B82F6" 
                    name="return"
                    radius={[2, 2, 0, 0]}
                  />
                  <Bar 
                    dataKey="volatility" 
                    fill="#F59E0B" 
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
