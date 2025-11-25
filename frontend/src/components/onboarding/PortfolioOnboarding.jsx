import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { Upload } from 'lucide-react';

const PortfolioOnboarding = () => {
  console.log('PortfolioOnboarding component rendered.'); // Debug log
  const navigate = useNavigate();
  const { checkOnboardingStatus, user, api } = useAuth();
  const [assets, setAssets] = useState([
    { ticker: '', quantity: '', average_cost: '', asset_type: 'Stock', currency: 'USD' }
  ]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [uploadMethod, setUploadMethod] = useState('manual'); // 'manual' or 'csv'
  const [csvFile, setCsvFile] = useState(null);

  const handleAssetChange = (idx, field, value) => {
    const updated = assets.map((a, i) =>
      i === idx ? { ...a, [field]: value } : a
    );
    setAssets(updated);
  };

  const addAsset = () => {
    setAssets([...assets, { ticker: '', quantity: '', average_cost: '', asset_type: 'Stock', currency: 'USD' }]);
  };

  const removeAsset = (idx) => {
    setAssets(assets.filter((_, i) => i !== idx));
  };

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file && file.type === 'text/csv') {
      setCsvFile(file);
      setError('');
    } else {
      setError('Please upload a valid CSV file');
      setCsvFile(null);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError('');

    try {
      let data;

      if (uploadMethod === 'csv' && csvFile) {
        // Upload CSV file
        const formData = new FormData();
        formData.append('file', csvFile);

        const response = await api.post('/assets/onboard', formData);
        data = response.data;
      } else {
        // Manual entry - filter out empty assets
        const validAssets = assets.filter(asset =>
          asset.ticker.trim() && asset.quantity && asset.average_cost
        );

        if (validAssets.length === 0) {
          setError('Please enter at least one valid asset.');
          setIsSubmitting(false);
          return;
        }

        const response = await api.post('/assets/onboard', validAssets);
        data = response.data;
      }

      if (data.errors && data.errors.length > 0) {
        setError(`Some assets failed to save: ${data.errors.join(', ')}`);
      }

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

        {/* Upload Method Toggle */}
        <div className="mb-6 bg-white dark:bg-gray-800 shadow rounded-lg p-4">
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">Upload Method</label>
          <div className="flex gap-4">
            <button
              type="button"
              onClick={() => setUploadMethod('manual')}
              className={`flex-1 py-2 px-4 rounded-md ${uploadMethod === 'manual' ? 'bg-indigo-600 text-white' : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300'}`}
            >
              Manual Entry
            </button>
            <button
              type="button"
              onClick={() => setUploadMethod('csv')}
              className={`flex-1 py-2 px-4 rounded-md ${uploadMethod === 'csv' ? 'bg-indigo-600 text-white' : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300'}`}
            >
              Upload CSV
            </button>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {uploadMethod === 'csv' ? (
            <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Upload CSV File
              </label>
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">
                CSV Format: TICKER,CURRENCY,ASSET_TYPE,Quantity,Cost
              </p>
              <div className="flex items-center justify-center w-full">
                <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-gray-300 border-dashed rounded-lg cursor-pointer bg-gray-50 dark:bg-gray-700 hover:bg-gray-100 dark:hover:bg-gray-600">
                  <div className="flex flex-col items-center justify-center pt-5 pb-6">
                    <Upload className="w-8 h-8 mb-2 text-gray-500 dark:text-gray-400" />
                    <p className="mb-2 text-sm text-gray-500 dark:text-gray-400">
                      <span className="font-semibold">{csvFile ? csvFile.name : 'Click to upload'}</span>
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">CSV file</p>
                  </div>
                  <input
                    type="file"
                    className="hidden"
                    accept=".csv"
                    onChange={handleFileChange}
                  />
                </label>
              </div>
            </div>
          ) : (
            <>
              {assets.map((asset, idx) => (
                <div key={idx} className="bg-white dark:bg-gray-800 shadow rounded-lg p-6 mb-4 flex flex-col gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Ticker</label>
                    <input type="text" value={asset.ticker} onChange={e => handleAssetChange(idx, 'ticker', e.target.value)} required className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-base py-2 px-3 text-gray-900 dark:text-white dark:bg-gray-700 dark:border-gray-600" />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Asset Type</label>
                      <select value={asset.asset_type} onChange={e => handleAssetChange(idx, 'asset_type', e.target.value)} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-base py-2 px-3 text-gray-900 dark:text-white dark:bg-gray-700 dark:border-gray-600">
                        <option value="Stock">Stock</option>
                        <option value="Mutual Fund">Mutual Fund</option>
                        <option value="Crypto">Crypto</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Currency</label>
                      <select value={asset.currency} onChange={e => handleAssetChange(idx, 'currency', e.target.value)} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-base py-2 px-3 text-gray-900 dark:text-white dark:bg-gray-700 dark:border-gray-600">
                        <option value="USD">USD</option>
                        <option value="CAD">CAD</option>
                        <option value="EUR">EUR</option>
                      </select>
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Quantity</label>
                    <input type="number" value={asset.quantity} onChange={e => handleAssetChange(idx, 'quantity', e.target.value)} required min="0" step="any" className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-base py-2 px-3 text-gray-900 dark:text-white dark:bg-gray-700 dark:border-gray-600" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Average Cost</label>
                    <input type="number" value={asset.average_cost} onChange={e => handleAssetChange(idx, 'average_cost', e.target.value)} required min="0" step="any" className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-base py-2 px-3 text-gray-900 dark:text-white dark:bg-gray-700 dark:border-gray-600" />
                  </div>
                  {assets.length > 1 && (
                    <button type="button" onClick={() => removeAsset(idx)} className="text-red-600 hover:underline self-end">Remove</button>
                  )}
                </div>
              ))}
              <button type="button" onClick={addAsset} className="inline-flex items-center px-4 py-2 border border-indigo-600 text-indigo-600 rounded-md hover:bg-indigo-50 dark:hover:bg-indigo-900">Add Another Asset</button>
            </>
          )}
          <button type="submit" disabled={isSubmitting} className="w-full inline-flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50 disabled:cursor-not-allowed">
            {isSubmitting ? 'Saving...' : 'Complete Onboarding'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default PortfolioOnboarding;
