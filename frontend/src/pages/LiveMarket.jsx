import React, { useState, useEffect, useRef } from 'react';
import { TrendingUp, TrendingDown, Activity, RefreshCw, Search } from 'lucide-react';
import { Area, AreaChart, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { useAuth } from '../contexts/AuthContext';
import { useCurrency } from '../contexts/CurrencyContext';
import toast from 'react-hot-toast';

// Tickers not supported by Finnhub
const UNSUPPORTED_TICKERS = ['MAU.TO'];

const LiveMarket = () => {
  const [holdings, setHoldings] = useState([]);
  const [chartData, setChartData] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedStock, setSelectedStock] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [sortConfig, setSortConfig] = useState({ key: null, direction: 'asc' });
  const { api } = useAuth();
  const { currency, formatCurrency: formatCurrencyFromContext } = useCurrency();
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const priceHistoryRef = useRef({});
  const autoRefreshIntervalRef = useRef(null);

  // Auto-refresh interval in milliseconds (60 seconds)
  const AUTO_REFRESH_INTERVAL = 60000;

  useEffect(() => {
    fetchLiveMarketData();

    // Set up auto-refresh interval
    autoRefreshIntervalRef.current = setInterval(() => {
      console.log('Auto-refreshing market data...');
      fetchLiveMarketData(true); // Silent update
    }, AUTO_REFRESH_INTERVAL);

    return () => {
      // Cleanup WebSocket connection
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      // Cleanup auto-refresh interval
      if (autoRefreshIntervalRef.current) {
        clearInterval(autoRefreshIntervalRef.current);
      }
    };
  }, [api, currency]);

  // WebSocket connection setup
  const connectWebSocket = (symbols) => {
    if (!symbols || symbols.length === 0) return;

    const wsUrl = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v1')
      .replace('http://', 'ws://')
      .replace('https://', 'wss://');

    try {
      const ws = new WebSocket(`${wsUrl}/market/ws`);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('WebSocket connected');
        setWsConnected(true);

        // Subscribe to symbols
        ws.send(JSON.stringify({
          type: 'subscribe',
          symbols: symbols
        }));
      };

      ws.onmessage = (event) => {
        const message = JSON.parse(event.data);

        if (message.type === 'historical') {
          // Received historical cached data
          console.log('Received historical data', message.data);

          Object.entries(message.data).forEach(([symbol, history]) => {
            if (!priceHistoryRef.current[symbol]) {
              priceHistoryRef.current[symbol] = [];
            }
            // Replace with historical data
            priceHistoryRef.current[symbol] = history;
          });

          setChartData({...priceHistoryRef.current});
          setLastUpdate(new Date());

        } else if (message.type === 'update') {
          // Received live data update
          console.log('Received live update', message.data);

          const now = Date.now();
          const currentTime = new Date().toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
          });

          Object.entries(message.data).forEach(([symbol, quote]) => {
            if (!priceHistoryRef.current[symbol]) {
              priceHistoryRef.current[symbol] = [];
            }

            // Add new data point
            priceHistoryRef.current[symbol].push({
              time: currentTime,
              price: quote.current_price,
              timestamp: now
            });

            // Keep last 200 points
            if (priceHistoryRef.current[symbol].length > 200) {
              priceHistoryRef.current[symbol].shift();
            }
          });

          setChartData({...priceHistoryRef.current});
          setLastUpdate(new Date());
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setWsConnected(false);
      };

      ws.onclose = () => {
        console.log('WebSocket closed');
        setWsConnected(false);

        // Attempt to reconnect after 5 seconds
        reconnectTimeoutRef.current = setTimeout(() => {
          console.log('Attempting to reconnect WebSocket...');
          connectWebSocket(symbols);
        }, 5000);
      };

    } catch (err) {
      console.error('Error creating WebSocket:', err);
      setWsConnected(false);
    }
  };

  const fetchLiveMarketData = async (silentUpdate = false) => {
    try {
      if (!silentUpdate) {
        setLoading(true);
      }
      setError(null);

      console.log('Fetching live market data with currency:', currency);
      const startTime = Date.now();
      const response = await api.get('/market/live', {
        params: { currency },
        timeout: 60000 // 60 second timeout for initial fetch with many holdings
      });
      console.log(`Live market data fetched in ${Date.now() - startTime}ms`);
      const holdingsData = response.data.holdings;
      setHoldings(holdingsData);
      setLastUpdate(new Date());

      // Set initial selected stock
      if (!selectedStock && holdingsData.length > 0) {
        const supported = holdingsData.filter(h => !UNSUPPORTED_TICKERS.includes(h.ticker));
        if (supported.length > 0) {
          setSelectedStock(supported[0].ticker);
        }
      }

      // Extract symbols for WebSocket subscription
      const symbols = holdingsData
        .map(h => h.ticker)
        .filter(ticker => ticker && !UNSUPPORTED_TICKERS.includes(ticker));

      // Connect to WebSocket for live updates
      if (symbols.length > 0 && !wsRef.current) {
        connectWebSocket(symbols);
      }

    } catch (err) {
      console.error('Error fetching live market data:', err);
      if (!silentUpdate) {
        const errorMsg = err.response?.data?.detail || err.message || 'Failed to fetch live market data';
        setError(errorMsg);
        toast.error(errorMsg);
      }
    } finally {
      if (!silentUpdate) {
        setLoading(false);
      }
    }
  };

  const handleRefresh = () => {
    // Clear history and restart WebSocket
    priceHistoryRef.current = {};
    setChartData({});

    // Close existing WebSocket and reconnect
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    fetchLiveMarketData();
    toast.success('Refreshing market data...');
  };

  const getDayChangePercent = (ticker) => {
    const holding = holdings.find(h => h.ticker === ticker);
    return holding?.change_percent || 0;
  };

  const calculateUnrealizedGainLoss = (holding) => {
    // CRITICAL FIX: Always calculate from quantity and prices, don't trust cached cost_basis
    const costBasis = holding.quantity * holding.average_cost;
    const currentValue = holding.quantity * holding.current_price;
    return currentValue - costBasis;
  };

  const calculateUnrealizedGainLossPercentage = (holding) => {
    // CRITICAL FIX: Calculate return % directly from prices
    const costBasis = holding.quantity * holding.average_cost;
    const gainLoss = calculateUnrealizedGainLoss(holding);
    return (gainLoss / costBasis) * 100;
  };

  const getTotalUnrealizedGainLoss = () => {
    return holdings.reduce((sum, holding) => {
      return sum + calculateUnrealizedGainLoss(holding);
    }, 0);
  };

  const getTotalUnrealizedGainLossPercentage = () => {
    // CRITICAL FIX: Calculate total cost basis from quantity * average_cost
    const totalCostBasis = holdings.reduce((sum, h) => sum + (h.quantity * h.average_cost), 0);
    const totalGainLoss = getTotalUnrealizedGainLoss();
    return totalCostBasis > 0 ? (totalGainLoss / totalCostBasis) * 100 : 0;
  };

  const formatCurrency = (value) => {
    return formatCurrencyFromContext(value);
  };

  const formatPercentage = (value) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  const getColorClass = (value) => {
    return value >= 0 ? 'text-green-600' : 'text-red-600';
  };

  const getBackgroundColor = (value) => {
    return value >= 0 ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)';
  };

  // Filter holdings
  const filteredHoldings = holdings.filter(holding =>
    holding.ticker.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (holding.asset?.name || '').toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Sort holdings
  const sortedHoldings = React.useMemo(() => {
    let sortable = [...filteredHoldings];
    if (sortConfig.key) {
      sortable.sort((a, b) => {
        let aVal, bVal;

        switch(sortConfig.key) {
          case 'asset':
            aVal = a.asset?.name || a.ticker;
            bVal = b.asset?.name || b.ticker;
            break;
          case 'symbol':
            aVal = a.ticker;
            bVal = b.ticker;
            break;
          case 'quantity':
            aVal = a.quantity;
            bVal = b.quantity;
            break;
          case 'price':
            aVal = a.current_price;
            bVal = b.current_price;
            break;
          case 'value':
            aVal = a.market_value;
            bVal = b.market_value;
            break;
          case 'dayChange':
            aVal = a.change_percent || 0;
            bVal = b.change_percent || 0;
            break;
          case 'return':
            aVal = calculateUnrealizedGainLossPercentage(a);
            bVal = calculateUnrealizedGainLossPercentage(b);
            break;
          default:
            return 0;
        }

        if (typeof aVal === 'string') {
          return sortConfig.direction === 'asc'
            ? aVal.localeCompare(bVal)
            : bVal.localeCompare(aVal);
        }

        if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1;
        if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1;
        return 0;
      });
    }
    return sortable;
  }, [filteredHoldings, sortConfig]);

  const handleSort = (key) => {
    setSortConfig(prev => ({
      key,
      direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc'
    }));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2" style={{ borderColor: 'var(--color-primary)' }}></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg p-6" style={{ backgroundColor: 'var(--color-surface)', color: 'var(--color-text)' }}>
        <p style={{ color: 'var(--color-error)' }}>{error}</p>
      </div>
    );
  }

  if (holdings.length === 0) {
    return (
      <div className="rounded-lg p-6 text-center" style={{ backgroundColor: 'var(--color-surface)', color: 'var(--color-text)' }}>
        <p>No holdings found. Add some assets to your portfolio first.</p>
      </div>
    );
  }

  const totalGainLoss = getTotalUnrealizedGainLoss();
  const totalGainLossPercentage = getTotalUnrealizedGainLossPercentage();
  const supportedHoldings = holdings.filter(h => !UNSUPPORTED_TICKERS.includes(h.ticker));

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Total Portfolio Value */}
        <div className="rounded-lg p-6" style={{ backgroundColor: 'var(--color-surface)', border: '1px solid var(--color-border)' }}>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium" style={{ color: 'var(--color-text-secondary)' }}>Total Portfolio Value</span>
            <Activity className="h-5 w-5" style={{ color: 'var(--color-primary)' }} />
          </div>
          <p className="text-2xl font-bold" style={{ color: 'var(--color-text)' }}>
            {formatCurrency(holdings.reduce((sum, h) => sum + h.market_value, 0))}
          </p>
        </div>

        {/* Total Unrealized Gain/Loss */}
        <div 
          className="rounded-lg p-6" 
          style={{ 
            backgroundColor: getBackgroundColor(totalGainLoss),
            border: '1px solid var(--color-border)' 
          }}
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium" style={{ color: 'var(--color-text-secondary)' }}>Total Unrealized Gain/Loss</span>
            {totalGainLoss >= 0 ? (
              <TrendingUp className="h-5 w-5 text-green-600" />
            ) : (
              <TrendingDown className="h-5 w-5 text-red-600" />
            )}
          </div>
          <p className={`text-2xl font-bold ${getColorClass(totalGainLoss)}`}>
            {formatCurrency(totalGainLoss)}
          </p>
          <p className={`text-sm mt-1 ${getColorClass(totalGainLoss)}`}>
            {formatPercentage(totalGainLossPercentage)}
          </p>
        </div>

        {/* Live Update Indicator */}
        <div className="rounded-lg p-6" style={{ backgroundColor: 'var(--color-surface)', border: '1px solid var(--color-border)' }}>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium" style={{ color: 'var(--color-text-secondary)' }}>Live Market Data</span>
            <div className="flex items-center space-x-2">
              <div className={`h-2 w-2 rounded-full ${wsConnected ? 'bg-green-500 animate-pulse' : 'bg-yellow-500'}`}></div>
              <span className="text-xs" style={{ color: wsConnected ? 'var(--color-success)' : 'var(--color-warning)' }}>
                {wsConnected ? 'Live (WebSocket)' : 'Polling'}
              </span>
            </div>
          </div>
          <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
            {lastUpdate ? `Updated: ${lastUpdate.toLocaleTimeString()}` : 'Connecting...'}
          </p>
          <button
            onClick={handleRefresh}
            className="mt-2 px-3 py-1 rounded text-xs font-medium flex items-center space-x-1"
            style={{ backgroundColor: 'var(--color-primary)', color: 'var(--color-btn-primary-text)' }}
          >
            <RefreshCw className="h-3 w-3" />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Stock Charts Grid */}
      {supportedHoldings.length > 0 && (
        <div className="rounded-lg p-6" style={{ backgroundColor: 'var(--color-surface)', border: '1px solid var(--color-border)' }}>
          <h3 className="text-xl font-semibold mb-4" style={{ color: 'var(--color-text)' }}>
            Live Stock Charts
          </h3>
          
          {/* Stock Selector Tabs */}
          <div className="flex flex-wrap gap-2 mb-6">
            {supportedHoldings.map((holding) => {
              const dayChangePercent = getDayChangePercent(holding.ticker);
              return (
                <button
                  key={holding.ticker}
                  onClick={() => setSelectedStock(holding.ticker)}
                  className="px-4 py-2 rounded-lg text-sm font-medium transition-all"
                  style={{
                    backgroundColor: selectedStock === holding.ticker ? 'var(--color-primary)' : 'var(--color-secondary)',
                    color: selectedStock === holding.ticker ? 'var(--color-btn-primary-text)' : 'var(--color-text)',
                    border: '1px solid var(--color-border)'
                  }}
                >
                  <div className="flex items-center space-x-2">
                    <span>{holding.ticker}</span>
                    <span className={getColorClass(dayChangePercent)}>
                      {formatPercentage(dayChangePercent)}
                    </span>
                  </div>
                </button>
              );
            })}
          </div>

          {/* Selected Stock Chart */}
          {selectedStock && chartData[selectedStock] && chartData[selectedStock].length > 0 && (
            <div>
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h4 className="text-lg font-semibold" style={{ color: 'var(--color-text)' }}>
                    {holdings.find(h => h.ticker === selectedStock)?.asset?.name || selectedStock}
                  </h4>
                  <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
                    {selectedStock}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-2xl font-bold" style={{ color: 'var(--color-text)' }}>
                    {formatCurrency(chartData[selectedStock][chartData[selectedStock].length - 1].price)}
                  </p>
                  <p className={`text-sm font-medium ${getColorClass(getDayChangePercent(selectedStock))}`}>
                    {formatPercentage(getDayChangePercent(selectedStock))}
                  </p>
                </div>
              </div>

              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={chartData[selectedStock]}>
                  <defs>
                    <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="var(--color-primary)" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="var(--color-primary)" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                  <XAxis 
                    dataKey="time" 
                    stroke="var(--color-text-secondary)"
                    style={{ fontSize: '12px' }}
                    interval="preserveStartEnd"
                  />
                  <YAxis 
                    stroke="var(--color-text-secondary)"
                    style={{ fontSize: '12px' }}
                    domain={['auto', 'auto']}
                    tickFormatter={(value) => `$${value.toFixed(2)}`}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'var(--color-surface)',
                      border: '1px solid var(--color-border)',
                      borderRadius: '8px',
                      color: 'var(--color-text)'
                    }}
                    formatter={(value) => [formatCurrency(value), 'Price']}
                  />
                  <Area 
                    type="monotone" 
                    dataKey="price" 
                    stroke="var(--color-primary)" 
                    strokeWidth={2}
                    fill="url(#colorPrice)"
                  />
                </AreaChart>
              </ResponsiveContainer>
              
              <p className="text-xs text-center mt-2" style={{ color: 'var(--color-text-secondary)' }}>
                {wsConnected ? 'Chart shows historical + live WebSocket updates' : 'Chart shows real-time price updates'}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Holdings Table */}
      <div className="rounded-lg overflow-hidden" style={{ backgroundColor: 'var(--color-surface)', border: '1px solid var(--color-border)' }}>
        <div className="px-6 py-4" style={{ borderBottom: '1px solid var(--color-border)' }}>
          <div className="flex items-center justify-between">
            <h3 className="text-xl font-semibold" style={{ color: 'var(--color-text)' }}>
              Detailed Holdings
            </h3>
            {/* Search bar */}
            <div className="relative w-80">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 pointer-events-none" style={{ color: 'var(--color-text-secondary)' }} />
              <input
                type="text"
                placeholder="Search by symbol or name..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pr-4 py-2 rounded-md focus:ring-2 focus:outline-none"
                style={{
                  paddingLeft: '2.5rem',
                  backgroundColor: 'var(--color-secondary)',
                  border: '1px solid var(--color-border)',
                  color: 'var(--color-text)',
                }}
              />
            </div>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y" style={{ borderColor: 'var(--color-border)' }}>
            <thead style={{ backgroundColor: 'var(--color-secondary)' }}>
              <tr>
                <th
                  className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider cursor-pointer hover:bg-gray-700"
                  style={{ color: 'var(--color-text-secondary)' }}
                  onClick={() => handleSort('asset')}
                >
                  <div className="flex items-center">
                    Asset
                    {sortConfig.key === 'asset' && (
                      <span className="ml-1">{sortConfig.direction === 'asc' ? '↑' : '↓'}</span>
                    )}
                  </div>
                </th>
                <th
                  className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider cursor-pointer hover:bg-gray-700"
                  style={{ color: 'var(--color-text-secondary)' }}
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
                  className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider cursor-pointer hover:bg-gray-700"
                  style={{ color: 'var(--color-text-secondary)' }}
                  onClick={() => handleSort('quantity')}
                >
                  <div className="flex items-center justify-end">
                    Quantity
                    {sortConfig.key === 'quantity' && (
                      <span className="ml-1">{sortConfig.direction === 'asc' ? '↑' : '↓'}</span>
                    )}
                  </div>
                </th>
                <th
                  className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider cursor-pointer hover:bg-gray-700"
                  style={{ color: 'var(--color-text-secondary)' }}
                  onClick={() => handleSort('price')}
                >
                  <div className="flex items-center justify-end">
                    Current Price
                    {sortConfig.key === 'price' && (
                      <span className="ml-1">{sortConfig.direction === 'asc' ? '↑' : '↓'}</span>
                    )}
                  </div>
                </th>
                <th
                  className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider cursor-pointer hover:bg-gray-700"
                  style={{ color: 'var(--color-text-secondary)' }}
                  onClick={() => handleSort('value')}
                >
                  <div className="flex items-center justify-end">
                    Market Value
                    {sortConfig.key === 'value' && (
                      <span className="ml-1">{sortConfig.direction === 'asc' ? '↑' : '↓'}</span>
                    )}
                  </div>
                </th>
                <th
                  className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider cursor-pointer hover:bg-gray-700"
                  style={{ color: 'var(--color-text-secondary)' }}
                  onClick={() => handleSort('dayChange')}
                >
                  <div className="flex items-center justify-end">
                    Day Change
                    {sortConfig.key === 'dayChange' && (
                      <span className="ml-1">{sortConfig.direction === 'asc' ? '↑' : '↓'}</span>
                    )}
                  </div>
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--color-text-secondary)' }}>
                  Unrealized Gain/Loss
                </th>
                <th
                  className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider cursor-pointer hover:bg-gray-700"
                  style={{ color: 'var(--color-text-secondary)' }}
                  onClick={() => handleSort('return')}
                >
                  <div className="flex items-center justify-end">
                    Return %
                    {sortConfig.key === 'return' && (
                      <span className="ml-1">{sortConfig.direction === 'asc' ? '↑' : '↓'}</span>
                    )}
                  </div>
                </th>
              </tr>
            </thead>
            <tbody className="divide-y" style={{ backgroundColor: 'var(--color-surface)', borderColor: 'var(--color-border)' }}>
              {sortedHoldings.map((holding) => {
                const unrealizedGainLoss = calculateUnrealizedGainLoss(holding);
                const unrealizedGainLossPercentage = calculateUnrealizedGainLossPercentage(holding);
                const dayChange = holding.change_percent || 0;
                
                return (
                  <tr key={holding.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium" style={{ color: 'var(--color-text)' }}>
                        {holding.asset?.name || holding.ticker}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium" style={{ color: 'var(--color-text)' }}>
                        {holding.ticker}
                        {UNSUPPORTED_TICKERS.includes(holding.ticker) && (
                          <span className="ml-2 text-xs" style={{ color: 'var(--color-text-secondary)' }}>
                            (No live data)
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm" style={{ color: 'var(--color-text)' }}>
                      {holding.quantity.toFixed(4)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium" style={{ color: 'var(--color-text)' }}>
                      {formatCurrency(holding.current_price)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium" style={{ color: 'var(--color-text)' }}>
                      {formatCurrency(holding.market_value)}
                    </td>
                    <td className={`px-6 py-4 whitespace-nowrap text-right text-sm font-medium ${getColorClass(dayChange)}`}>
                      {formatPercentage(dayChange)}
                    </td>
                    <td className={`px-6 py-4 whitespace-nowrap text-right text-sm font-medium ${getColorClass(unrealizedGainLoss)}`}>
                      {formatCurrency(unrealizedGainLoss)}
                    </td>
                    <td className={`px-6 py-4 whitespace-nowrap text-right text-sm font-medium ${getColorClass(unrealizedGainLoss)}`}>
                      {formatPercentage(unrealizedGainLossPercentage)}
                    </td>
                  </tr>
                );
              })}
              {/* Total Row */}
              <tr className="font-bold" style={{ backgroundColor: 'var(--color-secondary)' }}>
                <td className="px-6 py-4 whitespace-nowrap text-sm" style={{ color: 'var(--color-text)' }}>
                  Total
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm"></td>
                <td className="px-6 py-4 whitespace-nowrap text-sm"></td>
                <td className="px-6 py-4 whitespace-nowrap text-sm"></td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm" style={{ color: 'var(--color-text)' }}>
                  {formatCurrency(holdings.reduce((sum, h) => sum + h.market_value, 0))}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm"></td>
                <td className={`px-6 py-4 whitespace-nowrap text-right text-sm ${getColorClass(totalGainLoss)}`}>
                  {formatCurrency(totalGainLoss)}
                </td>
                <td className={`px-6 py-4 whitespace-nowrap text-right text-sm ${getColorClass(totalGainLoss)}`}>
                  {formatPercentage(totalGainLossPercentage)}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default LiveMarket;
