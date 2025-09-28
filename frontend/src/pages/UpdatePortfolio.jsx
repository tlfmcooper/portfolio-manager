
import React, { useState } from 'react';
import BuyAssetForm from '../components/forms/BuyAssetForm';
import SellAssetForm from '../components/forms/SellAssetForm';
import EditAssetForm from '../components/forms/EditAssetForm';

const UpdatePortfolio = () => {
  const [activeTab, setActiveTab] = useState('buy');

  const handleAssetUpdated = () => {
    // Callback to refresh portfolio data after any operation
    console.log('Portfolio updated successfully');
    // Could add toast notification here
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
    <section className="dashboard-section active">
      <h2 style={{ 
        marginBottom: 'var(--space-24)', 
        fontSize: 'var(--font-size-2xl)', 
        color: 'var(--color-text)',
        fontWeight: 'var(--font-weight-semibold)'
      }}>
        Update Portfolio
      </h2>
      
      <div className="explanation-card" style={{
        backgroundColor: 'var(--color-bg-2)',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius-lg)',
        padding: 'var(--space-20)',
        marginBottom: 'var(--space-32)'
      }}>
        <p style={{ 
          margin: 0, 
          fontSize: 'var(--font-size-base)', 
          color: 'var(--color-text)', 
          lineHeight: 'var(--line-height-normal)' 
        }}>
          Manage your portfolio holdings by buying new assets, selling existing positions, or editing quantities and costs. 
          All transactions will be properly recorded and your portfolio metrics will be updated automatically.
        </p>
      </div>

      {/* Main Content Card */}
      <div style={{
        backgroundColor: 'var(--color-surface)',
        border: '1px solid var(--color-card-border)',
        borderRadius: 'var(--radius-lg)',
        padding: 'var(--space-32)',
        boxShadow: 'var(--shadow-sm)'
      }}>
        {/* Tab Navigation */}
        <div style={{
          borderBottom: '1px solid var(--color-border)',
          marginBottom: 'var(--space-32)'
        }}>
          <nav className="flex space-x-8" style={{ marginBottom: '-1px' }}>
            <button
              onClick={() => setActiveTab('buy')}
              className="py-2 px-1 border-b-2 font-medium text-sm transition-all duration-200"
              style={{
                borderBottomColor: activeTab === 'buy' ? 'var(--color-success)' : 'transparent',
                color: activeTab === 'buy' ? 'var(--color-success)' : 'var(--color-text-secondary)'
              }}
            >
              Buy Assets
            </button>
            <button
              onClick={() => setActiveTab('sell')}
              className="py-2 px-1 border-b-2 font-medium text-sm transition-all duration-200"
              style={{
                borderBottomColor: activeTab === 'sell' ? 'var(--color-error)' : 'transparent',
                color: activeTab === 'sell' ? 'var(--color-error)' : 'var(--color-text-secondary)'
              }}
            >
              Sell Assets
            </button>
            <button
              onClick={() => setActiveTab('edit')}
              className="py-2 px-1 border-b-2 font-medium text-sm transition-all duration-200"
              style={{
                borderBottomColor: activeTab === 'edit' ? 'var(--color-primary)' : 'transparent',
                color: activeTab === 'edit' ? 'var(--color-primary)' : 'var(--color-text-secondary)'
              }}
            >
              Edit Holdings
            </button>
          </nav>
        </div>

        {/* Form Content */}
        <div style={{ minHeight: '400px' }}>
          {renderForm()}
        </div>
      </div>
    </section>
  );
};

export default UpdatePortfolio;
