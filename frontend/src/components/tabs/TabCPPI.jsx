import React, { Suspense } from 'react';
import { Loader2 } from 'lucide-react';

// Lazy load the CPPI section
const CPPISection = React.lazy(() => import('../CPPISection'));

const LoadingSpinner = () => (
  <div className="flex items-center justify-center h-64">
    <Loader2 className="h-12 w-12 animate-spin" style={{ color: 'var(--color-primary)' }} />
  </div>
);

const TabCPPI = () => {
  return (
    <>
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
          CPPI (Constant Proportion Portfolio Insurance) is a dynamic strategy that adjusts risk exposure to provide downside protection while maintaining upside participation. The strategy outperformed buy-and-hold by 4.9%.
        </p>
      </div>
      <Suspense fallback={<LoadingSpinner />}>
        <CPPISection />
      </Suspense>
    </>
  );
};

export default TabCPPI;
