import React, { useState, useEffect, Suspense, lazy } from 'react';
import { Outlet, useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useCurrency } from '../contexts/CurrencyContext';
import { useTheme } from '../contexts/ThemeContext';
import { Loader2, Menu, TrendingUp, Shield, PieChart, Target, BarChart3, TrendingDown } from 'lucide-react';
import Sidebar from '../components/Sidebar';
import CurrencySwitcher from '../components/CurrencySwitcher';
import ThemeToggle from '../components/ThemeToggle';
import PortfolioChatWidget from '../components/PortfolioChatWidget';
import { DashboardSkeleton } from '../components/ui/Skeleton';

// Lazy load tab components
const TabOverview = lazy(() => import('../components/tabs/TabOverview'));
const TabRisk = lazy(() => import('../components/tabs/TabRisk'));
const TabAllocation = lazy(() => import('../components/tabs/TabAllocation'));
const TabEfficientFrontier = lazy(() => import('../components/tabs/TabEfficientFrontier'));
const TabMonteCarlo = lazy(() => import('../components/tabs/TabMonteCarlo'));
const TabCPPI = lazy(() => import('../components/tabs/TabCPPI'));

const LoadingSpinner = () => (
  <div className="min-h-screen flex items-center justify-center" style={{ backgroundColor: 'var(--color-background)' }}>
    <Loader2 className="h-12 w-12 animate-spin" style={{ color: 'var(--color-primary)' }} />
  </div>
);

const DashboardLayout = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');
  const { user, logout } = useAuth();
  const { isDark } = useTheme();
  const location = useLocation();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const tabs = [
    { id: 'overview', label: 'Overview', icon: TrendingUp },
    { id: 'risk', label: 'Risk Analytics', icon: Shield },
    { id: 'allocation', label: 'Asset Allocation', icon: PieChart },
    { id: 'efficient', label: 'Efficient Frontier', icon: Target },
    { id: 'simulation', label: 'Monte Carlo', icon: BarChart3 },
    { id: 'strategy', label: 'CPPI Strategy', icon: TrendingDown },
  ];

  useEffect(() => {
    const path = location.pathname;
    const viewParam = searchParams.get('view');

    if (viewParam && tabs.find(t => t.id === viewParam)) {
      setActiveTab(viewParam);
    } else if (path.includes('overview')) {
      setActiveTab('overview');
    } else if (path.includes('portfolio')) {
      setActiveTab('allocation');
    } else if (path.includes('analytics')) {
      setActiveTab('risk');
    } else if (path.includes('update-portfolio')) {
      setActiveTab('overview');
    } else if (path === '/dashboard' || path === '/dashboard/') {
      setActiveTab('overview');
    }
  }, [location, searchParams]);

  const handleTabClick = (tabId) => {
    setActiveTab(tabId);
    // Update URL to reflect tab change for deep linking
    const currentPath = location.pathname;
    if (currentPath.includes('analytics')) {
      setSearchParams({ view: tabId });
    } else {
      // If on another page, navigate to analytics with view param if it's an analytics tab
      // Or just update state if it's a general tab?
      // DashboardLayout logic is a bit mixed. Let's keep it simple:
      // If it's an analytics tab, go to analytics.
      if (['risk', 'efficient', 'simulation', 'strategy'].includes(tabId)) {
        navigate(`/dashboard/analytics?view=${tabId}`);
      } else if (tabId === 'allocation') {
        navigate('/dashboard/portfolio');
      } else {
        navigate('/dashboard/overview');
      }
    }
  };

  const getTabTitle = () => {
    switch (activeTab) {
      case 'overview':
        return 'Performance Overview';
      case 'risk':
        return 'Risk Analytics';
      case 'allocation':
        return 'Asset Allocation';
      case 'efficient':
        return 'Efficient Frontier Analysis';
      case 'simulation':
        return 'Monte Carlo Simulation';
      case 'strategy':
        return 'CPPI Strategy Analysis';
      default:
        return 'Performance Overview';
    }
  };

  const renderTabContent = () => {
    if (location.pathname.includes('update-portfolio') || location.pathname.includes('live-market')) {
      return <Outlet />;
    }
    
    switch (activeTab) {
      case 'overview':
        return <TabOverview />;
      case 'risk':
        return <TabRisk />;
      case 'allocation':
        return <TabAllocation />;
      case 'efficient':
        return <TabEfficientFrontier />;
      case 'simulation':
        return <TabMonteCarlo />;
      case 'strategy':
        return <TabCPPI />;
      default:
        return <TabOverview />;
    }
  };

  return (
    <div className="min-h-screen flex" style={{ backgroundColor: 'var(--color-background)' }}> 
      <Sidebar 
        sidebarOpen={sidebarOpen} 
        setSidebarOpen={setSidebarOpen} 
        sidebarCollapsed={sidebarCollapsed}
        setSidebarCollapsed={setSidebarCollapsed}
        darkMode={isDark} 
      />

      <div className="flex-1 flex flex-col overflow-hidden"> 
        {/* Sticky Header */}
        <header className="sticky top-0 z-30 dashboard-header" style={{ backgroundColor: 'var(--color-surface)', borderBottom: '1px solid var(--color-border)' }}>
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex justify-between items-center h-16">
            <div className="flex items-center space-x-4"> 
              {/* Mobile menu button */}
              <button
                type="button"
                className="md:hidden p-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-inset flex items-center justify-center"
                style={{ color: 'var(--color-text-secondary)' }}
                onClick={() => setSidebarOpen(true)}
              >
                <span className="sr-only">Open sidebar</span>
                <Menu className="h-6 w-6" aria-hidden="true" />
              </button>

              {/* Desktop sidebar toggle - show when sidebar is collapsed */}
              {sidebarCollapsed && (
                <button
                  type="button"
                  className="hidden md:flex p-2 rounded-lg focus:outline-none focus:ring-2 items-center justify-center"
                  style={{ color: 'var(--color-text-secondary)' }}
                  onClick={() => setSidebarCollapsed(false)}
                  title="Show sidebar"
                >
                  <Menu className="h-6 w-6" aria-hidden="true" />
                </button>
              )}

              <div className="flex flex-col justify-center flex-1 min-w-0"> 
                <h1 className="font-bold leading-tight truncate" style={{ color: 'var(--color-text)', fontSize: 'clamp(1.125rem, 2vw, 1.5rem)', margin: 0 }}>Strategic Multi-Asset Portfolio</h1>
                {user && (
                  <p className="text-xs sm:text-sm leading-tight mt-1 truncate" style={{ color: 'var(--color-text-secondary)', margin: 0 }}>
                    Welcome back, {user.display_name || user.username} • {new Date().toLocaleDateString()}
                  </p>
                )}
              </div>
            </div>

            <div className="flex items-center space-x-2 sm:space-x-3">
              {/* Currency Switcher */}
              <div className="hidden sm:block">
                <CurrencySwitcher />
              </div>

              {/* Theme Toggle - New dark mode system */}
              <ThemeToggle />

              <button
                onClick={logout}
                className="px-3 py-1.5 sm:px-4 sm:py-2 rounded-lg text-xs sm:text-sm font-semibold transition-colors"
                style={{
                  backgroundColor: 'var(--color-error)',
                  color: 'var(--color-white)'
                }}
              >
                Logout
              </button>
            </div>
          </div>
        </header>

        {/* Sticky Navigation Tabs */}
        {!location.pathname.includes('update-portfolio') && !location.pathname.includes('live-market') && (
          <nav className="sticky top-16 z-20 dashboard-nav" style={{ backgroundColor: 'var(--color-surface)', borderBottom: '1px solid var(--color-border)' }}>
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <div className="nav-tabs overflow-x-auto scrollbar-hide">
                {tabs.map((tab) => {
                  const Icon = tab.icon;
                  return (
                    <button
                      key={tab.id}
                      onClick={() => handleTabClick(tab.id)}
                      className={`nav-tab ${activeTab === tab.id ? 'active' : ''} whitespace-nowrap`}
                    >
                      <div className="flex items-center">
                        <Icon className="h-4 w-4 sm:h-5 sm:w-5 mr-1.5 sm:mr-2" />
                        <span className="text-sm sm:text-base">{tab.label}</span>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          </nav>
        )}

        <main className="flex-1 overflow-y-auto dashboard" style={{ backgroundColor: 'var(--color-background)' }}> 
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8" style={{ padding: 'var(--space-24) 16px' }}>
            {!location.pathname.includes('update-portfolio') && !location.pathname.includes('live-market') && (
              <h2 style={{ 
                marginBottom: 'var(--space-24)', 
                fontSize: 'var(--font-size-2xl)', 
                color: 'var(--color-text)',
                fontWeight: 'var(--font-weight-semibold)'
              }}>
                {getTabTitle()}
              </h2>
            )}
            <Suspense fallback={<DashboardSkeleton />}>
              {renderTabContent()}
            </Suspense>
          </div>
        </main>
      </div>
      <PortfolioChatWidget />
    </div>
  );
};

export default DashboardLayout;
