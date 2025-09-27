import React, { lazy, Suspense, useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { Toaster } from 'react-hot-toast';
import { Loader2, TrendingUp, Shield, PieChart, Target, BarChart3, TrendingDown } from 'lucide-react';
import PortfolioService from './services/portfolioService';

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
  <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
    <Loader2 className="h-12 w-12 text-indigo-600 animate-spin" />
  </div>
);

// Dashboard layout component
const DashboardLayout = () => {
  const [activeTab, setActiveTab] = useState('overview');
  const [portfolioData, setPortfolioData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [darkMode, setDarkMode] = useState(false);
  const { api, user, logout } = useAuth(); // <-- FIX: add logout here

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
    document.documentElement.classList.toggle('dark', newDarkMode);
  };

  const renderTabContent = () => {
    if (loading) {
      return (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
        </div>
      );
    }

    if (error) {
      return (
        <div className="bg-red-100 border border-red-400 text-red-700 px-6 py-4 rounded-lg" role="alert">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-400" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">Notice</h3>
              <div className="mt-2 text-sm text-red-700">
                <p>{error}</p>
              </div>
              <div className="mt-4">
                <button 
                  onClick={fetchPortfolioData}
                  className="bg-red-600 hover:bg-red-700 text-white font-bold py-2 px-4 rounded"
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
      <div className={`min-h-screen transition-colors duration-200 ${darkMode ? 'dark bg-gray-900' : 'bg-gray-50'}`}>
        <header className={`sticky top-0 z-10 ${darkMode ? 'bg-gray-800' : 'bg-white'} shadow`}>
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
            <div>
              <h1 className="text-xl font-bold text-gray-900 dark:text-white">Portfolio Dashboard</h1>
              {user && (
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Welcome back, {user.display_name || user.username}
                </p>
              )}
            </div>
            <div className="flex items-center space-x-4">
              <button
                onClick={toggleTheme}
                className={`px-4 py-2 rounded-lg border transition-all duration-200 ${
                  darkMode 
                    ? 'bg-gray-700 border-gray-600 text-gray-200 hover:bg-gray-600' 
                    : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'
                }`}
              >
                {darkMode ? '☀️ Light Mode' : '🌙 Dark Mode'}
              </button>
              <button
                onClick={logout} // <-- FIX: use logout directly
                className="px-4 py-2 rounded-lg bg-red-600 text-white hover:bg-red-700 transition-colors"
              >
                Logout
              </button>
            </div>
          </div>
        </header>

        <nav className={`border-b transition-colors duration-200 ${
          darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
        }`}>
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex space-x-8">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`py-4 px-1 border-b-2 font-medium text-sm ${
                      activeTab === tab.id
                        ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-200'
                    }`}
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

        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
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
        </main>
      </div>
    );
  };

  return renderTabContent();
};

// Protected layout component
const ProtectedLayout = () => {
  const { user, loading } = useAuth();

  if (loading) {
    return <LoadingSpinner />;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
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
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
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
