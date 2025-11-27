import React, { useState, useEffect } from 'react';
import { DollarSign, Plus, TrendingUp, TrendingDown } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useCurrency } from '../contexts/CurrencyContext';

const CashBalance = ({ onAddCash }) => {
  const [cashData, setCashData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [realizedGains, setRealizedGains] = useState(null);
  const { api, portfolioId } = useAuth();
  const { currentCurrency, formatCurrency } = useCurrency();

  useEffect(() => {
    fetchCashBalance();
    fetchRealizedGains();
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
