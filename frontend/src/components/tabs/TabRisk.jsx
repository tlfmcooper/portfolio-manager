import React, { Suspense } from 'react';
import { Loader2 } from 'lucide-react';

// Lazy load the risk section
const RiskSection = React.lazy(() => import('../RiskSection'));

const LoadingSpinner = () => (
  <div className="flex items-center justify-center h-64">
    <Loader2 className="h-12 w-12 animate-spin" style={{ color: 'var(--color-primary)' }} />
  </div>
);

const TabRisk = () => {
  return (
    <section className="dashboard-section active">
      <h2 style={{ 
        marginBottom: 'var(--space-24)', 
        fontSize: 'var(--font-size-2xl)', 
        color: 'var(--color-text)',
        fontWeight: 'var(--font-weight-semibold)'
      }}>
        Risk Analytics
      </h2>
      <Suspense fallback={<LoadingSpinner />}>
        <RiskSection />
      </Suspense>
    </section>
  );
};

export default TabRisk;
