import React, { Suspense, useState, useEffect } from 'react';
import { Loader2 } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';

// Lazy load the CPPI section
const CPPISection = React.lazy(() => import('../CPPISection'));

const LoadingSpinner = () => (
  <div className="flex items-center justify-center h-64">
    <Loader2 className="h-12 w-12 animate-spin" style={{ color: 'var(--color-primary)' }} />
  </div>
);

const TabCPPI = () => {
  const [cppiData, setCppiData] = useState(null);
  const { api, portfolioId } = useAuth(); // CRITICAL FIX: Get portfolioId from context

  useEffect(() => {
    const fetchData = async () => {
      if (!portfolioId) return; // Wait for portfolioId to load

      try {
        const response = await api.get(`/analysis/portfolios/${portfolioId}/analysis/cppi`); // CRITICAL FIX: Use dynamic portfolioId
        setCppiData(response.data);
      } catch (err) {
        console.error('Failed to fetch CPPI data:', err);
      }
    };

    fetchData();
  }, [api, portfolioId]); // CRITICAL FIX: Add portfolioId to dependencies

  const formatPercentage = (value) => {
    if (typeof value !== 'number') return 'N/A';
    return `${(value * 100).toFixed(1)}%`;
  };

  const getPerformanceText = () => {
    if (!cppiData || typeof cppiData.outperformance !== 'number') {
      return 'The strategy performance is being calculated.';
    }
    
    const outperformance = cppiData.outperformance;
    const performanceWord = outperformance >= 0 ? 'outperformed' : 'underperformed';
    const absPerformance = formatPercentage(Math.abs(outperformance));
    
    return `The strategy ${performanceWord} buy-and-hold by ${absPerformance}.`;
  };

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
          CPPI (Constant Proportion Portfolio Insurance) is a dynamic strategy that adjusts risk exposure to provide downside protection while maintaining upside participation. {getPerformanceText()}
        </p>
      </div>
      <Suspense fallback={<LoadingSpinner />}>
        <CPPISection />
      </Suspense>
    </>
  );
};

export default TabCPPI;
