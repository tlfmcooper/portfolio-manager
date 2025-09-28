import React, { Suspense } from 'react';
import { Loader2 } from 'lucide-react';

// Lazy load the overview section
const OverviewSection = React.lazy(() => import('../components/OverviewSection'));

const LoadingSpinner = () => (
  <div className="flex items-center justify-center h-64">
    <Loader2 className="h-12 w-12 animate-spin" style={{ color: 'var(--color-primary)' }} />
  </div>
);

const Overview = () => {
  return (
    <div className="space-y-8">
      <Suspense fallback={<LoadingSpinner />}>
        <OverviewSection />
      </Suspense>
    </div>
  );
};

export default Overview;
