import React, { useState } from 'react';
import { DollarSign, Minus, Banknote } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { useCurrency } from '../../contexts/CurrencyContext';
import toast from 'react-hot-toast';

const AddCashFormInline = ({ onSuccess }) => {
  const [amount, setAmount] = useState('');
  const [transactionType, setTransactionType] = useState('DEPOSIT');
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);
  const { api, portfolioId } = useAuth();
  const { currency, getCurrencySymbol } = useCurrency();

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
        currency: currency,  // Send the current dashboard currency
        notes: notes || null,
      });

      toast.success(response.data.message || `Cash ${transactionType.toLowerCase()} successful`);

      // Reset form
      setAmount('');
      setNotes('');

      if (onSuccess) {
        onSuccess(response.data);
      }
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
    <div>
      {/* Header */}
      <div className="flex items-center space-x-3 mb-6">
        <div
          className="p-2 rounded-lg"
          style={{ backgroundColor: 'var(--color-warning-bg, rgba(251, 191, 36, 0.1))' }}
        >
          <Banknote className="h-6 w-6" style={{ color: 'var(--color-warning)' }} />
        </div>
        <div>
          <h3
            className="text-lg font-semibold"
            style={{ color: 'var(--color-text-primary)' }}
          >
            {transactionType === 'DEPOSIT' ? 'Deposit Cash' : 'Withdraw Cash'}
          </h3>
          <p
            className="text-sm"
            style={{ color: 'var(--color-text-secondary)' }}
          >
            {transactionType === 'DEPOSIT'
              ? 'Add funds to your portfolio cash balance'
              : 'Withdraw funds from your portfolio cash balance'}
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Transaction Type Selector */}
        <div>
          <label
            className="block text-sm font-medium mb-3"
            style={{ color: 'var(--color-text-secondary)' }}
          >
            Transaction Type
          </label>
          <div className="grid grid-cols-2 gap-4">
            <button
              type="button"
              onClick={() => setTransactionType('DEPOSIT')}
              className={`flex items-center justify-center space-x-2 px-4 py-4 rounded-lg border-2 transition-all duration-200 ${
                transactionType === 'DEPOSIT'
                  ? 'border-green-500'
                  : ''
              }`}
              style={{
                backgroundColor:
                  transactionType === 'DEPOSIT'
                    ? 'var(--color-success-bg, rgba(34, 197, 94, 0.1))'
                    : 'var(--color-bg-2)',
                borderColor:
                  transactionType === 'DEPOSIT'
                    ? 'var(--color-success)'
                    : 'var(--color-border)',
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
              className={`flex items-center justify-center space-x-2 px-4 py-4 rounded-lg border-2 transition-all duration-200 ${
                transactionType === 'WITHDRAWAL'
                  ? 'border-red-500'
                  : ''
              }`}
              style={{
                backgroundColor:
                  transactionType === 'WITHDRAWAL'
                    ? 'var(--color-error-bg, rgba(239, 68, 68, 0.1))'
                    : 'var(--color-bg-2)',
                borderColor:
                  transactionType === 'WITHDRAWAL'
                    ? 'var(--color-error)'
                    : 'var(--color-border)',
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
            htmlFor="cash-amount"
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
              id="cash-amount"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className="w-full pl-12 pr-4 py-3 rounded-lg border focus:ring-2 focus:ring-opacity-50 transition-colors"
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
            htmlFor="cash-notes"
            className="block text-sm font-medium mb-2"
            style={{ color: 'var(--color-text-secondary)' }}
          >
            Notes (Optional)
          </label>
          <textarea
            id="cash-notes"
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

        {/* Submit Button */}
        <div className="pt-2">
          <button
            type="submit"
            className="w-full px-6 py-3 rounded-lg font-medium transition-all duration-200 hover:opacity-90"
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
              ? 'Deposit Cash'
              : 'Withdraw Cash'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default AddCashFormInline;
