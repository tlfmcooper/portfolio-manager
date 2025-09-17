import React from 'react'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts'

const AllocationSection = ({ data }) => {
  if (!data) return null

  const assetAllocation = data.asset_allocation || {}
  const individualPerformance = data.individual_performance || {}

  const formatPercentage = (value) => {
    if (typeof value !== 'number') return 'N/A'
    return `${(value * 100).toFixed(1)}%`
  }

  const formatCurrency = (value, weight) => {
    const totalValue = 1250000 // Default total value
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(totalValue * weight)
  }

  // Asset names mapping
  const assetNames = {
    'AAPL': 'Apple Inc.',
    'GOOGL': 'Alphabet Inc.',
    'MSFT': 'Microsoft Corp.',
    'AMZN': 'Amazon.com Inc.',
    'SPY': 'S&P 500 ETF',
    'QQQ': 'Nasdaq 100 ETF',
    'TLT': '20+ Year Treasury ETF',
    'GLD': 'Gold ETF',
    'VNQ': 'Real Estate ETF',
    'VEA': 'Developed Markets ETF'
  }

  // Prepare data for pie chart
  const pieData = Object.entries(assetAllocation).map(([symbol, weight], index) => ({
    name: symbol,
    value: weight * 100,
    weight: weight,
    color: `hsl(${index * 36}, 70%, 50%)`
  }))

  // Prepare data for bar chart (asset values)
  const barData = Object.entries(assetAllocation).map(([symbol, weight]) => ({
    symbol,
    value: 1250000 * weight, // Assuming $1.25M total value
    percentage: weight * 100
  }))

  // Colors for charts
  const COLORS = [
    '#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', 
    '#06B6D4', '#F97316', '#84CC16', '#F43F5E', '#6366F1'
  ]

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload
      return (
        <div className="bg-gray-900 text-white p-3 rounded-lg border border-gray-700">
          <p className="font-medium">{data.name || data.symbol}</p>
          <p className="text-sm">{formatCurrency(data.value || 1250000 * data.weight, data.weight || data.percentage / 100)}</p>
          <p className="text-sm">{formatPercentage(data.weight || data.percentage / 100)}</p>
        </div>
      )
    }
    return null
  }

  const totalAssets = Object.keys(assetAllocation).length
  const largestAllocation = Math.max(...Object.values(assetAllocation))

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-bold mb-6">Asset Allocation</h2>
        
        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
            <div className="text-center">
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">Total Assets</p>
              <p className="text-3xl font-bold text-gray-900 dark:text-white">{totalAssets}</p>
            </div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
            <div className="text-center">
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">Total Allocated</p>
              <p className="text-3xl font-bold text-gray-900 dark:text-white">$1,250,000</p>
            </div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
            <div className="text-center">
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">Largest Position</p>
              <p className="text-3xl font-bold text-gray-900 dark:text-white">{formatPercentage(largestAllocation)}</p>
            </div>
          </div>
        </div>

        {/* Charts Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
          {/* Pie Chart */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
            <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">
              Portfolio Composition
            </h3>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, value }) => `${name} ${value.toFixed(1)}%`}
                    outerRadius={100}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {pieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip content={<CustomTooltip />} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Bar Chart */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
            <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">
              Asset Values
            </h3>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={barData} margin={{ top: 20, right: 30, left: 20, bottom: 60 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.2} />
                  <XAxis 
                    dataKey="symbol" 
                    tick={{ fontSize: 12, fill: '#6B7280' }}
                    stroke="#6B7280"
                    angle={-45}
                    textAnchor="end"
                    height={80}
                  />
                  <YAxis 
                    tick={{ fontSize: 12, fill: '#6B7280' }}
                    stroke="#6B7280"
                    tickFormatter={(value) => `$${(value / 1000).toFixed(0)}K`}
                  />
                  <Tooltip 
                    content={<CustomTooltip />}
                    formatter={(value) => [`$${(value / 1000).toFixed(0)}K`, 'Value']}
                  />
                  <Bar 
                    dataKey="value" 
                    fill="#3B82F6"
                    radius={[4, 4, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Asset Breakdown Table */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Asset Breakdown</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-700">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Symbol
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Name
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Value
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Weight
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Allocation Bar
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                {Object.entries(assetAllocation)
                  .sort(([,a], [,b]) => b - a)
                  .map(([symbol, weight], index) => (
                  <tr key={symbol} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div 
                          className="h-3 w-3 rounded-full mr-3"
                          style={{ backgroundColor: COLORS[Object.keys(assetAllocation).indexOf(symbol) % COLORS.length] }}
                        ></div>
                        <div className="text-sm font-medium text-gray-900 dark:text-white">
                          {symbol}
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-600 dark:text-gray-300">
                        {assetNames[symbol] || symbol}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right">
                      <div className="text-sm font-medium text-gray-900 dark:text-white">
                        {formatCurrency(1250000 * weight, weight)}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right">
                      <div className="text-sm text-gray-900 dark:text-white">
                        {formatPercentage(weight)}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right">
                      <div className="flex items-center justify-end">
                        <div className="w-20 bg-gray-200 dark:bg-gray-600 rounded-full h-2">
                          <div 
                            className="h-2 rounded-full transition-all duration-300"
                            style={{ 
                              width: `${weight * 100}%`,
                              backgroundColor: COLORS[Object.keys(assetAllocation).indexOf(symbol) % COLORS.length]
                            }}
                          ></div>
                        </div>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Diversification Analysis */}
        <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-green-900 dark:text-green-100 mb-4">
            Diversification Analysis
          </h3>
          <div className="text-green-800 dark:text-green-200 space-y-2">
            <p>
              Your portfolio is allocated across <strong>{totalAssets} assets</strong>. The largest allocation is{' '}
              <strong>{formatPercentage(largestAllocation)}</strong> in{' '}
              <strong>
                {Object.entries(assetAllocation).find(([,weight]) => weight === largestAllocation)?.[0]}
              </strong>.
            </p>
            
            <div className="mt-4">
              <h4 className="font-medium text-green-900 dark:text-green-100 mb-2">Diversification Score</h4>
              <div className="flex items-center">
                <div className="flex-1">
                  {(() => {
                    const maxPercentage = largestAllocation * 100
                    const diversificationScore = maxPercentage < 30 ? 'Excellent' :
                                               maxPercentage < 50 ? 'Good' :
                                               maxPercentage < 70 ? 'Moderate' : 'Poor'
                    const scoreColor = maxPercentage < 30 ? 'text-green-600 dark:text-green-400' :
                                     maxPercentage < 50 ? 'text-blue-600 dark:text-blue-400' :
                                     maxPercentage < 70 ? 'text-yellow-600 dark:text-yellow-400' : 'text-red-600 dark:text-red-400'
                    
                    return (
                      <span className={`font-semibold ${scoreColor}`}>
                        {diversificationScore}
                      </span>
                    )
                  })()}
                  <span className="text-green-700 dark:text-green-300 ml-2">
                    ({largestAllocation * 100 < 30 
                      ? 'Well-diversified across assets' 
                      : 'Consider reducing concentration in largest position'})
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default AllocationSection
