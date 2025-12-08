import React, { Suspense, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Loader2, Shield, TrendingUp, BarChart3, Target, PieChart as PieChartIcon } from 'lucide-react';

// Lazy load analytics sections
const RiskSection = React.lazy(() => import('../components/RiskSection'));
const AllocationSection = React.lazy(() => import('../components/AllocationSection'));
const EfficientFrontierSection = React.lazy(() => import('../components/EfficientFrontierSection'));
const MonteCarloSection = React.lazy(() => import('../components/MonteCarloSection'));
const CPPISection = React.lazy(() => import('../components/CPPISection'));

const LoadingSpinner = () => (
  <div className="flex items-center justify-center h-64">
    <Loader2 className="h-12 w-12 animate-spin" style={{ color: 'var(--color-primary)' }} />
  </div>
);

const Analytics = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const activeTab = searchParams.get('view') || 'risk';

  const handleTabChange = (tab) => {
    setSearchParams({ view: tab });
  };

  const tabs = [
    { id: 'risk', label: 'Risk Analytics', icon: Shield },
    { id: 'allocation', label: 'Asset Allocation', icon: PieChartIcon }, // Added Asset Allocation tab
    { id: 'efficient-frontier', label: 'Efficient Frontier', icon: Target },
    { id: 'monte-carlo', label: 'Monte Carlo', icon: BarChart3 },
    { id: 'cppi', label: 'CPPI Strategy', icon: TrendingUp },
  ];

  return (
    <section className="dashboard-section active space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <h2 className="text-2xl font-semibold text-gray-900 dark:text-white">
          Advanced Analytics
        </h2>
        
        {/* Tabs Navigation */}
        <div className="flex overflow-x-auto pb-2 md:pb-0 gap-2 no-scrollbar">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => handleTabChange(tab.id)}
                className={`
                  flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors
                  ${isActive 
                    ? 'bg-indigo-600 text-white shadow-sm' 
                    : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 border border-gray-200 dark:border-gray-700'
                  }
                `}
              >
                <Icon className="h-4 w-4" />
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>

      <Suspense fallback={<LoadingSpinner />}>
        <div className="min-h-[500px]">
          {activeTab === 'risk' && <RiskSection />}
          {activeTab === 'allocation' && <AllocationSection />}
          {activeTab === 'efficient-frontier' && <EfficientFrontierSection />}
          {activeTab === 'monte-carlo' && <MonteCarloSection />}
          {activeTab === 'cppi' && <CPPISection />}
        </div>
      </Suspense>
    </section>
  );
};

export default Analytics;
