import React, { lazy, Suspense, useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { Toaster } from 'react-hot-toast';
import { Loader2, TrendingUp, Shield, PieChart, Target, BarChart3, TrendingDown, Menu } from 'lucide-react'; // Added Menu icon
import PortfolioService from './services/portfolioService';
import Sidebar from './components/Sidebar'; // Import Sidebar component

// Lazy load components for better performance
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Login = lazy(() => import('./pages/Login'));
const Register = lazy(() => import('./pages/Register'));
const Onboarding = lazy(() => import('./pages/Onboarding'));
const NotFound = lazy(() => import('./pages/NotFound'));

// Lazy load dashboard sections
const OverviewSection = lazy(() => import('./components/OverviewSection'));
const RiskSection = lazy(() => import('./components/RiskSection'));
const AllocationSection = lazy(() => import('./components/AllocationSection'));
const EfficientFrontierSection = lazy(() => import('./components/EfficientFrontierSection'));
const MonteCarloSection = lazy(() => import('./components/MonteCarloSection'));
const CPPISection = lazy(() => import('./components/CPPISection'));

// Loading component for Suspense fallback
const LoadingSpinner = () => (
  <div className="min-h-screen flex items-center justify-center" style={{ backgroundColor: 'var(--color-background)' }}>
    <Loader2 className="h-12 w-12 animate-spin" style={{ color: 'var(--color-primary)' }} />
  </div>
);

// Dashboard layout component
const DashboardLayout = () => {
  const [activeTab, setActiveTab] = useState('overview');
  const [portfolioData, setPortfolioData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [darkMode, setDarkMode] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false); // State for sidebar visibility
  const { api, user, logout } = useAuth();

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

  const renderTabContent = () => {
    if (loading) {
      return (
        <div className="flex items-center justify-center h-64">
          <div 
            className="animate-spin rounded-full h-12 w-12 border-b-2" 
            style={{ borderColor: 'var(--color-primary)' }}
          ></div>
        </div>
      );
    }

    if (error) {
      return (
        <div 
          className="border px-6 py-4 rounded-lg" 
          role="alert"
          style={{
            backgroundColor: 'rgba(var(--color-error-rgb), 0.1)',
            borderColor: 'var(--color-error)',
            color: 'var(--color-error)'
          }}
        >
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium">Notice</h3>
              <div className="mt-2 text-sm">
                <p>{error}</p>
              </div>
              <div className="mt-4">
                <button 
                  onClick={fetchPortfolioData}
                  className="font-bold py-2 px-4 rounded"
                  style={{
                    backgroundColor: 'var(--color-error)',
                    color: 'var(--color-white)'
                  }}
                >
                  Retry
                </button>
              </div>
            </div>
          </div>
        </div>
      );
    }

    return (
      <div className="min-h-screen flex"> {/* Changed to flex container for sidebar */}
        <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} darkMode={darkMode} toggleDarkMode={toggleTheme} />

        <div className="flex-1 flex flex-col"> {/* Main content area */}
          <header className="dashboard-header">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex justify-between items-center">
              <div className="flex items-center"> {/* Added flex for hamburger menu */}
                <button
                  type="button"
                  className="md:hidden p-1 text-gray-500 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-indigo-500"
                  onClick={() => setSidebarOpen(true)}
                >
                  <span className="sr-only">Open sidebar</span>
                  <Menu className="h-6 w-6" aria-hidden="true" />
                </button>
                <div className="portfolio-info ml-4"> {/* Added ml-4 for spacing */}
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

          <nav className="dashboard-nav">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <div className="nav-tabs">
                {tabs.map((tab) => {
                  const Icon = tab.icon;
                  return (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id)}
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

          <main className="flex-1 overflow-y-auto"> {/* Removed max-w-7xl and padding */}
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8" style={{ padding: 'var(--space-24) 16px' }}>
              <Suspense fallback={<LoadingSpinner />}>
                {portfolioData && (
                  <div className="space-y-8">
                    {activeTab === 'overview' && <OverviewSection />}
                    {activeTab === 'risk' && <RiskSection />}
                    {activeTab === 'allocation' && <AllocationSection />}
                    {activeTab === 'efficient' && <EfficientFrontierSection />}
                    {activeTab === 'simulation' && <MonteCarloSection />}
                    {activeTab === 'strategy' && <CPPISection />}
                  </div>
                )}
              </Suspense>
            </div>
          </main>
        </div>
      </div>
    );
  };

  return renderTabContent();
};

// Protected layout component
const ProtectedLayout = () => {
  const { user, loading, isOnboarded } = useAuth(); // Get isOnboarded status

  if (loading) {
    return <LoadingSpinner />;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  // Redirect to onboarding if user is logged in but not onboarded
  if (user && !loading && !isOnboarded) {
    return <Navigate to="/onboarding" replace />;
  }

  return (
    <Suspense fallback={<LoadingSpinner />}>
      <Routes>
        <Route path="/dashboard" element={<DashboardLayout />} />
        <Route path="/onboarding" element={<Onboarding />} />
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </Suspense>
  );
};

function App() {
  return (
    <Router>
      <AuthProvider>
        <Toaster 
          position="top-right"
          toastOptions={{
            duration: 4000,
            style: {
              background: '#363636',
              color: '#fff',
            },
            success: {
              duration: 3000,
              theme: {
                primary: 'green',
                secondary: 'black',
              },
            },
          }}
        />
        <div className="min-h-screen" style={{ backgroundColor: 'var(--color-background)' }}>
          <Suspense fallback={<LoadingSpinner />}>
            <Routes>
              {/* Public routes */}
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />
              
              {/* Protected routes */}
              <Route path="/*" element={<ProtectedLayout />} />
            </Routes>
          </Suspense>
        </div>
      </AuthProvider>
    </Router>
  );
}

export default App;