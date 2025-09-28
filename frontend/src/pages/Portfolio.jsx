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
    <div className="space-y-8">
      <Suspense fallback={<LoadingSpinner />}>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <div>
            <h2 className="text-2xl font-bold mb-4" style={{ color: 'var(--color-text)' }}>
              Asset Allocation
            </h2>
            <AllocationSection />
          </div>
          <div>
            <h2 className="text-2xl font-bold mb-4" style={{ color: 'var(--color-text)' }}>
              Holdings Overview
            </h2>
            <HoldingsView />
          </div>
        </div>
        <div>
          <h2 className="text-2xl font-bold mb-4" style={{ color: 'var(--color-text)' }}>
            Performance Metrics
          </h2>
          <PerformanceView />
        </div>
      </Suspense>
    </div>
  );
};

export default Portfolio;
