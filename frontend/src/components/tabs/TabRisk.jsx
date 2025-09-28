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
    <Suspense fallback={<LoadingSpinner />}>
      <RiskSection />
    </Suspense>
  );
};

export default TabRisk;
