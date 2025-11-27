import React, { useState, useEffect } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { useAuth } from '../contexts/AuthContext'

const PerformanceView = () => {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const { api, portfolioId } = useAuth() // CRITICAL FIX: Get portfolioId from context

  useEffect(() => {
    const fetchData = async () => {
      if (!portfolioId) return; // Wait for portfolioId to load

      try {
        const response = await api.get(`/analysis/portfolios/${portfolioId}/metrics`) // CRITICAL FIX: Use dynamic portfolioId
        setData(response.data)
      } catch (err) {
        setError('Failed to fetch performance data')
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

  const formatPercentage = (value) => {
    return `${value >= 0 ? '+' : ''}${(value * 100).toFixed(2)}%`
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
    { name: 'Volatility', value: data.portfolio_volatility_annualized, color: '#EF4444' },
  ]

  return (
    <div className="space-y-6">
      {/* Performance Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
        {/* Sharpe Ratio */}
        <div className="rounded-lg shadow p-6" style={{ backgroundColor: 'var(--color-surface)' }}>
          <div className="text-center">
            <p className="text-sm font-medium mb-2" style={{ color: 'var(--color-text-secondary)' }}>Sharpe Ratio</p>
            <p className={`text-3xl font-bold ${getColorForValue(data.sharpe_ratio)}`}>
              {formatRatio(data.sharpe_ratio)}
            </p>
            <p className="text-xs mt-1" style={{ color: 'var(--color-text-secondary)' }}>Risk-adjusted return</p>
          </div>
        </div>

        {/* Max Drawdown */}
        <div className="rounded-lg shadow p-6" style={{ backgroundColor: 'var(--color-surface)' }}>
          <div className="text-center">
            <p className="text-sm font-medium mb-2" style={{ color: 'var(--color-text-secondary)' }}>Max Drawdown</p>
            <p className={`text-3xl font-bold ${getColorForValue(data.max_drawdown, false)}`}>
              {formatPercentage(data.max_drawdown)}
            </p>
            <p className="text-xs mt-1" style={{ color: 'var(--color-text-secondary)' }}>Worst peak-to-trough</p>
          </div>
        </div>
        {/* Volatility */}
        <div className="rounded-lg shadow p-6" style={{ backgroundColor: 'var(--color-surface)' }}>
          <div className="text-center">
            <p className="text-sm font-medium mb-2" style={{ color: 'var(--color-text-secondary)' }}>Volatility</p>
            <p className={`text-3xl font-bold ${getColorForValue(data.portfolio_volatility_annualized, false)}`}>
              {formatPercentage(data.portfolio_volatility_annualized)}
            </p>
            <p className="text-xs mt-1" style={{ color: 'var(--color-text-secondary)' }}>Price fluctuation</p>
          </div>
        </div>
      </div>

      {/* Performance Chart */}
      <div className="rounded-lg shadow p-6" style={{ backgroundColor: 'var(--color-surface)' }}>
        <h3 className="text-lg font-semibold mb-4" style={{ color: 'var(--color-text)' }}>Performance Metrics Visualization</h3>
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
      <div className="rounded-lg shadow p-6" style={{ backgroundColor: 'var(--color-surface)' }}>
        <h3 className="text-lg font-semibold mb-4" style={{ color: 'var(--color-text)' }}>Understanding Your Metrics</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-sm">
          <div>
            <h4 className="font-medium mb-2" style={{ color: 'var(--color-text)' }}>Sharpe Ratio ({formatRatio(data.sharpe_ratio)})</h4>
            <p style={{ color: 'var(--color-text-secondary)' }}>
              Measures risk-adjusted return. Higher values indicate better performance per unit of risk.
              {data.sharpe_ratio > 1 ? ' Excellent risk-adjusted performance.' :
               data.sharpe_ratio > 0.5 ? ' Good risk-adjusted performance.' :
               ' Consider reviewing risk management.'}
            </p>
          </div>
          
          <div>
            <h4 className="font-medium mb-2" style={{ color: 'var(--color-text)' }}>Volatility ({formatPercentage(data.portfolio_volatility_annualized)})</h4>
            <p style={{ color: 'var(--color-text-secondary)' }}>
              Price fluctuation measure.
              {data.portfolio_volatility_annualized < 10 ? ' Low volatility portfolio.' :
               data.portfolio_volatility_annualized < 20 ? ' Moderate volatility portfolio.' :
               ' High volatility portfolio.'}
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default PerformanceView
