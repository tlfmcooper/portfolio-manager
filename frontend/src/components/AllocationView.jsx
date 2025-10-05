import React from 'react'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts'
import { useCurrency } from '../contexts/CurrencyContext'

const AllocationView = ({ data }) => {
  const { formatCurrency } = useCurrency()

  if (!data || !Array.isArray(data)) return null

  const formatPercentage = (value) => {
    return `${value.toFixed(1)}%`
  }

  // Color palette for sectors
  const COLORS = [
    '#3B82F6', // Blue
    '#10B981', // Green
    '#F59E0B', // Yellow
    '#EF4444', // Red
    '#8B5CF6', // Purple
    '#06B6D4', // Cyan
    '#F97316', // Orange
    '#84CC16', // Lime
  ]

  const totalValue = data.reduce((sum, sector) => sum + sector.value, 0)

  // Prepare data for charts
  const pieData = data.map((sector, index) => ({
    ...sector,
    color: COLORS[index % COLORS.length]
  }))

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload
      return (
        <div className="bg-white p-3 border border-gray-200 rounded shadow">
          <p className="font-medium">{data.sector}</p>
          <p className="text-blue-600">{formatCurrency(data.value)}</p>
          <p className="text-gray-600">{formatPercentage(data.percentage)}</p>
        </div>
      )
    }
    return null
  }

  return (
    <div className="space-y-6">
      {/* Allocation Summary */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Sector Allocation Overview</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <p className="text-sm font-medium text-gray-500">Total Sectors</p>
            <p className="text-2xl font-semibold text-gray-900">{data.length}</p>
          </div>
          <div>
            <p className="text-sm font-medium text-gray-500">Total Allocated</p>
            <p className="text-2xl font-semibold text-gray-900">
              {formatCurrency(totalValue)}
            </p>
          </div>
          <div>
            <p className="text-sm font-medium text-gray-500">Largest Sector</p>
            <p className="text-2xl font-semibold text-gray-900">
              {formatPercentage(Math.max(...data.map(s => s.percentage)))}
            </p>
          </div>
        </div>
      </div>
      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Pie Chart */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Sector Distribution</h3>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ sector, percentage }) => `${sector} ${formatPercentage(percentage)}`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="percentage"
                >
                  {pieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Bar Chart */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Sector Values</h3>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 60 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis 
                  dataKey="sector" 
                  tick={{ fontSize: 12 }}
                  angle={-45}
                  textAnchor="end"
                  height={80}
                />
                <YAxis 
                  tick={{ fontSize: 12 }}
                  tickFormatter={(value) => `$${(value / 1000).toFixed(0)}K`}
                />
                <Tooltip 
                  formatter={(value) => [formatCurrency(value), 'Value']}
                  labelStyle={{ color: '#374151' }}
                  contentStyle={{ 
                    backgroundColor: '#fff', 
                    border: '1px solid #e5e7eb',
                    borderRadius: '6px'
                  }}
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
      {/* Sector Breakdown Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">Detailed Sector Breakdown</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Sector
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Value
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Percentage
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Allocation Bar
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {data
                .sort((a, b) => b.percentage - a.percentage)
                .map((sector, index) => (
                <tr key={index} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <div 
                        className="h-3 w-3 rounded-full mr-3"
                        style={{ backgroundColor: COLORS[index % COLORS.length] }}
                      ></div>
                      <div className="text-sm font-medium text-gray-900">
                        {sector.sector}
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right">
                    <div className="text-sm font-medium text-gray-900">
                      {formatCurrency(sector.value)}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right">
                    <div className="text-sm text-gray-900">
                      {formatPercentage(sector.percentage)}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right">
                    <div className="flex items-center justify-end">
                      <div className="w-20 bg-gray-200 rounded-full h-2">
                        <div 
                          className="h-2 rounded-full transition-all duration-300"
                          style={{ 
                            width: `${sector.percentage}%`,
                            backgroundColor: COLORS[index % COLORS.length]
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
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Diversification Analysis</h3>
        <div className="prose max-w-none">
          <p className="text-gray-600 mb-4">
            Your portfolio is allocated across {data.length} sectors. The largest sector allocation is{' '}
            <span className="font-semibold text-gray-900">
              {data.reduce((max, sector) => sector.percentage > max.percentage ? sector : max).sector}
            </span>
            {' '}at {formatPercentage(Math.max(...data.map(s => s.percentage)))}.
          </p>
          
          <div className="mt-4">
            <h4 className="font-medium text-gray-900 mb-2">Diversification Score</h4>
            <div className="flex items-center">
              <div className="flex-1">
                {(() => {
                  const maxPercentage = Math.max(...data.map(s => s.percentage))
                  const diversificationScore = maxPercentage < 30 ? 'Excellent' :
                                             maxPercentage < 50 ? 'Good' :
                                             maxPercentage < 70 ? 'Moderate' : 'Poor'
                  const scoreColor = maxPercentage < 30 ? 'text-green-600' :
                                   maxPercentage < 50 ? 'text-blue-600' :
                                   maxPercentage < 70 ? 'text-yellow-600' : 'text-red-600'
                  
                  return (
                    <span className={`font-semibold ${scoreColor}`}>
                      {diversificationScore}
                    </span>
                  )
                })()}
                <span className="text-gray-600 ml-2">
                  ({Math.max(...data.map(s => s.percentage)) < 30 
                    ? 'Well-diversified across sectors' 
                    : 'Consider reducing concentration in largest sector'})
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default AllocationView
