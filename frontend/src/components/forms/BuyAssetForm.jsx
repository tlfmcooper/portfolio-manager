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
    <div>
      <form onSubmit={handleSubmit} className="space-y-6">
        <div>
          <label 
            htmlFor="ticker" 
            className="form-label"
            style={{
              display: 'block',
              marginBottom: 'var(--space-8)',
              fontWeight: 'var(--font-weight-medium)',
              fontSize: 'var(--font-size-sm)',
              color: 'var(--color-text)'
            }}
          >
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
          disabled={isSubmitting}
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
            cursor: isSubmitting ? 'not-allowed' : 'pointer',
            transition: 'all var(--duration-normal) var(--ease-standard)',
            border: 'none',
            textDecoration: 'none',
            position: 'relative',
            width: '100%',
            background: 'var(--color-success)',
            color: 'var(--color-white)',
            opacity: isSubmitting ? 0.5 : 1
          }}
        >
          {isSubmitting ? 'Buying...' : 'Buy Asset'}
        </button>
      </form>
    </div>
  );
};

export default BuyAssetForm;