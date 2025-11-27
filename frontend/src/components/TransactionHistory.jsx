import React, { useState, useEffect } from 'react';
import {
  ArrowUpCircle,
  ArrowDownCircle,
  DollarSign,
  TrendingUp,
  TrendingDown,
  Calendar,
  FileText,
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useCurrency } from '../contexts/CurrencyContext';

const TransactionHistory = () => {
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('ALL'); // ALL, BUY, SELL, DEPOSIT, WITHDRAWAL
  const { api, portfolioId } = useAuth();
  const { formatCurrency } = useCurrency();

  useEffect(() => {
    fetchTransactions();
  }, [portfolioId]);

  const fetchTransactions = async () => {
    if (!portfolioId) return;

    try {
      setLoading(true);
      const response = await api.get(`/portfolios/${portfolioId}/transactions/`);
      setTransactions(response.data);
    } catch (error) {
      console.error('Error fetching transactions:', error);
    } finally {
      setLoading(false);
    }
  };

  const getTransactionIcon = (type) => {
    switch (type) {
      case 'BUY':
        return <ArrowDownCircle className="h-5 w-5 text-blue-500" />;
      case 'SELL':
        return <ArrowUpCircle className="h-5 w-5 text-orange-500" />;
      case 'DEPOSIT':
        return <DollarSign className="h-5 w-5 text-green-500" />;
      case 'WITHDRAWAL':
        return <TrendingDown className="h-5 w-5 text-red-500" />;
      default:
        return <FileText className="h-5 w-5 text-gray-500" />;
    }
  };

  const getTransactionColor = (type) => {
    switch (type) {
      case 'BUY':
        return 'text-blue-600';
      case 'SELL':
        return 'text-orange-600';
      case 'DEPOSIT':
        return 'text-green-600';
      case 'WITHDRAWAL':
        return 'text-red-600';
      default:
        return 'text-gray-600';
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const filteredTransactions = transactions.filter((txn) => {
    if (filter === 'ALL') return true;
    return txn.transaction_type === filter;
  });

  if (loading) {
    return (
      <div
        className="rounded-lg shadow p-6 animate-pulse"
        style={{ backgroundColor: 'var(--color-surface)' }}
      >
        <div className="h-6 bg-gray-300 rounded w-1/3 mb-4"></div>
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-16 bg-gray-300 rounded"></div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div
      className="rounded-lg shadow p-6"
      style={{ backgroundColor: 'var(--color-surface)' }}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h2
          className="text-2xl font-bold"
          style={{ color: 'var(--color-text-primary)' }}
        >
          Transaction History
        </h2>
        <span
          className="text-sm"
          style={{ color: 'var(--color-text-secondary)' }}
        >
          {filteredTransactions.length} transaction{filteredTransactions.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Filter Buttons */}
      <div className="flex flex-wrap gap-2 mb-4">
        {['ALL', 'BUY', 'SELL', 'DEPOSIT', 'WITHDRAWAL'].map((type) => (
          <button
            key={type}
            onClick={() => setFilter(type)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              filter === type
                ? 'shadow-md'
                : ''
            }`}
            style={{
              backgroundColor:
                filter === type ? 'var(--color-primary)' : 'var(--color-background)',
              color: filter === type ? 'white' : 'var(--color-text-secondary)',
            }}
          >
            {type}
          </button>
        ))}
      </div>

      {/* Transactions List */}
      {filteredTransactions.length === 0 ? (
        <div
          className="text-center py-12"
          style={{ color: 'var(--color-text-secondary)' }}
        >
          <FileText className="h-12 w-12 mx-auto mb-3 opacity-50" />
          <p>No transactions found</p>
        </div>
      ) : (
        <div className="space-y-3 max-h-96 overflow-y-auto">
          {filteredTransactions.map((txn) => (
            <div
              key={txn.id}
              className="flex items-center justify-between p-4 rounded-lg border transition-colors hover:shadow-md"
              style={{
                backgroundColor: 'var(--color-background)',
                borderColor: 'var(--color-border)',
              }}
            >
              {/* Left Side: Icon & Details */}
              <div className="flex items-center space-x-4">
                <div className="flex-shrink-0">
                  {getTransactionIcon(txn.transaction_type)}
                </div>

                <div>
                  <div className="flex items-center space-x-2">
                    <span
                      className={`font-semibold ${getTransactionColor(
                        txn.transaction_type
                      )}`}
                    >
                      {txn.transaction_type}
                    </span>
                    {txn.asset && (
                      <span
                        className="text-sm"
                        style={{ color: 'var(--color-text-primary)' }}
                      >
                        • {txn.asset.ticker}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center space-x-3 mt-1">
                    <span
                      className="text-sm flex items-center space-x-1"
                      style={{ color: 'var(--color-text-secondary)' }}
                    >
                      <Calendar className="h-3 w-3" />
                      <span>{formatDate(txn.transaction_date)}</span>
                    </span>

                    {txn.quantity && (
                      <span
                        className="text-sm"
                        style={{ color: 'var(--color-text-tertiary)' }}
                      >
                        Qty: {txn.quantity}
                      </span>
                    )}

                    {txn.notes && (
                      <span
                        className="text-sm italic"
                        style={{ color: 'var(--color-text-tertiary)' }}
                      >
                        "{txn.notes}"
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* Right Side: Amount & Realized Gain/Loss */}
              <div className="text-right">
                <div
                  className={`font-bold ${
                    txn.transaction_type === 'DEPOSIT' || txn.transaction_type === 'SELL'
                      ? 'text-green-600'
                      : txn.transaction_type === 'WITHDRAWAL' || txn.transaction_type === 'BUY'
                      ? 'text-red-600'
                      : ''
                  }`}
                >
                  {txn.transaction_type === 'DEPOSIT' || txn.transaction_type === 'SELL'
                    ? '+'
                    : '-'}
                  {txn.quantity
                    ? formatCurrency(txn.quantity * txn.price)
                    : formatCurrency(txn.price)}
                </div>

                {txn.price && txn.quantity && (
                  <div
                    className="text-xs mt-1"
                    style={{ color: 'var(--color-text-tertiary)' }}
                  >
                    @ {formatCurrency(txn.price)} each
                  </div>
                )}

                {txn.realized_gain_loss !== null && txn.realized_gain_loss !== undefined && (
                  <div
                    className={`text-sm font-medium mt-1 flex items-center justify-end space-x-1 ${
                      txn.realized_gain_loss >= 0 ? 'text-green-600' : 'text-red-600'
                    }`}
                  >
                    {txn.realized_gain_loss >= 0 ? (
                      <TrendingUp className="h-3 w-3" />
                    ) : (
                      <TrendingDown className="h-3 w-3" />
                    )}
                    <span>
                      {txn.realized_gain_loss >= 0 ? '+' : ''}
                      {formatCurrency(txn.realized_gain_loss)} gain
                    </span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default TransactionHistory;
