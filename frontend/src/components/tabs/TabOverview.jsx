import React, { Suspense } from 'react';
import { Loader2 } from 'lucide-react';
import PortfolioWorkspace from '../PortfolioWorkspace';

// Lazy load the overview section
const OverviewSection = React.lazy(() => import('../OverviewSection'));

const LoadingSpinner = () => (
  <div className="flex items-center justify-center h-64">
    <Loader2 className="h-12 w-12 animate-spin" style={{ color: 'var(--color-primary)' }} />
  </div>
);

const TabOverview = () => {
  return (
    <>
    <PortfolioWorkspace />
    <Suspense fallback={<LoadingSpinner />}>
      <OverviewSection />
    </Suspense>
    </>
  );
};

export default TabOverview;
