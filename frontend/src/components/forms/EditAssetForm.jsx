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
    <div>
      {loadingHoldings ? (
        <div className="text-center py-4">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 mx-auto" style={{ borderColor: 'var(--color-primary)' }}></div>
          <p className="mt-2 text-sm" style={{ color: 'var(--color-text-secondary)' }}>Loading holdings...</p>
        </div>
      ) : holdings.length === 0 ? (
        <div className="text-center py-4">
          <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>No holdings available to edit.</p>
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
              Select Asset to Edit
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
                  {holding.ticker} - {holding.quantity} shares
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
              <h4 style={{
                fontWeight: 'var(--font-weight-medium)',
                color: 'var(--color-text)',
                marginBottom: 'var(--space-12)',
                fontSize: 'var(--font-size-base)'
              }}>
                Current Values:
              </h4>
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(2, 1fr)',
                gap: 'var(--space-16)',
                fontSize: 'var(--font-size-sm)',
                color: 'var(--color-text)'
              }}>
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
              htmlFor="average_cost" 
              className="form-label"
              style={{
                display: 'block',
                marginBottom: 'var(--space-8)',
                fontWeight: 'var(--font-weight-medium)',
                fontSize: 'var(--font-size-sm)',
                color: 'var(--color-text)'
              }}
            >
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

          <div style={{
            backgroundColor: 'var(--color-warning-bg)',
            padding: 'var(--space-16)',
            borderRadius: 'var(--radius-base)',
            border: '1px solid var(--color-warning-border)'
          }}>
            <p style={{
              fontSize: 'var(--font-size-sm)',
              color: 'var(--color-warning-text)',
              margin: 0
            }}>
              <strong>Note:</strong> Editing these values will update your cost basis and may affect 
              your portfolio calculations. Use this to correct entry errors.
            </p>
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
              background: 'var(--color-primary)',
              color: 'var(--color-white)',
              opacity: (isSubmitting || !selectedHolding) ? 0.5 : 1
            }}
          >
            {isSubmitting ? 'Updating...' : 'Update Asset'}
          </button>
        </form>
      )}
    </div>
  );
};

export default EditAssetForm;