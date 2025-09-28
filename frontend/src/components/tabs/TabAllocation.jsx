import React, { Suspense } from 'react';
import { Loader2 } from 'lucide-react';

// Lazy load the allocation section
const AllocationSection = React.lazy(() => import('../AllocationSection'));

const LoadingSpinner = () => (
  <div className="flex items-center justify-center h-64">
    <Loader2 className="h-12 w-12 animate-spin" style={{ color: 'var(--color-primary)' }} />
  </div>
);

const TabAllocation = () => {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <AllocationSection />
    </Suspense>
  );
};

export default TabAllocation;
