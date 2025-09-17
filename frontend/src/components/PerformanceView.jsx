import React from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

const PerformanceView = ({ data }) => {
  if (!data) return null

  const formatPercentage = (value) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
  }

  const formatRatio = (value) => {
    return value.toFixed(3)
  }

  const getColorForValue = (value, isPositiveBetter = true) => {
    if (isPositiveBetter) {
      return value >= 0 ? 'text-green-600' : 'text-red-600'
    } else {
      return value <= 0 ? 'text-green-600' : 'text-red-600'
    }
  }

  // Prepare chart data
  const chartData = [
    { name: 'Sharpe Ratio', value: data.sharpe_ratio, color: '#3B82F6' },
    { name: 'Alpha', value: data.alpha, color: '#10B981' },
    { name: 'Beta', value: data.beta, color: '#F59E0B' },
    { name: 'Volatility', value: data.volatility, color: '#EF4444' },
  ]

  return (
    <div className="space-y-6">
      {/* Performance Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
        {/* Sharpe Ratio */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-center">
            <p className="text-sm font-medium text-gray-500 mb-2">Sharpe Ratio</p>
            <p className={`text-3xl font-bold ${getColorForValue(data.sharpe_ratio)}`}>
              {formatRatio(data.sharpe_ratio)}
            </p>
            <p className="text-xs text-gray-400 mt-1">Risk-adjusted return</p>
          </div>
        </div>

        {/* Max Drawdown */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-center">
            <p className="text-sm font-medium text-gray-500 mb-2">Max Drawdown</p>
            <p className={`text-3xl font-bold ${getColorForValue(data.max_drawdown, false)}`}>
              {formatPercentage(data.max_drawdown)}
            </p>
            <p className="text-xs text-gray-400 mt-1">Worst peak-to-trough</p>
          </div>
        </div>
        {/* Volatility */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-center">
            <p className="text-sm font-medium text-gray-500 mb-2">Volatility</p>
            <p className={`text-3xl font-bold ${getColorForValue(data.volatility, false)}`}>
              {formatPercentage(data.volatility)}
            </p>
            <p className="text-xs text-gray-400 mt-1">Price fluctuation</p>
          </div>
        </div>

        {/* Beta */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-center">
            <p className="text-sm font-medium text-gray-500 mb-2">Beta</p>
            <p className={`text-3xl font-bold ${
              data.beta > 1 ? 'text-red-600' : 
              data.beta < 0.8 ? 'text-green-600' : 'text-yellow-600'
            }`}>
              {formatRatio(data.beta)}
            </p>
            <p className="text-xs text-gray-400 mt-1">Market sensitivity</p>
          </div>
        </div>

        {/* Alpha */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-center">
            <p className="text-sm font-medium text-gray-500 mb-2">Alpha</p>
            <p className={`text-3xl font-bold ${getColorForValue(data.alpha)}`}>
              {formatPercentage(data.alpha)}
            </p>
            <p className="text-xs text-gray-400 mt-1">Excess return</p>
          </div>
        </div>
      </div>

      {/* Performance Chart */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Performance Metrics Visualization</h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis 
                dataKey="name" 
                tick={{ fontSize: 12 }}
                angle={-45}
                textAnchor="end"
                height={80}
              />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip 
                formatter={(value) => [value.toFixed(3), '']}
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
      {/* Metrics Explanation */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Understanding Your Metrics</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-sm">
          <div>
            <h4 className="font-medium text-gray-900 mb-2">Sharpe Ratio ({formatRatio(data.sharpe_ratio)})</h4>
            <p className="text-gray-600">
              Measures risk-adjusted return. Higher values indicate better performance per unit of risk.
              {data.sharpe_ratio > 1 ? ' Excellent risk-adjusted performance.' :
               data.sharpe_ratio > 0.5 ? ' Good risk-adjusted performance.' :
               ' Consider reviewing risk management.'}
            </p>
          </div>
          
          <div>
            <h4 className="font-medium text-gray-900 mb-2">Alpha ({formatPercentage(data.alpha)})</h4>
            <p className="text-gray-600">
              Excess return compared to market benchmark.
              {data.alpha > 0 ? ' Your portfolio is outperforming the market.' :
               ' Your portfolio is underperforming the market.'}
            </p>
          </div>
          
          <div>
            <h4 className="font-medium text-gray-900 mb-2">Beta ({formatRatio(data.beta)})</h4>
            <p className="text-gray-600">
              Market sensitivity. 1.0 = market-level volatility.
              {data.beta > 1 ? ' Higher volatility than market.' :
               data.beta < 0.8 ? ' Lower volatility than market.' :
               ' Similar volatility to market.'}
            </p>
          </div>
          
          <div>
            <h4 className="font-medium text-gray-900 mb-2">Volatility ({formatPercentage(data.volatility)})</h4>
            <p className="text-gray-600">
              Price fluctuation measure.
              {data.volatility < 10 ? ' Low volatility portfolio.' :
               data.volatility < 20 ? ' Moderate volatility portfolio.' :
               ' High volatility portfolio.'}
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default PerformanceView
