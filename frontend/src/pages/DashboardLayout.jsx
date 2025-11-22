import React, { useState, useEffect, Suspense } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useCurrency } from '../contexts/CurrencyContext';
import { useTheme } from '../contexts/ThemeContext';
import { Loader2, Menu, TrendingUp, Shield, PieChart, Target, BarChart3, TrendingDown } from 'lucide-react';
import PortfolioService from '../services/portfolioService';
import Sidebar from '../components/Sidebar';
import CurrencySwitcher from '../components/CurrencySwitcher';
import ThemeToggle from '../components/ThemeToggle';

// Import tab components
import TabOverview from '../components/tabs/TabOverview';
import TabRisk from '../components/tabs/TabRisk';
import TabAllocation from '../components/tabs/TabAllocation';
import TabEfficientFrontier from '../components/tabs/TabEfficientFrontier';
import TabMonteCarlo from '../components/tabs/TabMonteCarlo';
import TabCPPI from '../components/tabs/TabCPPI';

const LoadingSpinner = () => (
  <div className="min-h-screen flex items-center justify-center" style={{ backgroundColor: 'var(--color-background)' }}>
    <Loader2 className="h-12 w-12 animate-spin" style={{ color: 'var(--color-primary)' }} />
  </div>
);

const DashboardLayout = () => {
  const [portfolioData, setPortfolioData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');
  const { api, user, logout } = useAuth();
  const { currency } = useCurrency();
  const { isDark } = useTheme();
  const location = useLocation();
  const navigate = useNavigate();

  const tabs = [
    { id: 'overview', label: 'Overview', icon: TrendingUp },
    { id: 'risk', label: 'Risk Analytics', icon: Shield },
    { id: 'allocation', label: 'Asset Allocation', icon: PieChart },
    { id: 'efficient', label: 'Efficient Frontier', icon: Target },
    { id: 'simulation', label: 'Monte Carlo', icon: BarChart3 },
    { id: 'strategy', label: 'CPPI Strategy', icon: TrendingDown },
  ];

  const portfolioService = new PortfolioService(api);

  useEffect(() => {
    if (user) {
      fetchPortfolioData();
    }
  }, [user, currency]); // Re-fetch when currency changes

  useEffect(() => {
    const path = location.pathname;
    if (path.includes('overview')) {
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
  }, [location]);

  const handleTabClick = (tabId) => {
    setActiveTab(tabId);
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

  const fetchPortfolioData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Use lightweight summary endpoint instead of heavy analysis
      // Analysis is called separately by individual tabs as needed
      const summary = await portfolioService.getPortfolioSummary(currency);

      if (summary) {
        setPortfolioData(summary);
      } else {
        setPortfolioData(portfolioService.getMockPortfolioData());
      }
    } catch (err) {
      console.error('Error fetching portfolio data:', err);

      try {
        setPortfolioData(portfolioService.getMockPortfolioData());
        setError('Using sample data. Connect your portfolio to see real metrics.');
      } catch (mockError) {
        setError('Failed to load portfolio data. Please try again.');
      }
    } finally {
      setLoading(false);
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

              <div className="flex flex-col justify-center"> 
                <h1 className="font-bold leading-tight" style={{ color: 'var(--color-text)', fontSize: 'var(--font-size-xl)', margin: 0 }}>Strategic Multi-Asset Portfolio</h1>
                {user && (
                  <p className="text-sm leading-tight mt-1" style={{ color: 'var(--color-text-secondary)', margin: 0 }}>
                    Welcome back, {user.display_name || user.username} • Last Updated: {new Date().toLocaleDateString()}
                  </p>
                )}
              </div>
            </div>

            <div className="flex items-center space-x-3">
              {/* Currency Switcher */}
              <CurrencySwitcher />

              {/* Theme Toggle - New dark mode system */}
              <ThemeToggle />

              <button
                onClick={logout}
                className="px-4 py-2 rounded-lg text-sm font-semibold transition-colors"
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
              <div className="nav-tabs">
                {tabs.map((tab) => {
                  const Icon = tab.icon;
                  return (
                    <button
                      key={tab.id}
                      onClick={() => handleTabClick(tab.id)}
                      className={`nav-tab ${activeTab === tab.id ? 'active' : ''}`}
                    >
                      <div className="flex items-center">
                        <Icon className="h-5 w-5 mr-2" />
                        {tab.label}
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
            <Suspense fallback={<LoadingSpinner />}>
              {renderTabContent()}
            </Suspense>
          </div>
        </main>
      </div>
    </div>
  );
};

export default DashboardLayout;
