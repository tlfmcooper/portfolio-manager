import React, { lazy, Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { CurrencyProvider } from './contexts/CurrencyContext';
import { ThemeProvider } from './contexts/ThemeContext';
import { AgentProvider } from './contexts/AgentContext';
import { Toaster } from 'react-hot-toast';
import { Loader2 } from 'lucide-react';
import OfflineIndicator from './components/OfflineIndicator';
import Tooltip from './components/Tooltip';
import LandingPage from './pages/LandingPage';
import { DashboardSkeleton } from './components/ui/Skeleton';

// Lazy load components
const Login = lazy(() => import('./pages/Login'));
const Register = lazy(() => import('./pages/Register'));
import Onboarding from './pages/Onboarding';
const DashboardLayout = lazy(() => import('./pages/DashboardLayout'));
const Overview = lazy(() => import('./pages/Overview'));
const Portfolio = lazy(() => import('./pages/Portfolio'));
const Analytics = lazy(() => import('./pages/Analytics'));
const UpdatePortfolio = lazy(() => import('./pages/UpdatePortfolio'));
const LiveMarket = lazy(() => import('./pages/LiveMarket'));
const NotFound = lazy(() => import('./pages/NotFound'));

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
  const { user, loading, isOnboarded } = useAuth();

  if (loading) {
    return <LoadingSpinner />;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
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
              <Route path="live-market" element={<LiveMarket />} />
              <Route path="update-portfolio" element={<UpdatePortfolio />} />
            </Route>
            <Route path="/onboarding" element={<Onboarding />} />
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
            <AgentProvider>
              <OfflineIndicator />
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
          </CurrencyProvider>
        </AuthProvider>
      </ThemeProvider>
    </Router>
  );
}

export default App;