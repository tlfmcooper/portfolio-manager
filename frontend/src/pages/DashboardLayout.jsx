
import React, { useState, useEffect, Suspense } from 'react';
import { Outlet } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Loader2, Menu } from 'lucide-react';
import PortfolioService from '../services/portfolioService';
import Sidebar from '../components/Sidebar';

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
  const { api, user, logout } = useAuth();

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

  return (
    <div className="min-h-screen flex"> 
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

        <main className="flex-1 overflow-y-auto"> 
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8" style={{ padding: 'var(--space-24) 16px' }}>
            <Suspense fallback={<LoadingSpinner />}>
              <Outlet />
            </Suspense>
          </div>
        </main>
      </div>
    </div>
  );
};

export default DashboardLayout;
