import React, { lazy, Suspense, useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { CurrencyProvider } from './contexts/CurrencyContext';
import { ThemeProvider } from './contexts/ThemeContext';
import { AgentProvider } from './contexts/AgentContext';
import { DataCacheProvider } from './contexts/DataCacheContext';
import { Toaster } from 'react-hot-toast';
import { Loader2 } from 'lucide-react';
import OfflineIndicator from './components/OfflineIndicator';
import Tooltip from './components/Tooltip';
import LandingPage from './pages/LandingPage';
import { DashboardSkeleton } from './components/ui/Skeleton';

// Lazy load components
const Login = lazy(() => import('./pages/Login'));
const Register = lazy(() => import('./pages/Register'));
const Onboarding = lazy(() => import('./pages/Onboarding'));
const DashboardLayout = lazy(() => import('./pages/DashboardLayout'));
const Overview = lazy(() => import('./pages/Overview'));
const Portfolio = lazy(() => import('./pages/Portfolio'));
const Analytics = lazy(() => import('./pages/Analytics'));
const Settings = lazy(() => import('./pages/Settings'));
const UpdatePortfolio = lazy(() => import('./pages/UpdatePortfolio'));
const LiveMarket = lazy(() => import('./pages/LiveMarket'));
const NotFound = lazy(() => import('./pages/NotFound'));

const AppUpdateBanner = () => {
  const [updateHandler, setUpdateHandler] = useState(null);

  useEffect(() => {
    const handleUpdateAvailable = (event) => {
      setUpdateHandler(() => event.detail?.update || null);
    };

    window.addEventListener('app:updateAvailable', handleUpdateAvailable);
    return () => {
      window.removeEventListener('app:updateAvailable', handleUpdateAvailable);
    };
  }, []);

  if (!updateHandler) return null;

  return (
    <div className="fixed bottom-4 left-4 right-4 sm:left-auto sm:right-4 sm:w-96 z-[60] rounded-lg shadow-lg p-4 flex items-center justify-between gap-3" style={{ backgroundColor: 'var(--color-surface)', color: 'var(--color-text)', border: '1px solid var(--color-border)' }}>
      <span className="text-sm font-medium">A new version is ready.</span>
      <button
        type="button"
        onClick={updateHandler}
        className="px-3 py-1.5 rounded-md text-sm font-semibold"
        style={{ backgroundColor: 'var(--color-primary)', color: 'var(--color-btn-primary-text)' }}
      >
        Update
      </button>
    </div>
  );
};

// Loading component
const LoadingSpinner = () => (
  <div className="min-h-screen flex items-center justify-center" style={{ backgroundColor: 'var(--color-background)' }}>
    <Loader2 className="h-12 w-12 animate-spin" style={{ color: 'var(--color-primary)' }} />
  </div>
);

// Dashboard loading skeleton
const DashboardLoadingFallback = () => (
  <div style={{ backgroundColor: 'var(--color-background)' }}>
    <DashboardSkeleton />
  </div>
);

// Protected layout component
const ProtectedLayout = () => {
  const { user, loading, error, isOnboarded, retryBootstrap, isAuthenticated } = useAuth();
  const location = useLocation();

  if (loading) {
    return <LoadingSpinner />;
  }

  if (!user && isAuthenticated && error) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4" style={{ backgroundColor: 'var(--color-background)' }}>
        <div className="max-w-md w-full rounded-lg p-6 text-center" style={{ backgroundColor: 'var(--color-surface)', border: '1px solid var(--color-border)', color: 'var(--color-text)' }}>
          <h1 className="text-xl font-semibold mb-2">Unable to reach the dashboard</h1>
          <p className="text-sm mb-4" style={{ color: 'var(--color-text-secondary)' }}>{error}</p>
          <button
            type="button"
            onClick={retryBootstrap}
            className="px-4 py-2 rounded-lg text-sm font-semibold"
            style={{ backgroundColor: 'var(--color-primary)', color: 'var(--color-btn-primary-text)' }}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (isOnboarded && location.pathname.startsWith('/onboarding')) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <Suspense fallback={<DashboardLoadingFallback />}>
      <Routes>
        {!isOnboarded ? (
          <>
            <Route path="/onboarding" element={<Onboarding />} />
            <Route path="*" element={<Navigate to="/onboarding" replace />} />
          </>
        ) : (
          <>
            <Route path="/dashboard" element={<DashboardLayout />}>
              <Route index element={<Navigate to="/dashboard/overview" replace />} />
              <Route path="overview" element={<Overview />} />
              <Route path="portfolio" element={<Portfolio />} />
              <Route path="analytics" element={<Analytics />} />
              <Route path="settings" element={<Settings />} />
              <Route path="live-market" element={<LiveMarket />} />
              <Route path="update-portfolio" element={<UpdatePortfolio />} />
            </Route>
            <Route path="/onboarding" element={<Navigate to="/dashboard" replace />} />
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="*" element={<NotFound />} />
          </>
        )}
      </Routes>
    </Suspense>
  );
};

function App() {
  return (
    <Router>
      <ThemeProvider>
        <AuthProvider>
          <CurrencyProvider>
            <DataCacheProvider>
              <AgentProvider>
                <OfflineIndicator />
                <AppUpdateBanner />
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
                  <Suspense fallback={<DashboardLoadingFallback />}>
                    <Routes>
                      {/* Public routes */}
                      <Route path="/" element={<LandingPage />} />
                      <Route path="/login" element={<Login />} />
                      <Route path="/register" element={<Register />} />

                      {/* Protected routes */}
                      <Route path="/*" element={<ProtectedLayout />} />
                    </Routes>
                  </Suspense>
                  <Tooltip />
                </div>
              </AgentProvider>
            </DataCacheProvider>
          </CurrencyProvider>
        </AuthProvider>
      </ThemeProvider>
    </Router>
  );
}

export default App;
