import React, { useState, useEffect } from 'react'
import { TrendingUp, TrendingDown } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'

const HoldingsView = () => {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const { api } = useAuth()

  useEffect(() => {
    const fetchData = async () => {
      try {
        // TODO: Replace with dynamic portfolio ID
        const response = await api.get('/holdings/')
        setData(response.data)
      } catch (err) {
        setError('Failed to fetch holdings data')
        console.error(err)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [api])

  if (loading) return <div>Loading...</div>
  if (error) return <div className="text-red-500">{error}</div>
  if (!data || !Array.isArray(data)) return null

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

  const getReturnColor = (value) => {
    return value >= 0 ? 'text-green-600' : 'text-red-600'
  }

  const getReturnIcon = (value) => {
    return value >= 0 ? (
      <TrendingUp className="h-4 w-4 text-green-600" />
    ) : (
      <TrendingDown className="h-4 w-4 text-red-600" />
    )
  }

  const totalValue = data.reduce((sum, holding) => sum + holding.market_value, 0)

  const [showSellModal, setShowSellModal] = useState(false)
  const [selectedHolding, setSelectedHolding] = useState(null)
  const [sellQuantity, setSellQuantity] = useState('')
  const [sellUnitCost, setSellUnitCost] = useState('')
  const [sellError, setSellError] = useState('')
  const [isSelling, setIsSelling] = useState(false)

  const handleSellClick = (holding) => {
    setSelectedHolding(holding)
    setSellQuantity('')
    setSellUnitCost('')
    setSellError('')
    setShowSellModal(true)
  }

  const handleSellSubmit = async (e) => {
    e.preventDefault()
    setIsSelling(true)
    setSellError('')
    try {
      const response = await api.post('/assets/sell', {
        ticker: selectedHolding.ticker,
        quantity: parseFloat(sellQuantity),
        unit_cost: parseFloat(sellUnitCost),
      })
      if (!response.data.success) {
        throw new Error(response.data.message || 'Failed to sell asset')
      }
      setShowSellModal(false)
      // Optionally refresh holdings here
    } catch (err) {
      setSellError(err.message || 'Failed to sell asset')
    } finally {
      setIsSelling(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Holdings Summary */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Holdings Overview
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <p className="text-sm font-medium text-gray-500">Total Holdings</p>
            <p className="text-2xl font-semibold text-gray-900">
              {data.length}
            </p>
          </div>
          <div>
            <p className="text-sm font-medium text-gray-500">Total Value</p>
            <p className="text-2xl font-semibold text-gray-900">
              {formatCurrency(totalValue)}
            </p>
          </div>
          <div>
            <p className="text-sm font-medium text-gray-500">Avg. Weight</p>
            <p className="text-2xl font-semibold text-gray-900">
              {(100 / data.length).toFixed(1)}%
            </p>
          </div>
        </div>
      </div>
      {/* Holdings Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">
            Individual Holdings
          </h3>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Symbol
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Name
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Value
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Weight
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  1D Return
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  YTD Return
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {data.map((holding, index) => (
                <tr key={index} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-gray-900">
                      {holding.ticker}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900">{holding.asset.name}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right">
                    <div className="text-sm font-medium text-gray-900">
                      {formatCurrency(holding.market_value)}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right">
                    <div className="text-sm text-gray-900">
                      {(holding.market_value / totalValue * 100).toFixed(1)}%
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right">
                    <div
                      className={`text-sm font-medium flex items-center justify-end ${getReturnColor(
                        0
                      )}`}
                    >
                      {getReturnIcon(0)}
                      <span className="ml-1">
                        {formatPercentage(0)}
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right">
                    <div
                      className={`text-sm font-medium flex items-center justify-end ${getReturnColor(
                        holding.unrealized_gain_loss_percentage
                      )}`}
                    >
                      {getReturnIcon(holding.unrealized_gain_loss_percentage)}
                      <span className="ml-1">
                        {formatPercentage(holding.unrealized_gain_loss_percentage)}
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right">
                    <button
                      className="text-red-600 hover:underline"
                      onClick={() => handleSellClick(holding)}
                    >
                      Sell
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {/* Sell Modal */}
        {showSellModal && (
          <div className="fixed inset-0 flex items-center justify-center bg-black bg-opacity-50 z-50">
            <div className="bg-white rounded-lg p-6 shadow-lg w-96">
              <h3 className="text-lg font-semibold mb-4">
                Sell Asset: {selectedHolding?.ticker}
              </h3>
              {sellError && (
                <div className="text-red-600 mb-2">{sellError}</div>
              )}
              <form onSubmit={handleSellSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium">Quantity</label>
                  <input
                    type="number"
                    value={sellQuantity}
                    onChange={(e) => setSellQuantity(e.target.value)}
                    required
                    min="0"
                    step="any"
                    className="mt-1 block w-full border rounded-md"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium">Unit Cost</label>
                  <input
                    type="number"
                    value={sellUnitCost}
                    onChange={(e) => setSellUnitCost(e.target.value)}
                    required
                    min="0"
                    step="any"
                    className="mt-1 block w-full border rounded-md"
                  />
                </div>
                <div className="flex justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setShowSellModal(false)}
                    className="px-4 py-2 bg-gray-200 rounded"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isSelling}
                    className="px-4 py-2 bg-green-600 text-white rounded"
                  >
                    {isSelling ? 'Selling...' : 'Sell'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default HoldingsView
