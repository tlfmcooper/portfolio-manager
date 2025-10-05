import React, { useState, useEffect } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts'
import { TrendingDown, Shield, Target, Info } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'

const CPPISection = () => {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const { api, portfolioId } = useAuth() // CRITICAL FIX: Get portfolioId from context

  useEffect(() => {
    const fetchData = async () => {
      if (!portfolioId) return; // Wait for portfolioId to load

      try {
        const response = await api.get(`/analysis/portfolios/${portfolioId}/cppi`) // CRITICAL FIX: Use dynamic portfolioId
        setData(response.data)
      } catch (err) {
        setError('Failed to fetch CPPI analysis data')
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

  const cppiAnalysis = data || {}
  const {
    multiplier = 3,
    floor = 0.8,
    initial_value = 1000,
    final_cppi_value = 1180,
    final_buyhold_value = 1125,
    outperformance = 0.049,
    performance_data = [],
    drawdown_data = []
  } = cppiAnalysis

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value)
  }

  const formatPercentage = (value) => {
    if (typeof value !== 'number') return 'N/A'
    return `${value >= 0 ? '+' : ''}${(value * 100).toFixed(1)}%`
  }

  // Strategy metrics
  const strategyMetrics = [
    {
      label: 'CPPI Final Value',
      value: formatCurrency(final_cppi_value),
      description: 'Dynamic Strategy',
      type: 'positive'
    },
    {
      label: 'Buy & Hold Value',
      value: formatCurrency(final_buyhold_value),
      description: 'Static Strategy',
      type: 'neutral'
    },
    {
      label: 'Outperformance',
      value: formatPercentage(outperformance),
      description: 'CPPI Advantage',
      type: outperformance > 0 ? 'positive' : 'negative'
    },
    {
      label: 'Multiplier',
      value: `${multiplier}.0x`,
      description: 'Risk Leverage',
      type: 'neutral'
    }
  ]

  // Prepare data for allocation chart
  const allocationData = performance_data.map(item => ({
    day: item.day,
    risky_allocation: item.risky_allocation || 0,
    safe_allocation: 100 - (item.risky_allocation || 0)
  }))

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-gray-900 text-white p-3 rounded-lg border border-gray-700">
          <p className="font-medium">Day {label}</p>
          {payload.map((entry, index) => (
            <p key={index} className="text-sm" style={{ color: entry.color }}>
              {entry.dataKey === 'cppi_wealth' ? 'CPPI Wealth' :
               entry.dataKey === 'buyhold_wealth' ? 'Buy & Hold' :
               entry.dataKey === 'floor_value' ? 'Floor Protection' :
               entry.dataKey === 'risky_allocation' ? 'Risky Assets' :
               entry.dataKey === 'safe_allocation' ? 'Safe Assets' :
               entry.dataKey === 'risk_budget' ? 'Risk Budget' :
               entry.dataKey === 'cppi_drawdown' ? 'CPPI Drawdown' :
               entry.dataKey === 'buyhold_drawdown' ? 'Buy & Hold Drawdown' :
               entry.name}: {
                entry.dataKey.includes('wealth') || entry.dataKey.includes('floor') ? 
                  formatCurrency(entry.value) : 
                  `${entry.value.toFixed(1)}%`
              }
            </p>
          ))}
        </div>
      )
    }
    return null
  }

  return (
    <div className="space-y-8">
      <div>
        {/* Explanation Card */}
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-6 mb-8">
          <div className="flex items-start">
            <Shield className="h-6 w-6 text-blue-600 dark:text-blue-400 mt-1 mr-3 flex-shrink-0" />
            <div>
              <h4 className="text-lg font-semibold text-blue-900 dark:text-blue-100 mb-2">
                Understanding CPPI Strategy
              </h4>
              <p className="text-blue-800 dark:text-blue-200">
                CPPI (Constant Proportion Portfolio Insurance) is a dynamic strategy that adjusts risk exposure 
                to provide downside protection while maintaining upside participation. The strategy uses a multiplier 
                of {multiplier}x and maintains a floor protection at {formatPercentage(floor)} of initial investment. 
                The strategy {outperformance >= 0 ? 'outperformed' : 'underperformed'} buy-and-hold by {formatPercentage(Math.abs(outperformance))}.
              </p>
            </div>
          </div>
        </div>

        {/* Strategy Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {strategyMetrics.map((metric, index) => {
            const typeColors = {
              positive: 'border-l-green-500',
              negative: 'border-l-red-500',
              neutral: 'border-l-blue-500'
            }
            
            const textColors = {
              positive: 'text-green-600',
              negative: 'text-red-600',
              neutral: 'text-blue-600'
            }
            
            return (
              <div 
                key={index}
                className={`bg-white dark:bg-gray-800 rounded-lg shadow-sm border-l-4 p-6 ${typeColors[metric.type]}`}
              >
                <div className="text-center">
                  <p className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">
                    {metric.label}
                  </p>
                  <p className="text-3xl font-bold text-gray-900 dark:text-white mb-1">
                    {metric.value}
                  </p>
                  <p className={`text-xs font-medium uppercase tracking-wider ${textColors[metric.type]}`}>
                    {metric.description}
                  </p>
                </div>
              </div>
            )
          })}
        </div>

        {/* Charts Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
          {/* Performance Comparison */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
            <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">
              Performance Comparison
            </h3>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={performance_data} margin={{ top: 20, right: 30, left: 20, bottom: 50 }}>
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
                  
                  <Line 
                    type="monotone" 
                    dataKey="cppi_wealth" 
                    stroke="#3B82F6" 
                    strokeWidth={3}
                    dot={{ r: 2 }}
                    name="CPPI Strategy"
                  />
                  <Line 
                    type="monotone" 
                    dataKey="buyhold_wealth" 
                    stroke="#F59E0B" 
                    strokeWidth={2}
                    dot={false}
                    name="Buy & Hold"
                  />
                  <Line 
                    type="monotone" 
                    dataKey="floor_value" 
                    stroke="#EF4444" 
                    strokeWidth={2}
                    strokeDasharray="5 5"
                    dot={false}
                    name="Floor Protection"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Dynamic Allocation */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
            <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">
              Dynamic Allocation
            </h3>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={allocationData} margin={{ top: 20, right: 30, left: 20, bottom: 50 }}>
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
                    domain={[0, 100]}
                    label={{ value: 'Allocation (%)', angle: -90, position: 'insideLeft' }}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  
                  <Area
                    type="monotone"
                    dataKey="risky_allocation"
                    stackId="1"
                    stroke="#3B82F6"
                    fill="#3B82F6"
                    fillOpacity={0.6}
                    name="Risky Assets"
                  />
                  <Area
                    type="monotone"
                    dataKey="safe_allocation"
                    stackId="1"
                    stroke="#10B981"
                    fill="#10B981"
                    fillOpacity={0.6}
                    name="Safe Assets"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Risk Budget Evolution */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
            <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">
              Risk Budget Evolution
            </h3>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={performance_data} margin={{ top: 20, right: 30, left: 20, bottom: 50 }}>
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
                    tickFormatter={(value) => `${value.toFixed(0)}%`}
                    label={{ value: 'Risk Budget (%)', angle: -90, position: 'insideLeft' }}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  
                  <Area
                    type="monotone"
                    dataKey="risk_budget"
                    stroke="#8B5CF6"
                    fill="#8B5CF6"
                    fillOpacity={0.4}
                    name="Risk Budget (Cushion)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Drawdown Comparison */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
            <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">
              Drawdown Comparison
            </h3>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={drawdown_data} margin={{ top: 20, right: 30, left: 20, bottom: 50 }}>
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
                    tickFormatter={(value) => `${value.toFixed(0)}%`}
                    domain={[-8, 1]}
                    label={{ value: 'Drawdown (%)', angle: -90, position: 'insideLeft' }}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  
                  <Area
                    type="monotone"
                    dataKey="cppi_drawdown"
                    stroke="#3B82F6"
                    fill="#3B82F6"
                    fillOpacity={0.4}
                    name="CPPI Drawdown"
                  />
                  <Area
                    type="monotone"
                    dataKey="buyhold_drawdown"
                    stroke="#F59E0B"
                    fill="#F59E0B"
                    fillOpacity={0.4}
                    name="Buy & Hold Drawdown"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Strategy Analysis */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6 mb-8">
          <div className="flex items-start">
            <Target className="h-6 w-6 text-blue-600 dark:text-blue-400 mt-1 mr-3 flex-shrink-0" />
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
                CPPI Strategy Analysis
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <h4 className="font-medium text-gray-900 dark:text-white mb-2">Strategy Mechanics</h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Multiplier:</span>
                      <span className="font-medium text-gray-900 dark:text-white">{multiplier}x</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Floor Protection:</span>
                      <span className="font-medium text-gray-900 dark:text-white">
                        {formatPercentage(floor)}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Initial Investment:</span>
                      <span className="font-medium text-gray-900 dark:text-white">
                        {formatCurrency(initial_value)}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Final CPPI Value:</span>
                      <span className="font-medium text-green-600">
                        {formatCurrency(final_cppi_value)}
                      </span>
                    </div>
                  </div>
                </div>
                <div>
                  <h4 className="font-medium text-gray-900 dark:text-white mb-2">Performance Benefits</h4>
                  <div className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
                    <p>
                      • <strong>Downside Protection:</strong> The floor mechanism protects against 
                      losses below {formatPercentage(floor)} of initial investment
                    </p>
                    <p>
                      • <strong>Dynamic Allocation:</strong> Risk exposure automatically adjusts 
                      based on portfolio cushion above the floor
                    </p>
                    <p>
                      • <strong>Outperformance:</strong> Generated {formatPercentage(outperformance)} 
                      excess return compared to static buy-and-hold
                    </p>
                    <p>
                      • <strong>Risk Management:</strong> Reduced maximum drawdown through 
                      adaptive risk budgeting
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Risk Considerations */}
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-6">
          <div className="flex items-start">
            <Info className="h-6 w-6 text-yellow-600 dark:text-yellow-400 mt-1 mr-3 flex-shrink-0" />
            <div>
              <h4 className="text-lg font-semibold text-yellow-900 dark:text-yellow-100 mb-2">
                Strategy Considerations
              </h4>
              <div className="text-yellow-800 dark:text-yellow-200 space-y-2">
                <p>
                  <strong>Market Conditions:</strong> CPPI strategies perform well in trending markets 
                  but may lag in highly volatile or sideways markets due to frequent rebalancing.
                </p>
                <p>
                  <strong>Transaction Costs:</strong> The dynamic nature of CPPI requires regular 
                  rebalancing, which can generate higher transaction costs in practice.
                </p>
                <p>
                  <strong>Gap Risk:</strong> Large market gaps can potentially breach the floor 
                  protection in extreme market conditions.
                </p>
                <p>
                  <strong>Opportunity Cost:</strong> The floor protection comes at the cost of 
                  potential upside when markets perform strongly.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default CPPISection
