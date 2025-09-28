import React, { useState, useEffect } from 'react'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts'
import { useAuth } from '../contexts/AuthContext'

const AllocationSection = () => {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const { api } = useAuth()

  useEffect(() => {
    const fetchData = async () => {
      try {
        // TODO: Replace with dynamic portfolio ID
        const response = await api.get('/analysis/portfolios/1/analysis/sector-allocation')
        setData(response.data)
      } catch (err) {
        setError('Failed to fetch allocation data')
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

  const assetAllocation = data || {}

  const formatPercentage = (value) => {
    if (typeof value !== 'number') return 'N/A'
    return `${value.toFixed(1)}%`
  }

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value)
  }

  // Prepare data for pie chart
  const pieData = Object.entries(assetAllocation).map(([sector, allocation], index) => ({
    name: sector,
    value: allocation.percentage,
    color: `hsl(${index * 36}, 70%, 50%)`
  }))

  // Prepare data for bar chart (asset values)
  const barData = Object.entries(assetAllocation).map(([sector, allocation]) => ({
    sector,
    value: allocation.value,
    percentage: allocation.percentage
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
          <p className="font-medium">{data.name || data.sector}</p>
          <p className="text-sm">{formatCurrency(data.value)}</p>
          <p className="text-sm">{formatPercentage(data.percentage)}</p>
        </div>
      )
    }
    return null
  }

  const totalSectors = Object.keys(assetAllocation).length
  const largestAllocation = Math.max(...Object.values(assetAllocation).map(a => a.percentage))

  return (
    <div className="space-y-8">
      <div>
        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
            <div className="text-center">
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">Total Sectors</p>
              <p className="text-3xl font-bold text-gray-900 dark:text-white">{totalSectors}</p>
            </div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
            <div className="text-center">
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">Total Allocated</p>
              <p className="text-3xl font-bold text-gray-900 dark:text-white">{formatCurrency(Object.values(assetAllocation).reduce((acc, a) => acc + a.value, 0))}</p>
            </div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
            <div className="text-center">
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">Largest Sector</p>
              <p className="text-3xl font-bold text-gray-900 dark:text-white">{formatPercentage(largestAllocation)}</p>
            </div>
          </div>
        </div>

        {/* Charts Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
          {/* Pie Chart */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
            <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">
              Sector Composition
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
              Sector Values
            </h3>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={barData} margin={{ top: 20, right: 30, left: 20, bottom: 60 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.2} />
                  <XAxis 
                    dataKey="sector" 
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
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Sector Breakdown</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-700">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Sector
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
                  .sort(([,a], [,b]) => b.value - a.value)
                  .map(([sector, allocation], index) => (
                  <tr key={sector} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div 
                          className="h-3 w-3 rounded-full mr-3"
                          style={{ backgroundColor: COLORS[index % COLORS.length] }}
                        ></div>
                        <div className="text-sm font-medium text-gray-900 dark:text-white">
                          {sector}
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right">
                      <div className="text-sm font-medium text-gray-900 dark:text-white">
                        {formatCurrency(allocation.value)}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right">
                      <div className="text-sm text-gray-900 dark:text-white">
                        {formatPercentage(allocation.percentage)}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right">
                      <div className="flex items-center justify-end">
                        <div className="w-20 bg-gray-200 dark:bg-gray-600 rounded-full h-2">
                          <div 
                            className="h-2 rounded-full transition-all duration-300"
                            style={{ 
                              width: `${allocation.percentage}%`,
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
      </div>
    </div>
  )
}

export default AllocationSection
