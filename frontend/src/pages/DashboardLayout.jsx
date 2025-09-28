
import React, { useState, useEffect, Suspense } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Loader2, Menu, TrendingUp, Shield, PieChart, Target, BarChart3, TrendingDown } from 'lucide-react';
import PortfolioService from '../services/portfolioService';
import Sidebar from '../components/Sidebar';

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
  const [darkMode, setDarkMode] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');
  const { api, user, logout } = useAuth();
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

  // Initialize portfolio service
  const portfolioService = new PortfolioService(api);

  useEffect(() => {
    if (user) {
      fetchPortfolioData();
    }
  }, [user]);

  // Set active tab based on current route
  useEffect(() => {
    const path = location.pathname;
    if (path.includes('overview')) {
      setActiveTab('overview');
    } else if (path.includes('portfolio')) {
      setActiveTab('allocation');
    } else if (path.includes('analytics')) {
      setActiveTab('risk'); // Default to risk for analytics page
    } else if (path.includes('update-portfolio')) {
      setActiveTab('overview'); // Default for update-portfolio
    } else if (path === '/dashboard' || path === '/dashboard/') {
      setActiveTab('overview'); // Default to overview
    }
  }, [location]);

  const handleTabClick = (tabId) => {
    setActiveTab(tabId);
    // No need to navigate - just change the active tab state
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
    // If on update-portfolio route, show the outlet for the UpdatePortfolio component
    if (location.pathname.includes('update-portfolio')) {
      return <Outlet />;
    }
    
    // Otherwise, show the tab-based content
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

      // Try to get portfolio analysis first (most comprehensive)
      const analysis = await portfolioService.getPortfolioAnalysis();
      
      if (analysis) {
        setPortfolioData(analysis);
      } else {
        // Fallback to mock data if no analysis available
        setPortfolioData(portfolioService.getMockPortfolioData());
      }
    } catch (err) {
      console.error('Error fetching portfolio data:', err);
      
      // Use mock data as fallback
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

  const toggleTheme = () => {
    const newDarkMode = !darkMode;
    setDarkMode(newDarkMode);
    document.documentElement.setAttribute('data-color-scheme', newDarkMode ? 'dark' : 'light');
  };

  return (
    <div className="min-h-screen flex bg-gray-100 dark:bg-gray-900"> 
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} darkMode={darkMode} toggleDarkMode={toggleTheme} />

      <div className="flex-1 flex flex-col"> 
        <header className="dashboard-header">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex justify-between items-center">
            <div className="flex items-center"> 
              <button
                type="button"
                className="md:hidden p-1 text-gray-500 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-indigo-500"
                onClick={() => setSidebarOpen(true)}
              >
                <span className="sr-only">Open sidebar</span>
                <Menu className="h-6 w-6" aria-hidden="true" />
              </button>
              <div className="portfolio-info ml-4"> 
                <h1>Strategic Multi-Asset Portfolio</h1>
                {user && (
                  <p className="portfolio-meta">
                    Welcome back, {user.display_name || user.username} • Last Updated: {new Date().toLocaleDateString()}
                  </p>
                )}
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <button
                onClick={toggleTheme}
                className="px-4 py-2 rounded-lg border transition-all duration-200"
                style={{
                  backgroundColor: darkMode ? 'var(--color-surface)' : 'var(--color-surface)',
                  borderColor: 'var(--color-border)',
                  color: 'var(--color-text)'
                }}
              >
                {darkMode ? '☀️ Light Mode' : '🌙 Dark Mode'}
              </button>
              <button
                onClick={logout}
                className="px-4 py-2 rounded-lg transition-colors"
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

        {/* Navigation Tabs - Hide on update-portfolio route */}
        {!location.pathname.includes('update-portfolio') && (
          <nav className="dashboard-nav">
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

        <main className="flex-1 overflow-y-auto dashboard"> 
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8" style={{ padding: 'var(--space-24) 16px' }}>
            {/* Show dynamic title for tab-based content */}
            {!location.pathname.includes('update-portfolio') && (
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
