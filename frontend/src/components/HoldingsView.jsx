import React, { useState, useEffect } from 'react'
import { TrendingUp, TrendingDown, Search } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'

const HoldingsView = () => {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [sortConfig, setSortConfig] = useState({ key: null, direction: 'asc' })
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

  // Filter and sort data
  const filteredData = data.filter(holding =>
    holding.ticker.toLowerCase().includes(searchTerm.toLowerCase()) ||
    holding.asset.name.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const sortedData = React.useMemo(() => {
    let sortableData = [...filteredData]
    if (sortConfig.key) {
      sortableData.sort((a, b) => {
        let aVal, bVal

        switch(sortConfig.key) {
          case 'symbol':
            aVal = a.ticker
            bVal = b.ticker
            break
          case 'name':
            aVal = a.asset.name
            bVal = b.asset.name
            break
          case 'value':
            aVal = a.market_value
            bVal = b.market_value
            break
          case 'weight':
            aVal = a.market_value / totalValue
            bVal = b.market_value / totalValue
            break
          case 'return':
            aVal = a.unrealized_gain_loss_percentage
            bVal = b.unrealized_gain_loss_percentage
            break
          default:
            return 0
        }

        if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1
        if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1
        return 0
      })
    }
    return sortableData
  }, [filteredData, sortConfig, totalValue])

  const handleSort = (key) => {
    setSortConfig(prev => ({
      key,
      direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc'
    }))
  }

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
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900">
              Individual Holdings
            </h3>
            {/* Search bar */}
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Search className="h-5 w-5 text-gray-400" />
              </div>
              <input
                type="text"
                placeholder="Search by symbol or name..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                  onClick={() => handleSort('symbol')}
                >
                  <div className="flex items-center">
                    Symbol
                    {sortConfig.key === 'symbol' && (
                      <span className="ml-1">{sortConfig.direction === 'asc' ? '↑' : '↓'}</span>
                    )}
                  </div>
                </th>
                <th
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                  onClick={() => handleSort('name')}
                >
                  <div className="flex items-center">
                    Name
                    {sortConfig.key === 'name' && (
                      <span className="ml-1">{sortConfig.direction === 'asc' ? '↑' : '↓'}</span>
                    )}
                  </div>
                </th>
                <th
                  className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                  onClick={() => handleSort('value')}
                >
                  <div className="flex items-center justify-end">
                    Value
                    {sortConfig.key === 'value' && (
                      <span className="ml-1">{sortConfig.direction === 'asc' ? '↑' : '↓'}</span>
                    )}
                  </div>
                </th>
                <th
                  className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                  onClick={() => handleSort('weight')}
                >
                  <div className="flex items-center justify-end">
                    Weight
                    {sortConfig.key === 'weight' && (
                      <span className="ml-1">{sortConfig.direction === 'asc' ? '↑' : '↓'}</span>
                    )}
                  </div>
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  1D Return
                </th>
                <th
                  className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                  onClick={() => handleSort('return')}
                >
                  <div className="flex items-center justify-end">
                    YTD Return
                    {sortConfig.key === 'return' && (
                      <span className="ml-1">{sortConfig.direction === 'asc' ? '↑' : '↓'}</span>
                    )}
                  </div>
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {sortedData.map((holding, index) => (
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
