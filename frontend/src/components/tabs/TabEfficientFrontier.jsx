import React, { Suspense } from 'react';
import { Loader2 } from 'lucide-react';

// Lazy load the efficient frontier section
const EfficientFrontierSection = React.lazy(() => import('../EfficientFrontierSection'));

const LoadingSpinner = () => (
  <div className="flex items-center justify-center h-64">
    <Loader2 className="h-12 w-12 animate-spin" style={{ color: 'var(--color-primary)' }} />
  </div>
);

const TabEfficientFrontier = () => {
  return (
    <section className="dashboard-section active">
      <h2 style={{ 
        marginBottom: 'var(--space-24)', 
        fontSize: 'var(--font-size-2xl)', 
        color: 'var(--color-text)',
        fontWeight: 'var(--font-weight-semibold)'
      }}>
        Efficient Frontier Analysis
      </h2>
      <div className="explanation-card" style={{
        backgroundColor: 'var(--color-bg-2)',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius-lg)',
        padding: 'var(--space-20)',
        marginBottom: 'var(--space-24)'
      }}>
        <p style={{ 
          margin: 0, 
          fontSize: 'var(--font-size-base)', 
          color: 'var(--color-text)', 
          lineHeight: 'var(--line-height-normal)' 
        }}>
          The efficient frontier shows optimal risk-return combinations. Portfolios on the frontier provide maximum return for each level of risk. Your current portfolio (marked in blue) sits near the efficient frontier, indicating good optimization.
        </p>
      </div>
      <Suspense fallback={<LoadingSpinner />}>
        <EfficientFrontierSection />
      </Suspense>
    </section>
  );
};

export default TabEfficientFrontier;
