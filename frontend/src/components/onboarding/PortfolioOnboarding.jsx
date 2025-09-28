import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

const PortfolioOnboarding = () => {
  console.log('PortfolioOnboarding component rendered.'); // Debug log
  const navigate = useNavigate();
  const { checkOnboardingStatus, user } = useAuth();
  const [assets, setAssets] = useState([
    { ticker: '', quantity: '', unit_cost: '' }
  ]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleAssetChange = (idx, field, value) => {
    const updated = assets.map((a, i) =>
      i === idx ? { ...a, [field]: value } : a
    );
    setAssets(updated);
  };

  const addAsset = () => {
    setAssets([...assets, { ticker: '', quantity: '', unit_cost: '' }]);
  };

  const removeAsset = (idx) => {
    setAssets(assets.filter((_, i) => i !== idx));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError('');
    
    // Filter out empty assets
    const validAssets = assets.filter(asset => 
      asset.ticker.trim() && asset.quantity && asset.unit_cost
    );
    
    if (validAssets.length === 0) {
      setError('Please enter at least one valid asset.');
      setIsSubmitting(false);
      return;
    }
    
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch('http://127.0.0.1:8000/api/v1/assets/onboard', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(validAssets)
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        const errorMsg = data.detail?.errors 
          ? data.detail.errors.join(', ') 
          : data.detail || 'Failed to save assets';
        throw new Error(errorMsg);
      }
      
      if (data.errors && data.errors.length > 0) {
        setError(`Some assets failed to save: ${data.errors.join(', ')}`);
      }
      // FIX: Remove check for data.success, just check if assets were created
      if (data.assets && data.assets.length > 0) {
        console.log('Successfully saved assets:', data.assets);
        // Refresh onboarding status in AuthContext
        await checkOnboardingStatus(user);
        navigate('/dashboard');
      }
      
    } catch (err) {
      console.error('Asset onboarding error:', err);
      setError(err.message || 'Failed to save assets. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-2xl mx-auto">
        <h2 className="text-3xl font-extrabold text-gray-900 dark:text-white mb-8 text-center">Add Your Assets</h2>
        {error && <div className="bg-red-50 border-l-4 border-red-500 p-4 mb-6 text-red-700">{error}</div>}
        <form onSubmit={handleSubmit} className="space-y-6">
          {assets.map((asset, idx) => (
            <div key={idx} className="bg-white dark:bg-gray-800 shadow rounded-lg p-6 mb-4 flex flex-col gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Ticker</label>
                <input type="text" value={asset.ticker} onChange={e => handleAssetChange(idx, 'ticker', e.target.value)} required className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-base py-2 px-3 text-gray-900 dark:text-white dark:bg-gray-700 dark:border-gray-600" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Quantity</label>
                <input type="number" value={asset.quantity} onChange={e => handleAssetChange(idx, 'quantity', e.target.value)} required min="0" step="any" className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-base py-2 px-3 text-gray-900 dark:text-white dark:bg-gray-700 dark:border-gray-600" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Unit Cost</label>
                <input type="number" value={asset.unit_cost} onChange={e => handleAssetChange(idx, 'unit_cost', e.target.value)} required min="0" step="any" className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-base py-2 px-3 text-gray-900 dark:text-white dark:bg-gray-700 dark:border-gray-600" />
              </div>
              {assets.length > 1 && (
                <button type="button" onClick={() => removeAsset(idx)} className="text-red-600 hover:underline self-end">Remove</button>
              )}
            </div>
          ))}
          <button type="button" onClick={addAsset} className="inline-flex items-center px-4 py-2 border border-indigo-600 text-indigo-600 rounded-md hover:bg-indigo-50">Add Another Asset</button>
          <button type="submit" disabled={isSubmitting} className="w-full inline-flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50 disabled:cursor-not-allowed">
            {isSubmitting ? 'Saving...' : 'Complete Onboarding'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default PortfolioOnboarding;
