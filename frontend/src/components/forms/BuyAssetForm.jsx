import React, { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { toast } from 'react-hot-toast';

const BuyAssetForm = ({ onAssetAdded }) => {
  const [formData, setFormData] = useState({
    ticker: '',
    quantity: '',
    unit_cost: ''
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { api } = useAuth();

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch('http://127.0.0.1:8000/api/v1/assets/onboard', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify([{
          ticker: formData.ticker.toUpperCase().trim(),
          quantity: parseFloat(formData.quantity),
          unit_cost: parseFloat(formData.unit_cost)
        }])
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to buy asset');
      }

      if (data.assets && data.assets.length > 0) {
        toast.success(`Successfully bought ${formData.quantity} shares of ${formData.ticker.toUpperCase()}`);
        setFormData({ ticker: '', quantity: '', unit_cost: '' });
        if (onAssetAdded) {
          onAssetAdded();
        }
      }

      if (data.errors && data.errors.length > 0) {
        toast.error(`Errors: ${data.errors.join(', ')}`);
      }

    } catch (error) {
      console.error('Error buying asset:', error);
      toast.error(error.message || 'Failed to buy asset');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-medium text-gray-900 dark:text-white">Buy Asset</h3>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="ticker" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
            Ticker Symbol
          </label>
          <input
            type="text"
            id="ticker"
            name="ticker"
            value={formData.ticker}
            onChange={handleChange}
            placeholder="e.g., AAPL, MSFT"
            required
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
          />
        </div>

        <div>
          <label htmlFor="quantity" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
            Quantity
          </label>
          <input
            type="number"
            id="quantity"
            name="quantity"
            value={formData.quantity}
            onChange={handleChange}
            placeholder="Number of shares"
            required
            min="0"
            step="any"
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
          />
        </div>

        <div>
          <label htmlFor="unit_cost" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
            Unit Cost ($)
          </label>
          <input
            type="number"
            id="unit_cost"
            name="unit_cost"
            value={formData.unit_cost}
            onChange={handleChange}
            placeholder="Price per share"
            required
            min="0"
            step="0.01"
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
          />
        </div>

        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSubmitting ? 'Buying...' : 'Buy Asset'}
        </button>
      </form>
    </div>
  );
};

export default BuyAssetForm;