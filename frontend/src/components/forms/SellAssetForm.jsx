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
    <div>
      {loadingHoldings ? (
        <div className="text-center py-4">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 mx-auto" style={{ borderColor: 'var(--color-primary)' }}></div>
          <p className="mt-2 text-sm" style={{ color: 'var(--color-text-secondary)' }}>Loading holdings...</p>
        </div>
      ) : holdings.length === 0 ? (
        <div className="text-center py-4">
          <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>No holdings available to sell.</p>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label 
              htmlFor="holding" 
              className="form-label"
              style={{
                display: 'block',
                marginBottom: 'var(--space-8)',
                fontWeight: 'var(--font-weight-medium)',
                fontSize: 'var(--font-size-sm)',
                color: 'var(--color-text)'
              }}
            >
              Select Asset to Sell
            </label>
            <select
              id="holding"
              value={selectedHolding}
              onChange={handleHoldingChange}
              required
              className="form-control"
              style={{
                display: 'block',
                width: '100%',
                padding: 'var(--space-12)',
                fontSize: 'var(--font-size-base)',
                lineHeight: '1.5',
                color: 'var(--color-text)',
                backgroundColor: 'var(--color-surface)',
                border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius-base)',
                transition: 'border-color var(--duration-fast) var(--ease-standard), box-shadow var(--duration-fast) var(--ease-standard)'
              }}
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
            <div style={{
              backgroundColor: 'var(--color-bg-1)',
              padding: 'var(--space-16)',
              borderRadius: 'var(--radius-base)',
              border: '1px solid var(--color-border)'
            }}>
              <p style={{ 
                fontSize: 'var(--font-size-sm)', 
                color: 'var(--color-text)',
                margin: 0
              }}>
                <strong>Available:</strong> {selectedHoldingData.quantity} shares<br />
                <strong>Average Cost:</strong> ${selectedHoldingData.average_cost?.toFixed(2) || 'N/A'}<br />
                <strong>Current Price:</strong> ${selectedHoldingData.current_price?.toFixed(2) || 'N/A'}
              </p>
            </div>
          )}

          <div>
            <label 
              htmlFor="quantity" 
              className="form-label"
              style={{
                display: 'block',
                marginBottom: 'var(--space-8)',
                fontWeight: 'var(--font-weight-medium)',
                fontSize: 'var(--font-size-sm)',
                color: 'var(--color-text)'
              }}
            >
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
              className="form-control"
              style={{
                display: 'block',
                width: '100%',
                padding: 'var(--space-12)',
                fontSize: 'var(--font-size-base)',
                lineHeight: '1.5',
                color: 'var(--color-text)',
                backgroundColor: 'var(--color-surface)',
                border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius-base)',
                transition: 'border-color var(--duration-fast) var(--ease-standard), box-shadow var(--duration-fast) var(--ease-standard)'
              }}
            />
          </div>

          <div>
            <label 
              htmlFor="unit_cost" 
              className="form-label"
              style={{
                display: 'block',
                marginBottom: 'var(--space-8)',
                fontWeight: 'var(--font-weight-medium)',
                fontSize: 'var(--font-size-sm)',
                color: 'var(--color-text)'
              }}
            >
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
              className="form-control"
              style={{
                display: 'block',
                width: '100%',
                padding: 'var(--space-12)',
                fontSize: 'var(--font-size-base)',
                lineHeight: '1.5',
                color: 'var(--color-text)',
                backgroundColor: 'var(--color-surface)',
                border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius-base)',
                transition: 'border-color var(--duration-fast) var(--ease-standard), box-shadow var(--duration-fast) var(--ease-standard)'
              }}
            />
          </div>

          <button
            type="submit"
            disabled={isSubmitting || !selectedHolding}
            className="btn btn--primary btn--full-width"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: 'var(--space-12) var(--space-16)',
              borderRadius: 'var(--radius-base)',
              fontSize: 'var(--font-size-base)',
              fontWeight: '500',
              lineHeight: 1.5,
              cursor: (isSubmitting || !selectedHolding) ? 'not-allowed' : 'pointer',
              transition: 'all var(--duration-normal) var(--ease-standard)',
              border: 'none',
              textDecoration: 'none',
              position: 'relative',
              width: '100%',
              background: 'var(--color-error)',
              color: 'var(--color-white)',
              opacity: (isSubmitting || !selectedHolding) ? 0.5 : 1
            }}
          >
            {isSubmitting ? 'Selling...' : 'Sell Asset'}
          </button>
        </form>
      )}
    </div>
  );
};

export default SellAssetForm;