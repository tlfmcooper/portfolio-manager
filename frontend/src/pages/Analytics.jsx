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
    <div className="space-y-8">
      <Suspense fallback={<LoadingSpinner />}>
        <div>
          <h2 className="text-2xl font-bold mb-4" style={{ color: 'var(--color-text)' }}>
            Risk Analytics
          </h2>
          <RiskSection />
        </div>
        
        <div>
          <h2 className="text-2xl font-bold mb-4" style={{ color: 'var(--color-text)' }}>
            Efficient Frontier Analysis
          </h2>
          <EfficientFrontierSection />
        </div>
        
        <div>
          <h2 className="text-2xl font-bold mb-4" style={{ color: 'var(--color-text)' }}>
            Monte Carlo Simulation
          </h2>
          <MonteCarloSection />
        </div>
        
        <div>
          <h2 className="text-2xl font-bold mb-4" style={{ color: 'var(--color-text)' }}>
            CPPI Strategy
          </h2>
          <CPPISection />
        </div>
      </Suspense>
    </div>
  );
};

export default Analytics;
