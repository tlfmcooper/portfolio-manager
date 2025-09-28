import React, { Suspense } from 'react';
import { Loader2 } from 'lucide-react';

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
  return (
    <section className="dashboard-section active">
      <h2 style={{ 
        marginBottom: 'var(--space-24)', 
        fontSize: 'var(--font-size-2xl)', 
        color: 'var(--color-text)',
        fontWeight: 'var(--font-weight-semibold)'
      }}>
        Portfolio Management
      </h2>
      <Suspense fallback={<LoadingSpinner />}>
        <div className="allocation-grid" style={{ marginBottom: 'var(--space-32)' }}>
          <div>
            <h3 style={{ 
              marginBottom: 'var(--space-16)', 
              fontSize: 'var(--font-size-xl)', 
              color: 'var(--color-text)',
              fontWeight: 'var(--font-weight-medium)'
            }}>
              Asset Allocation
            </h3>
            <AllocationSection />
          </div>
          <div>
            <h3 style={{ 
              marginBottom: 'var(--space-16)', 
              fontSize: 'var(--font-size-xl)', 
              color: 'var(--color-text)',
              fontWeight: 'var(--font-weight-medium)'
            }}>
              Holdings Overview
            </h3>
            <HoldingsView />
          </div>
        </div>
        <div>
          <h3 style={{ 
            marginBottom: 'var(--space-16)', 
            fontSize: 'var(--font-size-xl)', 
            color: 'var(--color-text)',
            fontWeight: 'var(--font-weight-medium)'
          }}>
            Performance Metrics
          </h3>
          <PerformanceView />
        </div>
      </Suspense>
    </section>
  );
};

export default Portfolio;
