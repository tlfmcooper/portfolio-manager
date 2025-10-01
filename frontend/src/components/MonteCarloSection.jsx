import React, { useState, useEffect } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts'
import { BarChart3, TrendingUp, AlertCircle } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'

const MonteCarloSection = () => {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const { api, portfolioId } = useAuth() // CRITICAL FIX: Get portfolioId from context

  useEffect(() => {
    const fetchData = async () => {
      if (!portfolioId) return; // Wait for portfolioId to load

      try {
        const response = await api.get(`/analysis/portfolios/${portfolioId}/analysis/monte-carlo`) // CRITICAL FIX: Use dynamic portfolioId
        setData(response.data)
      } catch (err) {
        setError('Failed to fetch Monte Carlo simulation data')
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

  const monteCarlo = data || {}
  const {
    scenarios = 1000,
    time_horizon = 252,
    initial_value = 1000,
    final_mean = 1125,
    final_std = 152,
    percentile_5 = 850,
    percentile_95 = 1420,
    success_probability = 0.85,
    simulation_paths = [],
    final_distribution = []
  } = monteCarlo

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value)
  }

  const formatNumber = (value) => {
    return new Intl.NumberFormat('en-US').format(value)
  }

  const getSuccessColor = (probability) => {
    if (probability >= 0.8) return 'text-green-600'
    if (probability >= 0.6) return 'text-yellow-600'
    return 'text-red-600'
  }

  const getSuccessStatus = (probability) => {
    if (probability >= 0.8) return 'High Confidence'
    if (probability >= 0.6) return 'Moderate Confidence'
    return 'Low Confidence'
  }

  // Summary metrics
  const summaryMetrics = [
    {
      label: 'Success Probability',
      value: `${(success_probability * 100).toFixed(0)}%`,
      description: `${formatNumber(scenarios)} Scenarios`,
      type: 'success'
    },
    {
      label: 'Expected Value',
      value: formatCurrency(final_mean),
      description: 'Mean Outcome',
      type: 'neutral'
    },
    {
      label: '5th Percentile',
      value: formatCurrency(percentile_5),
      description: 'Worst Case',
      type: 'negative'
    },
    {
      label: '95th Percentile',
      value: formatCurrency(percentile_95),
      description: 'Best Case',
      type: 'positive'
    }
  ]

  // Prepare path data for line chart
  const pathData = simulation_paths.map(path => ({
    day: path.day,
    path_1: path.path_1,
    path_2: path.path_2,
    path_3: path.path_3,
    path_4: path.path_4,
    path_5: path.path_5,
    mean_path: path.mean_path
  }))

  // Prepare distribution data for bar chart
  const distributionData = final_distribution.map(dist => ({
    range: dist.range,
    count: dist.count,
    percentage: dist.percentage
  }))

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-gray-900 text-white p-3 rounded-lg border border-gray-700">
          <p className="font-medium">Day {label}</p>
          {payload.map((entry, index) => (
            <p key={index} className="text-sm" style={{ color: entry.color }}>
              {entry.dataKey.replace('_', ' ')}: {formatCurrency(entry.value)}
            </p>
          ))}
        </div>
      )
    }
    return null
  }

  const DistributionTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload
      return (
        <div className="bg-gray-900 text-white p-3 rounded-lg border border-gray-700">
          <p className="font-medium">Final Value Range: {label}</p>
          <p className="text-sm">{data.count} scenarios ({data.percentage.toFixed(1)}%)</p>
        </div>
      )
    }
    return null
  }

  return (
    <div className="space-y-8">
      <div>
        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {summaryMetrics.map((metric, index) => {
            const typeColors = {
              success: success_probability >= 0.8 ? 'border-l-green-500 text-green-600' : 'border-l-yellow-500 text-yellow-600',
              positive: 'border-l-green-500 text-green-600',
              negative: 'border-l-red-500 text-red-600',
              neutral: 'border-l-blue-500 text-blue-600'
            }
            
            return (
              <div 
                key={index}
                className={`bg-white dark:bg-gray-800 rounded-lg shadow-sm border-l-4 p-6 ${typeColors[metric.type] || 'border-l-blue-500'}`}
              >
                <div className="text-center">
                  <p className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">
                    {metric.label}
                  </p>
                  <p className="text-3xl font-bold text-gray-900 dark:text-white mb-1">
                    {metric.value}
                  </p>
                  <p className="text-xs text-gray-600 dark:text-gray-400">
                    {metric.description}
                  </p>
                </div>
              </div>
            )
          })}
        </div>

        {/* Charts Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
          {/* Simulation Paths Chart */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
            <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">
              Simulation Paths (Sample Scenarios)
            </h3>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={pathData} margin={{ top: 20, right: 30, left: 20, bottom: 50 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.2} />
                  <XAxis 
                    dataKey="day" 
                    tick={{ fontSize: 12, fill: '#6B7280' }}
                    stroke="#6B7280"
                    label={{ value: 'Trading Days', position: 'insideBottom', offset: -5 }}
                  />
                  <YAxis 
                    tick={{ fontSize: 12, fill: '#6B7280' }}
                    stroke="#6B7280"
                    tickFormatter={(value) => `$${(value / 1000).toFixed(0)}K`}
                    label={{ value: 'Portfolio Value ($K)', angle: -90, position: 'insideLeft' }}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  
                  {/* Individual paths with transparency */}
                  <Line 
                    type="monotone" 
                    dataKey="path_1" 
                    stroke="#F59E0B" 
                    strokeWidth={1}
                    strokeOpacity={0.6}
                    dot={false}
                    name="Path 1"
                  />
                  <Line 
                    type="monotone" 
                    dataKey="path_2" 
                    stroke="#EF4444" 
                    strokeWidth={1}
                    strokeOpacity={0.6}
                    dot={false}
                    name="Path 2"
                  />
                  <Line 
                    type="monotone" 
                    dataKey="path_3" 
                    stroke="#10B981" 
                    strokeWidth={1}
                    strokeOpacity={0.6}
                    dot={false}
                    name="Path 3"
                  />
                  <Line 
                    type="monotone" 
                    dataKey="path_4" 
                    stroke="#8B5CF6" 
                    strokeWidth={1}
                    strokeOpacity={0.6}
                    dot={false}
                    name="Path 4"
                  />
                  <Line 
                    type="monotone" 
                    dataKey="path_5" 
                    stroke="#06B6D4" 
                    strokeWidth={1}
                    strokeOpacity={0.6}
                    dot={false}
                    name="Path 5"
                  />
                  
                  {/* Mean path highlighted */}
                  <Line 
                    type="monotone" 
                    dataKey="mean_path" 
                    stroke="#3B82F6" 
                    strokeWidth={3}
                    dot={{ r: 2 }}
                    name="Mean Path"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Final Return Distribution */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
            <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">
              Final Return Distribution
            </h3>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={distributionData} margin={{ top: 20, right: 30, left: 20, bottom: 60 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.2} />
                  <XAxis 
                    dataKey="range" 
                    tick={{ fontSize: 10, fill: '#6B7280' }}
                    stroke="#6B7280"
                    angle={-45}
                    textAnchor="end"
                    height={80}
                    label={{ value: 'Final Portfolio Value Range', position: 'insideBottom', offset: -40 }}
                  />
                  <YAxis 
                    tick={{ fontSize: 12, fill: '#6B7280' }}
                    stroke="#6B7280"
                    label={{ value: 'Number of Scenarios', angle: -90, position: 'insideLeft' }}
                  />
                  <Tooltip content={<DistributionTooltip />} />
                  <Bar 
                    dataKey="count" 
                    fill="#3B82F6"
                    radius={[2, 2, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Analysis Summary */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-start">
            <BarChart3 className="h-6 w-6 text-blue-600 dark:text-blue-400 mt-1 mr-3 flex-shrink-0" />
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
                Simulation Analysis
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <h4 className="font-medium text-gray-900 dark:text-white mb-2">Key Statistics</h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Scenarios Analyzed:</span>
                      <span className="font-medium text-gray-900 dark:text-white">
                        {formatNumber(scenarios)}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Time Horizon:</span>
                      <span className="font-medium text-gray-900 dark:text-white">
                        {time_horizon} trading days (1 year)
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Initial Investment:</span>
                      <span className="font-medium text-gray-900 dark:text-white">
                        {formatCurrency(initial_value)}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Standard Deviation:</span>
                      <span className="font-medium text-gray-900 dark:text-white">
                        {formatCurrency(final_std)}
                      </span>
                    </div>
                  </div>
                </div>
                <div>
                  <h4 className="font-medium text-gray-900 dark:text-white mb-2">Risk Assessment</h4>
                  <div className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
                    <p>
                      • <strong className={getSuccessColor(success_probability)}>
                        {(success_probability * 100).toFixed(0)}% probability
                      </strong> of achieving positive returns over the investment horizon
                    </p>
                    <p>
                      • There's a <strong>5% chance</strong> of returns falling below {formatCurrency(percentile_5)}
                    </p>
                    <p>
                      • There's a <strong>5% chance</strong> of returns exceeding {formatCurrency(percentile_95)}
                    </p>
                    <p>
                      • Expected return range: <strong>{formatCurrency(percentile_5)}</strong> to{' '}
                      <strong>{formatCurrency(percentile_95)}</strong>
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Confidence Assessment */}
        <div className={`rounded-lg p-6 border ${
          success_probability >= 0.8 
            ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800' 
            : success_probability >= 0.6
              ? 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800'
              : 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800'
        }`}>
          <div className="flex items-start">
            <AlertCircle className={`h-6 w-6 mt-1 mr-3 flex-shrink-0 ${
              success_probability >= 0.8 
                ? 'text-green-600 dark:text-green-400'
                : success_probability >= 0.6
                  ? 'text-yellow-600 dark:text-yellow-400'
                  : 'text-red-600 dark:text-red-400'
            }`} />
            <div>
              <h4 className={`text-lg font-semibold mb-2 ${
                success_probability >= 0.8 
                  ? 'text-green-900 dark:text-green-100'
                  : success_probability >= 0.6
                    ? 'text-yellow-900 dark:text-yellow-100'
                    : 'text-red-900 dark:text-red-100'
              }`}>
                Investment Confidence: {getSuccessStatus(success_probability)}
              </h4>
              <p className={`${
                success_probability >= 0.8 
                  ? 'text-green-800 dark:text-green-200'
                  : success_probability >= 0.6
                    ? 'text-yellow-800 dark:text-yellow-200'
                    : 'text-red-800 dark:text-red-200'
              }`}>
                Based on {formatNumber(scenarios)} simulated scenarios, your portfolio shows {' '}
                {success_probability >= 0.8 
                  ? 'strong potential for positive returns with well-managed downside risk.'
                  : success_probability >= 0.6
                    ? 'moderate potential for positive returns but consider risk management strategies.'
                    : 'significant downside risk. Consider reviewing your portfolio allocation and risk tolerance.'
                }
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default MonteCarloSection
