import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { toast } from 'react-hot-toast';
import PortfolioService from '../../services/portfolioService';

const SellAssetForm = ({ onAssetSold }) => {
  const [holdings, setHoldings] = useState([]);
  const [selectedHolding, setSelectedHolding] = useState('');
  const [formData, setFormData] = useState({
    quantity: '',
    unit_cost: ''
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [loadingHoldings, setLoadingHoldings] = useState(true);
  const { api } = useAuth();

  const portfolioService = new PortfolioService(api);

  useEffect(() => {
    fetchHoldings();
  }, []);

  const fetchHoldings = async () => {
    try {
      setLoadingHoldings(true);
      const holdingsData = await portfolioService.getHoldings();
      setHoldings(holdingsData || []);
    } catch (error) {
      console.error('Error fetching holdings:', error);
      toast.error('Failed to load holdings');
    } finally {
      setLoadingHoldings(false);
    }
  };

  const handleHoldingChange = (e) => {
    setSelectedHolding(e.target.value);
    setFormData({ quantity: '', unit_cost: '' });
  };

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

    const holding = holdings.find(h => h.id.toString() === selectedHolding);
    if (!holding) {
      toast.error('Please select a holding to sell');
      setIsSubmitting(false);
      return;
    }

    const sellQuantity = parseFloat(formData.quantity);
    if (sellQuantity > holding.quantity) {
      toast.error(`Cannot sell ${sellQuantity} shares. You only own ${holding.quantity} shares.`);
      setIsSubmitting(false);
      return;
    }

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch('http://127.0.0.1:8000/api/v1/assets/sell', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          ticker: holding.ticker,
          quantity: sellQuantity,
          unit_cost: parseFloat(formData.unit_cost)
        })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to sell asset');
      }

      toast.success(`Successfully sold ${sellQuantity} shares of ${holding.ticker}`);
      setFormData({ quantity: '', unit_cost: '' });
      setSelectedHolding('');
      await fetchHoldings(); // Refresh holdings
      if (onAssetSold) {
        onAssetSold();
      }

    } catch (error) {
      console.error('Error selling asset:', error);
      toast.error(error.message || 'Failed to sell asset');
    } finally {
      setIsSubmitting(false);
    }
  };

  const selectedHoldingData = holdings.find(h => h.id.toString() === selectedHolding);

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-medium text-gray-900 dark:text-white">Sell Asset</h3>
      
      {loadingHoldings ? (
        <div className="text-center py-4">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mx-auto"></div>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">Loading holdings...</p>
        </div>
      ) : holdings.length === 0 ? (
        <div className="text-center py-4">
          <p className="text-sm text-gray-600 dark:text-gray-400">No holdings available to sell.</p>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="holding" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              Select Asset to Sell
            </label>
            <select
              id="holding"
              value={selectedHolding}
              onChange={handleHoldingChange}
              required
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
            >
              <option value="">Choose a holding...</option>
              {holdings.map((holding) => (
                <option key={holding.id} value={holding.id}>
                  {holding.ticker} ({holding.quantity} shares available)
                </option>
              ))}
            </select>
          </div>

          {selectedHoldingData && (
            <div className="bg-gray-50 dark:bg-gray-800 p-3 rounded-md">
              <p className="text-sm text-gray-700 dark:text-gray-300">
                <strong>Available:</strong> {selectedHoldingData.quantity} shares<br />
                <strong>Average Cost:</strong> ${selectedHoldingData.average_cost?.toFixed(2) || 'N/A'}<br />
                <strong>Current Price:</strong> ${selectedHoldingData.current_price?.toFixed(2) || 'N/A'}
              </p>
            </div>
          )}

          <div>
            <label htmlFor="quantity" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              Quantity to Sell
            </label>
            <input
              type="number"
              id="quantity"
              name="quantity"
              value={formData.quantity}
              onChange={handleChange}
              placeholder="Number of shares to sell"
              required
              min="0"
              max={selectedHoldingData?.quantity || 0}
              step="any"
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
            />
          </div>

          <div>
            <label htmlFor="unit_cost" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              Sell Price ($)
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
            disabled={isSubmitting || !selectedHolding}
            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSubmitting ? 'Selling...' : 'Sell Asset'}
          </button>
        </form>
      )}
    </div>
  );
};

export default SellAssetForm;