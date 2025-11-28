import React, { useState, useEffect } from 'react';
import { DollarSign, Plus, TrendingUp, TrendingDown, ChevronDown, ChevronUp } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useCurrency } from '../contexts/CurrencyContext';

const CashBalance = ({ onAddCash }) => {
  const [cashData, setCashData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [realizedGains, setRealizedGains] = useState(null);
  const [realizedGainsDetailed, setRealizedGainsDetailed] = useState(null);
  const [showDetailedTable, setShowDetailedTable] = useState(false);
  const { api, portfolioId } = useAuth();
  const { currentCurrency, formatCurrency } = useCurrency();

  useEffect(() => {
    fetchCashBalance();
    fetchRealizedGains();
    fetchRealizedGainsDetailed();
  }, [portfolioId, currentCurrency]);

  const fetchCashBalance = async () => {
    if (!portfolioId) return;

    try {
      setLoading(true);
      const response = await api.get(
        `/portfolios/${portfolioId}/cash/balance`,
        { params: { currency: currentCurrency } }
      );
      setCashData(response.data);
    } catch (error) {
      console.error('Error fetching cash balance:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchRealizedGains = async () => {
    if (!portfolioId) return;

    try {
      const response = await api.get(`/portfolios/${portfolioId}/realized-gains`);
      setRealizedGains(response.data);
    } catch (error) {
      console.error('Error fetching realized gains:', error);
    }
  };

  const fetchRealizedGainsDetailed = async () => {
    if (!portfolioId) return;

    try {
      const response = await api.get(`/portfolios/${portfolioId}/realized-gains/detailed`);
      setRealizedGainsDetailed(response.data);
    } catch (error) {
      console.error('Error fetching detailed realized gains:', error);
    }
  };

  if (loading) {
    return (
      <div
        className="rounded-lg shadow p-6 animate-pulse"
        style={{ backgroundColor: 'var(--color-surface)' }}
      >
        <div className="h-6 bg-gray-300 rounded w-1/3 mb-4"></div>
        <div className="h-10 bg-gray-300 rounded w-1/2"></div>
      </div>
    );
  }

  const cashBalance = cashData?.cash_balance || 0;
  const realizedGain = realizedGains?.total_realized_gains || 0;
  const isGainPositive = realizedGain >= 0;

  return (
    <div
      className="rounded-lg shadow p-6"
      style={{ backgroundColor: 'var(--color-surface)' }}
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-3">
          <div
            className="p-3 rounded-lg"
            style={{ backgroundColor: 'var(--color-primary-light)' }}
          >
            <DollarSign
              className="h-6 w-6"
              style={{ color: 'var(--color-primary)' }}
            />
          </div>
          <div>
            <p
              className="text-sm font-medium"
              style={{ color: 'var(--color-text-secondary)' }}
            >
              Cash Balance
            </p>
            <p
              className="text-3xl font-bold"
              style={{ color: 'var(--color-text-primary)' }}
            >
              {formatCurrency(cashBalance, currentCurrency)}
            </p>
          </div>
        </div>

        <button
          onClick={onAddCash}
          className="flex items-center space-x-2 px-4 py-2 rounded-lg transition-colors"
          style={{
            backgroundColor: 'var(--color-primary)',
            color: 'white',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.opacity = '0.9';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.opacity = '1';
          }}
        >
          <Plus className="h-5 w-5" />
          <span>Add Cash</span>
        </button>
      </div>

      {/* Realized Gains Section */}
      {realizedGains && (
        <div
          className="mt-4 pt-4"
          style={{ borderTop: '1px solid var(--color-border)' }}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              {isGainPositive ? (
                <TrendingUp className="h-5 w-5 text-green-500" />
              ) : (
                <TrendingDown className="h-5 w-5 text-red-500" />
              )}
              <span
                className="text-sm font-medium"
                style={{ color: 'var(--color-text-secondary)' }}
              >
                Total Realized Gains/Losses
              </span>
            </div>
            <span
              className={`text-lg font-bold ${
                isGainPositive ? 'text-green-600' : 'text-red-600'
              }`}
            >
              {isGainPositive ? '+' : ''}
              {formatCurrency(realizedGain, cashData?.portfolio_currency || 'USD')}
            </span>
          </div>
          <p
            className="text-xs mt-1"
            style={{ color: 'var(--color-text-tertiary)' }}
          >
            Calculated using FIFO (First In, First Out) method
          </p>

          {/* Toggle for detailed breakdown */}
          {realizedGainsDetailed?.realized_gains?.length > 0 && (
            <button
              onClick={() => setShowDetailedTable(!showDetailedTable)}
              className="flex items-center space-x-1 mt-3 text-sm font-medium transition-colors hover:opacity-80"
              style={{ color: 'var(--color-primary)' }}
            >
              <span>{showDetailedTable ? 'Hide' : 'Show'} Detailed Breakdown</span>
              {showDetailedTable ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </button>
          )}

          {/* Detailed Realized Gains Table */}
          {showDetailedTable && realizedGainsDetailed?.realized_gains?.length > 0 && (
            <div className="mt-4 overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr style={{ borderBottom: '2px solid var(--color-border)' }}>
                    <th className="text-left py-2 px-2" style={{ color: 'var(--color-text-secondary)' }}>Ticker</th>
                    <th className="text-left py-2 px-2" style={{ color: 'var(--color-text-secondary)' }}>Name</th>
                    <th className="text-right py-2 px-2" style={{ color: 'var(--color-text-secondary)' }}>Qty Sold</th>
                    <th className="text-right py-2 px-2" style={{ color: 'var(--color-text-secondary)' }}>Cost Basis</th>
                    <th className="text-right py-2 px-2" style={{ color: 'var(--color-text-secondary)' }}>Proceeds</th>
                    <th className="text-right py-2 px-2" style={{ color: 'var(--color-text-secondary)' }}>Realized G/L</th>
                  </tr>
                </thead>
                <tbody>
                  {realizedGainsDetailed.realized_gains.map((item, index) => {
                    const isPositive = item.realized_gain_loss >= 0;
                    return (
                      <tr
                        key={index}
                        style={{ borderBottom: '1px solid var(--color-border)' }}
                      >
                        <td className="py-2 px-2 font-medium" style={{ color: 'var(--color-text-primary)' }}>
                          {item.ticker}
                        </td>
                        <td className="py-2 px-2" style={{ color: 'var(--color-text-secondary)' }}>
                          {item.name?.length > 20 ? `${item.name.substring(0, 20)}...` : item.name}
                        </td>
                        <td className="py-2 px-2 text-right" style={{ color: 'var(--color-text-primary)' }}>
                          {item.quantity_sold?.toFixed(2)}
                        </td>
                        <td className="py-2 px-2 text-right" style={{ color: 'var(--color-text-primary)' }}>
                          {formatCurrency(item.cost_basis, realizedGainsDetailed.currency || 'USD')}
                        </td>
                        <td className="py-2 px-2 text-right" style={{ color: 'var(--color-text-primary)' }}>
                          {formatCurrency(item.proceeds, realizedGainsDetailed.currency || 'USD')}
                        </td>
                        <td className={`py-2 px-2 text-right font-medium ${isPositive ? 'text-green-600' : 'text-red-600'}`}>
                          {isPositive ? '+' : ''}{formatCurrency(item.realized_gain_loss, realizedGainsDetailed.currency || 'USD')}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* No data message */}
          {showDetailedTable && (!realizedGainsDetailed?.realized_gains || realizedGainsDetailed.realized_gains.length === 0) && (
            <div className="mt-4 p-4 text-center rounded" style={{ backgroundColor: 'var(--color-background)' }}>
              <p style={{ color: 'var(--color-text-secondary)' }}>
                No realized gains/losses yet. Sell some assets to see detailed breakdown.
              </p>
            </div>
          )}
        </div>
      )}

      {/* Currency Note */}
      {cashData && cashData.portfolio_currency !== cashData.display_currency && (
        <div
          className="mt-3 p-2 rounded"
          style={{ backgroundColor: 'var(--color-background)' }}
        >
          <p
            className="text-xs"
            style={{ color: 'var(--color-text-secondary)' }}
          >
            Converted from {cashData.portfolio_currency} at rate: {cashData.exchange_rate?.toFixed(4)}
          </p>
        </div>
      )}
    </div>
  );
};

export default CashBalance;
