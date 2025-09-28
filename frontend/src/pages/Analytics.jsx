import React, { Suspense } from 'react';
import { Loader2 } from 'lucide-react';

// Lazy load analytics sections
const RiskSection = React.lazy(() => import('../components/RiskSection'));
const EfficientFrontierSection = React.lazy(() => import('../components/EfficientFrontierSection'));
const MonteCarloSection = React.lazy(() => import('../components/MonteCarloSection'));
const CPPISection = React.lazy(() => import('../components/CPPISection'));

const LoadingSpinner = () => (
  <div className="flex items-center justify-center h-64">
    <Loader2 className="h-12 w-12 animate-spin" style={{ color: 'var(--color-primary)' }} />
  </div>
);

const Analytics = () => {
  return (
    <section className="dashboard-section active">
      <h2 style={{ 
        marginBottom: 'var(--space-24)', 
        fontSize: 'var(--font-size-2xl)', 
        color: 'var(--color-text)',
        fontWeight: 'var(--font-weight-semibold)'
      }}>
        Advanced Analytics
      </h2>
      <Suspense fallback={<LoadingSpinner />}>
        <div style={{ marginBottom: 'var(--space-32)' }}>
          <h3 style={{ 
            marginBottom: 'var(--space-16)', 
            fontSize: 'var(--font-size-xl)', 
            color: 'var(--color-text)',
            fontWeight: 'var(--font-weight-medium)'
          }}>
            Risk Analytics
          </h3>
          <RiskSection />
        </div>
        
        <div style={{ marginBottom: 'var(--space-32)' }}>
          <h3 style={{ 
            marginBottom: 'var(--space-16)', 
            fontSize: 'var(--font-size-xl)', 
            color: 'var(--color-text)',
            fontWeight: 'var(--font-weight-medium)'
          }}>
            Efficient Frontier Analysis
          </h3>
          <EfficientFrontierSection />
        </div>
        
        <div style={{ marginBottom: 'var(--space-32)' }}>
          <h3 style={{ 
            marginBottom: 'var(--space-16)', 
            fontSize: 'var(--font-size-xl)', 
            color: 'var(--color-text)',
            fontWeight: 'var(--font-weight-medium)'
          }}>
            Monte Carlo Simulation
          </h3>
          <MonteCarloSection />
        </div>
        
        <div style={{ marginBottom: 'var(--space-32)' }}>
          <h3 style={{ 
            marginBottom: 'var(--space-16)', 
            fontSize: 'var(--font-size-xl)', 
            color: 'var(--color-text)',
            fontWeight: 'var(--font-weight-medium)'
          }}>
            CPPI Strategy
          </h3>
          <CPPISection />
        </div>
      </Suspense>
    </section>
  );
};

export default Analytics;
