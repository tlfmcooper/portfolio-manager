import React, { Suspense } from 'react';
import { Loader2 } from 'lucide-react';

// Lazy load the monte carlo section
const MonteCarloSection = React.lazy(() => import('../MonteCarloSection'));

const LoadingSpinner = () => (
  <div className="flex items-center justify-center h-64">
    <Loader2 className="h-12 w-12 animate-spin" style={{ color: 'var(--color-primary)' }} />
  </div>
);

const TabMonteCarlo = () => {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <MonteCarloSection />
    </Suspense>
  );
};

export default TabMonteCarlo;
