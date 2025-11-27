import React, { Suspense, useState } from 'react';
import { Loader2, PieChart, TrendingUp, Wallet, DollarSign, Receipt } from 'lucide-react';
import CashBalance from '../components/CashBalance';
import TransactionHistory from '../components/TransactionHistory';
import AddCashForm from '../components/forms/AddCashForm';

// Lazy load portfolio-related sections
const AllocationSection = React.lazy(() => import('../components/AllocationSection'));
const HoldingsView = React.lazy(() => import('../components/HoldingsView'));
const PerformanceView = React.lazy(() => import('../components/PerformanceView'));

const LoadingSpinner = () => (
  <div className="flex items-center justify-center h-64">
    <Loader2 className="h-12 w-12 animate-spin" style={{ color: 'var(--color-primary)' }} />
  </div>
);

const Portfolio = () => {
  const [showAddCashModal, setShowAddCashModal] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  const handleAddCashSuccess = () => {
    // Refresh components by updating key
    setRefreshKey(prev => prev + 1);
  };

  return (
    <section className="dashboard-section active">
      {/* Header with Icon */}
      <div className="flex items-center gap-3 mb-6">
        <div
          className="p-3 rounded-xl"
          style={{
            backgroundColor: 'var(--color-primary-light)',
            color: 'var(--color-primary)'
          }}
        >
          <Wallet className="h-6 w-6" />
        </div>
        <div>
          <h2 style={{
            fontSize: 'var(--font-size-2xl)',
            color: 'var(--color-text)',
            fontWeight: 'var(--font-weight-semibold)',
            marginBottom: '4px'
          }}>
            Portfolio Management
          </h2>
          <p style={{
            fontSize: 'var(--font-size-sm)',
            color: 'var(--color-text-secondary)'
          }}>
            Track your investments, cash balance, and transaction history
          </p>
        </div>
      </div>

      <Suspense fallback={<LoadingSpinner />}>
        {/* Cash Balance Section */}
        <div style={{ marginBottom: 'var(--space-32)' }}>
          <div className="flex items-center gap-2 mb-4">
            <DollarSign className="h-5 w-5" style={{ color: 'var(--color-primary)' }} />
            <h3 style={{
              fontSize: 'var(--font-size-xl)',
              color: 'var(--color-text)',
              fontWeight: 'var(--font-weight-medium)'
            }}>
              Cash Management
            </h3>
          </div>
          <CashBalance
            key={`cash-${refreshKey}`}
            onAddCash={() => setShowAddCashModal(true)}
          />
        </div>
        {/* Asset Allocation Section */}
        <div style={{ marginBottom: 'var(--space-32)' }}>
          <div className="flex items-center gap-2 mb-4">
            <PieChart className="h-5 w-5" style={{ color: 'var(--color-primary)' }} />
            <h3 style={{ 
              fontSize: 'var(--font-size-xl)', 
              color: 'var(--color-text)',
              fontWeight: 'var(--font-weight-medium)'
            }}>
              Asset Allocation
            </h3>
          </div>
          <AllocationSection />
        </div>

        {/* Holdings Overview Section */}
        <div style={{ marginBottom: 'var(--space-32)' }}>
          <div className="flex items-center gap-2 mb-4">
            <Wallet className="h-5 w-5" style={{ color: 'var(--color-primary)' }} />
            <h3 style={{ 
              fontSize: 'var(--font-size-xl)', 
              color: 'var(--color-text)',
              fontWeight: 'var(--font-weight-medium)'
            }}>
              Holdings Overview
            </h3>
          </div>
          <HoldingsView />
        </div>

        {/* Performance Metrics Section */}
        <div style={{ marginBottom: 'var(--space-32)' }}>
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp className="h-5 w-5" style={{ color: 'var(--color-primary)' }} />
            <h3 style={{
              fontSize: 'var(--font-size-xl)',
              color: 'var(--color-text)',
              fontWeight: 'var(--font-weight-medium)'
            }}>
              Performance Metrics
            </h3>
          </div>
          <PerformanceView />
        </div>

        {/* Transaction History Section */}
        <div>
          <div className="flex items-center gap-2 mb-4">
            <Receipt className="h-5 w-5" style={{ color: 'var(--color-primary)' }} />
            <h3 style={{
              fontSize: 'var(--font-size-xl)',
              color: 'var(--color-text)',
              fontWeight: 'var(--font-weight-medium)'
            }}>
              Transaction History
            </h3>
          </div>
          <TransactionHistory key={`txns-${refreshKey}`} />
        </div>
      </Suspense>

      {/* Add Cash Modal */}
      {showAddCashModal && (
        <AddCashForm
          onClose={() => setShowAddCashModal(false)}
          onSuccess={handleAddCashSuccess}
        />
      )}
    </section>
  );
};

export default Portfolio;
