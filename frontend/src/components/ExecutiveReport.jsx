import React from 'react'
import { TrendingUp, TrendingDown, DollarSign, AlertTriangle } from 'lucide-react'

const ExecutiveReport = ({ data }) => {
  if (!data) return null

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value)
  }

  const formatPercentage = (value) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
  }

  const getRiskColor = (score) => {
    if (score <= 3) return 'text-green-600'
    if (score <= 6) return 'text-yellow-600'
    return 'text-red-600'
  }

  const getRiskLabel = (score) => {
    if (score <= 3) return 'Low Risk'
    if (score <= 6) return 'Medium Risk'
    return 'High Risk'
  }

  return (
    <div className="space-y-6">
      {/* Key Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Total Portfolio Value */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <DollarSign className="h-8 w-8 text-blue-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Total Value</p>
              <p className="text-2xl font-semibold text-gray-900">
                {formatCurrency(data.total_portfolio_value)}
              </p>
            </div>
          </div>
        </div>
        {/* Total Return */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              {data.total_return >= 0 ? (
                <TrendingUp className="h-8 w-8 text-green-600" />
              ) : (
                <TrendingDown className="h-8 w-8 text-red-600" />
              )}
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Total Return</p>
              <p className={`text-2xl font-semibold ${
                data.total_return >= 0 ? 'text-green-600' : 'text-red-600'
              }`}>
                {formatPercentage(data.total_return)}
              </p>
            </div>
          </div>
        </div>

        {/* YTD Performance */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              {data.ytd_performance >= 0 ? (
                <TrendingUp className="h-8 w-8 text-green-600" />
              ) : (
                <TrendingDown className="h-8 w-8 text-red-600" />
              )}
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">YTD Performance</p>
              <p className={`text-2xl font-semibold ${
                data.ytd_performance >= 0 ? 'text-green-600' : 'text-red-600'
              }`}>
                {formatPercentage(data.ytd_performance)}
              </p>
            </div>
          </div>
        </div>
        {/* Risk Score */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <AlertTriangle className={`h-8 w-8 ${getRiskColor(data.risk_score)}`} />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Risk Score</p>
              <p className={`text-2xl font-semibold ${getRiskColor(data.risk_score)}`}>
                {data.risk_score.toFixed(1)}/10
              </p>
              <p className={`text-sm ${getRiskColor(data.risk_score)}`}>
                {getRiskLabel(data.risk_score)}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Summary Section */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Portfolio Summary</h3>
        <div className="prose max-w-none">
          <p className="text-gray-600 mb-4">
            Your portfolio is currently valued at{' '}
            <span className="font-semibold text-gray-900">
              {formatCurrency(data.total_portfolio_value)}
            </span>
            {' '}with a total return of{' '}
            <span className={`font-semibold ${
              data.total_return >= 0 ? 'text-green-600' : 'text-red-600'
            }`}>
              {formatPercentage(data.total_return)}
            </span>
            {'. '}
            Year-to-date performance stands at{' '}
            <span className={`font-semibold ${
              data.ytd_performance >= 0 ? 'text-green-600' : 'text-red-600'
            }`}>
              {formatPercentage(data.ytd_performance)}
            </span>
            {'.'}
          </p>
          
          <p className="text-gray-600">
            The portfolio maintains a risk score of{' '}
            <span className={`font-semibold ${getRiskColor(data.risk_score)}`}>
              {data.risk_score.toFixed(1)} ({getRiskLabel(data.risk_score)})
            </span>
            {', indicating '}
            {data.risk_score <= 3 && 'a conservative investment approach with stable returns.'}
            {data.risk_score > 3 && data.risk_score <= 6 && 'a balanced approach between growth and stability.'}
            {data.risk_score > 6 && 'an aggressive growth strategy with higher volatility potential.'}
          </p>

          <div className="mt-4 text-sm text-gray-500">
            <p>Last updated: {new Date(data.last_updated).toLocaleString()}</p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ExecutiveReport
