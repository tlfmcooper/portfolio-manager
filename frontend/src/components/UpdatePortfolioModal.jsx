import React, { useState } from 'react';
import { X } from 'lucide-react';
import BuyAssetForm from './forms/BuyAssetForm';
import SellAssetForm from './forms/SellAssetForm';
import EditAssetForm from './forms/EditAssetForm';

const UpdatePortfolioModal = ({ isOpen, onClose, onPortfolioUpdated }) => {
  const [activeTab, setActiveTab] = useState('buy');

  if (!isOpen) {
    return null;
  }

  const handleAssetUpdated = () => {
    // Callback to refresh portfolio data after any operation
    if (onPortfolioUpdated) {
      onPortfolioUpdated();
    }
  };

  const renderForm = () => {
    switch (activeTab) {
      case 'buy':
        return <BuyAssetForm onAssetAdded={handleAssetUpdated} />;
      case 'sell':
        return <SellAssetForm onAssetSold={handleAssetUpdated} />;
      case 'edit':
        return <EditAssetForm onAssetEdited={handleAssetUpdated} />;
      default:
        return <BuyAssetForm onAssetAdded={handleAssetUpdated} />;
    }
  };

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50" id="portfolio-modal">
      <div className="relative top-8 mx-auto p-0 border shadow-lg rounded-lg bg-white dark:bg-gray-800 max-w-md w-full mx-4">
        <div className="p-6">
          {/* Header */}
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-xl leading-6 font-medium text-gray-900 dark:text-white">
              Update Portfolio
            </h3>
            <button 
              onClick={onClose} 
              className="text-gray-400 hover:text-gray-500 dark:hover:text-gray-300 transition-colors"
            >
              <X className="h-6 w-6" />
            </button>
          </div>

          {/* Tabs */}
          <div className="border-b border-gray-200 dark:border-gray-700 mb-6">
            <nav className="-mb-px flex space-x-8" aria-label="Tabs">
              <button
                onClick={() => setActiveTab('buy')}
                className={`py-2 px-1 border-b-2 font-medium text-sm transition-colors ${
                  activeTab === 'buy'
                    ? 'border-green-500 text-green-600 dark:text-green-400'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
                }`}
              >
                Buy Assets
              </button>
              <button
                onClick={() => setActiveTab('sell')}
                className={`py-2 px-1 border-b-2 font-medium text-sm transition-colors ${
                  activeTab === 'sell'
                    ? 'border-red-500 text-red-600 dark:text-red-400'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
                }`}
              >
                Sell Assets
              </button>
              <button
                onClick={() => setActiveTab('edit')}
                className={`py-2 px-1 border-b-2 font-medium text-sm transition-colors ${
                  activeTab === 'edit'
                    ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
                }`}
              >
                Edit Holdings
              </button>
            </nav>
          </div>

          {/* Form Content */}
          <div className="min-h-64">
            {renderForm()}
          </div>
        </div>
      </div>
    </div>
  );
};

export default UpdatePortfolioModal;