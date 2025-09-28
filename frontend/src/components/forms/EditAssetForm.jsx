import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { toast } from 'react-hot-toast';
import PortfolioService from '../../services/portfolioService';

const EditAssetForm = ({ onAssetEdited }) => {
  const [holdings, setHoldings] = useState([]);
  const [selectedHolding, setSelectedHolding] = useState('');
  const [formData, setFormData] = useState({
    quantity: '',
    average_cost: ''
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
    const holdingId = e.target.value;
    setSelectedHolding(holdingId);
    
    if (holdingId) {
      const holding = holdings.find(h => h.id.toString() === holdingId);
      if (holding) {
        setFormData({
          quantity: holding.quantity.toString(),
          average_cost: holding.average_cost?.toString() || ''
        });
      }
    } else {
      setFormData({ quantity: '', average_cost: '' });
    }
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
      toast.error('Please select a holding to edit');
      setIsSubmitting(false);
      return;
    }

    try {
      const updatedData = {
        quantity: parseFloat(formData.quantity),
        average_cost: parseFloat(formData.average_cost)
      };

      await portfolioService.updateHolding(holding.id, updatedData);

      toast.success(`Successfully updated ${holding.ticker}`);
      await fetchHoldings(); // Refresh holdings
      setSelectedHolding('');
      setFormData({ quantity: '', average_cost: '' });
      
      if (onAssetEdited) {
        onAssetEdited();
      }

    } catch (error) {
      console.error('Error updating holding:', error);
      toast.error(error.message || 'Failed to update holding');
    } finally {
      setIsSubmitting(false);
    }
  };

  const selectedHoldingData = holdings.find(h => h.id.toString() === selectedHolding);

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-medium text-gray-900 dark:text-white">Edit Asset</h3>
      
      {loadingHoldings ? (
        <div className="text-center py-4">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mx-auto"></div>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">Loading holdings...</p>
        </div>
      ) : holdings.length === 0 ? (
        <div className="text-center py-4">
          <p className="text-sm text-gray-600 dark:text-gray-400">No holdings available to edit.</p>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="holding" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              Select Asset to Edit
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
                  {holding.ticker} - {holding.quantity} shares
                </option>
              ))}
            </select>
          </div>

          {selectedHoldingData && (
            <div className="bg-gray-50 dark:bg-gray-800 p-3 rounded-md">
              <h4 className="font-medium text-gray-900 dark:text-white mb-2">Current Values:</h4>
              <div className="grid grid-cols-2 gap-4 text-sm text-gray-700 dark:text-gray-300">
                <div>
                  <strong>Ticker:</strong> {selectedHoldingData.ticker}
                </div>
                <div>
                  <strong>Current Price:</strong> ${selectedHoldingData.current_price?.toFixed(2) || 'N/A'}
                </div>
                <div>
                  <strong>Market Value:</strong> ${selectedHoldingData.market_value?.toFixed(2) || 'N/A'}
                </div>
                <div>
                  <strong>Cost Basis:</strong> ${selectedHoldingData.cost_basis?.toFixed(2) || 'N/A'}
                </div>
              </div>
            </div>
          )}

          <div>
            <label htmlFor="quantity" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              Quantity (shares)
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
            <label htmlFor="average_cost" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              Average Cost per Share ($)
            </label>
            <input
              type="number"
              id="average_cost"
              name="average_cost"
              value={formData.average_cost}
              onChange={handleChange}
              placeholder="Average cost per share"
              required
              min="0"
              step="0.01"
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
            />
          </div>

          <div className="bg-yellow-50 dark:bg-yellow-900/20 p-3 rounded-md">
            <p className="text-sm text-yellow-800 dark:text-yellow-200">
              <strong>Note:</strong> Editing these values will update your cost basis and may affect 
              your portfolio calculations. Use this to correct entry errors.
            </p>
          </div>

          <button
            type="submit"
            disabled={isSubmitting || !selectedHolding}
            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSubmitting ? 'Updating...' : 'Update Asset'}
          </button>
        </form>
      )}
    </div>
  );
};

export default EditAssetForm;