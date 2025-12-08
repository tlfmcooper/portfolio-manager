import React, { useState, useEffect } from 'react'
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { Target, Info } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { useAgentContext } from '../contexts/AgentContext'
import { useCurrency } from '../contexts/CurrencyContext'

const EfficientFrontierSection = () => {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const { api, portfolioId } = useAuth()
  const { frontierParams, globalParams } = useAgentContext()
  const { currency: contextCurrency } = useCurrency()

  // Determine effective currency: Frontier-specific > Global Agent > App Context
  const currency = frontierParams.currency || globalParams.currency || contextCurrency

  useEffect(() => {
    const fetchData = async () => {
      if (!portfolioId) {
        setLoading(false);
        return;
      }

      try {
        setLoading(true)
        const response = await api.get(`/analysis/portfolios/${portfolioId}/efficient-frontier`, {
          params: { currency }
        })
        setData(response.data)
      } catch (err) {
        setError('Failed to fetch efficient frontier data')
        console.error(err)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [api, portfolioId, currency])

  if (loading) return <div>Loading...</div>
  if (error) return <div className="text-red-500">{error}</div>
  if (!data) return null

  const efficientFrontier = data || {}
  const frontierPoints = efficientFrontier.frontier_points || []
  const specialPortfolios = efficientFrontier.special_portfolios || {}

  const formatPercentage = (value) => {
    if (typeof value !== 'number') return 'N/A'
    return `${(value * 100).toFixed(2)}%`
  }

  // Prepare data for the scatter chart
  const frontierData = frontierPoints.map((point, index) => ({
    risk: (point.risk * 100) || 0,
    return: (point.return * 100) || 0,
    type: 'frontier',
    id: index
  }))

  // Special portfolios data
  // Special portfolios data
  const SPECIAL_PORTFOLIO_ORDER = ['current', 'msr', 'gmv']
  
  const specialData = Object.entries(specialPortfolios)
    .sort(([keyA], [keyB]) => {
      const indexA = SPECIAL_PORTFOLIO_ORDER.indexOf(keyA)
      const indexB = SPECIAL_PORTFOLIO_ORDER.indexOf(keyB)
      // If both are in the list, sort by index
      if (indexA !== -1 && indexB !== -1) return indexA - indexB
      // If only A is in the list, it comes first
      if (indexA !== -1) return -1
      // If only B is in the list, it comes first
      if (indexB !== -1) return 1
      // If neither, keep original order (or sort alphabetically if preferred)
      return 0
    })
    .map(([key, portfolio]) => ({
      risk: (portfolio.risk * 100) || 0,
      return: (portfolio.return * 100) || 0,
      name: portfolio.name,
      type: key,
      size: 200
    }))

  // Combine all data for the chart
  const allData = [
    ...frontierData,
    ...specialData
  ]

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload
      return (
        <div className="bg-gray-900 text-white p-3 rounded-lg border border-gray-700">
          <p className="font-medium">
            {data.name || (data.type === 'frontier' ? 'Efficient Frontier' : 'Portfolio')}
          </p>
          <p className="text-sm">Risk: {data.risk.toFixed(2)}%</p>
          <p className="text-sm">Return: {data.return.toFixed(2)}%</p>
          {data.type !== 'frontier' && (
            <p className="text-xs text-gray-300 mt-1">
              Sharpe Ratio: {((data.return - 2) / data.risk).toFixed(3)}
            </p>
          )}
        </div>
      )
    }
    return null
  }

  const getPortfolioColor = (type) => {
    switch (type) {
      case 'current': return '#EF4444'  // Red
      case 'msr': return '#F59E0B'      // Orange
      case 'gmv': return '#10B981'      // Green
      default: return '#3B82F6'        // Blue
    }
  }

  const getPortfolioShape = (type) => {
    switch (type) {
      case 'current': return 'star'
      case 'msr': return 'triangle'
      case 'gmv': return 'square'
      default: return 'circle'
    }
  }

  return (
    <div className="space-y-8">
      <div>
        {/* Explanation Card */}
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-6 mb-8">
          <div className="flex items-start">
            <Target className="h-6 w-6 text-blue-600 dark:text-blue-400 mt-1 mr-3 flex-shrink-0" />
            <div>
              <h4 className="text-lg font-semibold text-blue-900 dark:text-blue-100 mb-2">
                Understanding the Efficient Frontier
              </h4>
              <p className="text-blue-800 dark:text-blue-200">
                The efficient frontier shows optimal risk-return combinations. Portfolios on the frontier provide 
                maximum return for each level of risk. Your current portfolio (marked with a star) sits near the 
                efficient frontier, indicating good optimization relative to the available investment universe.
              </p>
            </div>
          </div>
        </div>

        {/* Special Portfolios Summary */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          {Object.entries(specialPortfolios).map(([key, portfolio]) => {
            const sharpeRatio = ((portfolio.return - 0.02) / portfolio.risk) || 0
            const color = getPortfolioColor(key)
            
            return (
              <div 
                key={key}
                className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6"
              >
                <div className="flex items-center mb-3">
                  <div 
                    className="w-4 h-4 rounded mr-3"
                    style={{ backgroundColor: color }}
                  ></div>
                  <h4 className="font-semibold text-gray-900 dark:text-white text-sm">
                    {portfolio.name}
                  </h4>
                </div>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-500 dark:text-gray-400">Expected Return:</span>
                    <span className="font-medium text-gray-900 dark:text-white">
                      {formatPercentage(portfolio.return)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500 dark:text-gray-400">Risk (Volatility):</span>
                    <span className="font-medium text-gray-900 dark:text-white">
                      {formatPercentage(portfolio.risk)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500 dark:text-gray-400">Sharpe Ratio:</span>
                    <span className="font-medium text-gray-900 dark:text-white">
                      {sharpeRatio.toFixed(3)}
                    </span>
                  </div>
                </div>
              </div>
            )
          })}
        </div>

        {/* Efficient Frontier Chart */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">
            Risk-Return Optimization
          </h3>
          <div className="h-[500px] md:h-96">
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart
                margin={{ top: 80, right: 30, bottom: 60, left: 60 }}
                data={allData}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.2} />
                <XAxis 
                  type="number"
                  dataKey="risk"
                  domain={['dataMin - 1', 'dataMax + 1']}
                  tick={{ fontSize: 12, fill: '#6B7280' }}
                  stroke="#6B7280"
                  tickFormatter={(value) => `${value.toFixed(2)}%`}
                  label={{ 
                    value: 'Risk (Volatility %)', 
                    position: 'insideBottom', 
                    offset: -10,
                    style: { textAnchor: 'middle', fill: '#6B7280' }
                  }}
                />
                <YAxis 
                  type="number"
                  dataKey="return"
                  domain={['dataMin - 1', 'dataMax + 1']}
                  tick={{ fontSize: 12, fill: '#6B7280' }}
                  stroke="#6B7280"
                  tickFormatter={(value) => `${value.toFixed(2)}%`}
                  width={80}
                  label={{ 
                    value: 'Expected Return (%)', 
                    angle: -90, 
                    position: 'insideLeft',
                    style: { textAnchor: 'middle', fill: '#6B7280' }
                  }}
                />
                <Tooltip content={<CustomTooltip />} />
                
                {/* Efficient Frontier Line */}
                <Scatter
                  data={frontierData}
                  fill="#3B82F6"
                  name="Efficient Frontier"
                  line={{ stroke: '#3B82F6', strokeWidth: 2 }}
                  shape="circle"
                />
                
                {/* Special Portfolios */}
                {specialData.map((portfolio, index) => (
                  <Scatter
                    key={portfolio.type}
                    data={[portfolio]}
                    fill={getPortfolioColor(portfolio.type)}
                    name={portfolio.name}
                    shape={getPortfolioShape(portfolio.type)}
                    legendType={getPortfolioShape(portfolio.type)}
                  />
                ))}
                
                <Legend 
                  verticalAlign="top"
                  wrapperStyle={{ marginTop: '-20px', paddingLeft: '10px' }}
                  formatter={(value, entry) => (
                    <span style={{ color: entry.color }}>
                      {value}
                    </span>
                  )}
                />
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Portfolio Analysis */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">
            Portfolio Position Analysis
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h4 className="font-medium text-gray-900 dark:text-white mb-3">Optimization Score</h4>
              <div className="space-y-3">
                {(() => {
                  const current = specialPortfolios.current
                  if (!current) return <p className="text-gray-500">No current portfolio data</p>
                  
                  const currentSharpe = (current.return - 0.02) / current.risk
                  const msrSharpe = specialPortfolios.msr ? (specialPortfolios.msr.return - 0.02) / specialPortfolios.msr.risk : 0
                  const efficiency = msrSharpe > 0 ? (currentSharpe / msrSharpe) * 100 : 0
                  
                  return (
                    <>
                      <div className="flex justify-between items-center">
                        <span className="text-gray-600 dark:text-gray-400">Current Sharpe Ratio:</span>
                        <span className="font-medium text-gray-900 dark:text-white">
                          {currentSharpe.toFixed(3)}
                        </span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-gray-600 dark:text-gray-400">Optimal Sharpe Ratio:</span>
                        <span className="font-medium text-gray-900 dark:text-white">
                          {msrSharpe.toFixed(3)}
                        </span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-gray-600 dark:text-gray-400">Efficiency Score:</span>
                        <span className={`font-medium ${
                          efficiency >= 90 ? 'text-green-600' :
                          efficiency >= 75 ? 'text-yellow-600' : 'text-red-600'
                        }`}>
                          {efficiency.toFixed(1)}%
                        </span>
                      </div>
                    </>
                  )
                })()}
              </div>
            </div>
            <div>
              <h4 className="font-medium text-gray-900 dark:text-white mb-3">Improvement Potential</h4>
              <div className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
                <p>
                  • Your portfolio is positioned {(() => {
                    const current = specialPortfolios.current
                    const msr = specialPortfolios.msr
                    if (!current || !msr) return 'reasonably'
                    
                    const riskDiff = Math.abs(current.risk - msr.risk)
                    return riskDiff < 0.02 ? 'very close to' : riskDiff < 0.05 ? 'near' : 'away from'
                  })()} the optimal risk-return frontier
                </p>
                <p>
                  • Consider rebalancing toward the Maximum Sharpe Ratio portfolio for better risk-adjusted returns
                </p>
                <p>
                  • The Global Minimum Volatility portfolio offers lower risk but potentially lower returns
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default EfficientFrontierSection
