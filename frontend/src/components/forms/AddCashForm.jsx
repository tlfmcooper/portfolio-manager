import React, { useState } from 'react';
import { X, DollarSign, Minus } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { useCurrency } from '../../contexts/CurrencyContext';
import toast from 'react-hot-toast';

const AddCashForm = ({ onClose, onSuccess }) => {
  const [amount, setAmount] = useState('');
  const [transactionType, setTransactionType] = useState('DEPOSIT');
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);
  const { api, portfolioId } = useAuth();
  const { getCurrencySymbol } = useCurrency();

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!amount || parseFloat(amount) <= 0) {
      toast.error('Please enter a valid amount');
      return;
    }

    try {
      setLoading(true);

      const endpoint =
        transactionType === 'DEPOSIT'
          ? `/portfolios/${portfolioId}/cash/deposit`
          : `/portfolios/${portfolioId}/cash/withdrawal`;

      const response = await api.post(endpoint, {
        amount: parseFloat(amount),
        transaction_type: transactionType,
        notes: notes || null,
      });

      toast.success(response.data.message || `Cash ${transactionType.toLowerCase()} successful`);

      if (onSuccess) {
        onSuccess(response.data);
      }

      onClose();
    } catch (error) {
      console.error(`Error ${transactionType.toLowerCase()}ing cash:`, error);
      const errorMessage =
        error.response?.data?.detail ||
        `Failed to ${transactionType.toLowerCase()} cash`;
      toast.error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      onClick={onClose}
    >
      <div
        className="rounded-lg shadow-xl p-6 w-full max-w-md m-4"
        style={{ backgroundColor: 'var(--color-surface)' }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h2
            className="text-2xl font-bold"
            style={{ color: 'var(--color-text-primary)' }}
          >
            {transactionType === 'DEPOSIT' ? 'Add Cash' : 'Withdraw Cash'}
          </h2>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-opacity-10 transition-colors"
            style={{
              backgroundColor: 'transparent',
              color: 'var(--color-text-secondary)',
            }}
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Transaction Type Selector */}
          <div>
            <label
              className="block text-sm font-medium mb-2"
              style={{ color: 'var(--color-text-secondary)' }}
            >
              Transaction Type
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setTransactionType('DEPOSIT')}
                className={`flex items-center justify-center space-x-2 px-4 py-3 rounded-lg border-2 transition-colors ${
                  transactionType === 'DEPOSIT'
                    ? 'border-green-500 bg-green-50'
                    : 'border-gray-300'
                }`}
                style={{
                  color:
                    transactionType === 'DEPOSIT'
                      ? 'var(--color-success)'
                      : 'var(--color-text-secondary)',
                }}
              >
                <DollarSign className="h-5 w-5" />
                <span className="font-medium">Deposit</span>
              </button>

              <button
                type="button"
                onClick={() => setTransactionType('WITHDRAWAL')}
                className={`flex items-center justify-center space-x-2 px-4 py-3 rounded-lg border-2 transition-colors ${
                  transactionType === 'WITHDRAWAL'
                    ? 'border-red-500 bg-red-50'
                    : 'border-gray-300'
                }`}
                style={{
                  color:
                    transactionType === 'WITHDRAWAL'
                      ? 'var(--color-error)'
                      : 'var(--color-text-secondary)',
                }}
              >
                <Minus className="h-5 w-5" />
                <span className="font-medium">Withdraw</span>
              </button>
            </div>
          </div>

          {/* Amount Input */}
          <div>
            <label
              htmlFor="amount"
              className="block text-sm font-medium mb-2"
              style={{ color: 'var(--color-text-secondary)' }}
            >
              Amount
            </label>
            <div className="relative">
              <span
                className="absolute left-4 top-1/2 transform -translate-y-1/2 text-sm font-medium"
                style={{ color: 'var(--color-text-secondary)' }}
              >
                {getCurrencySymbol()}
              </span>
              <input
                type="number"
                id="amount"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                className="w-full pl-16 pr-4 py-3 rounded-lg border focus:ring-2 focus:ring-opacity-50 transition-colors"
                style={{
                  backgroundColor: 'var(--color-background)',
                  borderColor: 'var(--color-border)',
                  color: 'var(--color-text-primary)',
                }}
                placeholder="0.00"
                min="0.01"
                step="0.01"
                required
              />
            </div>
          </div>

          {/* Notes Input */}
          <div>
            <label
              htmlFor="notes"
              className="block text-sm font-medium mb-2"
              style={{ color: 'var(--color-text-secondary)' }}
            >
              Notes (Optional)
            </label>
            <textarea
              id="notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full px-4 py-3 rounded-lg border focus:ring-2 focus:ring-opacity-50 transition-colors resize-none"
              style={{
                backgroundColor: 'var(--color-background)',
                borderColor: 'var(--color-border)',
                color: 'var(--color-text-primary)',
              }}
              placeholder="Add notes about this transaction..."
              rows="3"
            />
          </div>

          {/* Action Buttons */}
          <div className="flex space-x-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-3 rounded-lg border transition-colors"
              style={{
                borderColor: 'var(--color-border)',
                color: 'var(--color-text-secondary)',
              }}
              disabled={loading}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="flex-1 px-4 py-3 rounded-lg font-medium transition-colors"
              style={{
                backgroundColor:
                  transactionType === 'DEPOSIT'
                    ? 'var(--color-success)'
                    : 'var(--color-error)',
                color: 'white',
              }}
              disabled={loading}
            >
              {loading
                ? 'Processing...'
                : transactionType === 'DEPOSIT'
                ? 'Deposit'
                : 'Withdraw'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default AddCashForm;
