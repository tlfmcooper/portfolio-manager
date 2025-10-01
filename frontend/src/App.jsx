import React, { lazy, Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { Toaster } from 'react-hot-toast';
import { Loader2 } from 'lucide-react';
import Tooltip from './components/Tooltip';
import LandingPage from './pages/LandingPage'; // Import LandingPage

// Lazy load components for better performance
const Login = lazy(() => import('./pages/Login'));
const Register = lazy(() => import('./pages/Register'));
import Onboarding from './pages/Onboarding'; // Directly import Onboarding
const DashboardLayout = lazy(() => import('./pages/DashboardLayout'));
const Overview = lazy(() => import('./pages/Overview'));
const Portfolio = lazy(() => import('./pages/Portfolio'));
const Analytics = lazy(() => import('./pages/Analytics'));
const UpdatePortfolio = lazy(() => import('./pages/UpdatePortfolio'));
const LiveMarket = lazy(() => import('./pages/LiveMarket'));
const NotFound = lazy(() => import('./pages/NotFound'));

// Loading component for Suspense fallback
const LoadingSpinner = () => (
  <div className="min-h-screen flex items-center justify-center" style={{ backgroundColor: 'var(--color-background)' }}>
    <Loader2 className="h-12 w-12 animate-spin" style={{ color: 'var(--color-primary)' }} />
  </div>
);

// Protected layout component
const ProtectedLayout = () => {
  const { user, loading, isOnboarded } = useAuth(); // Get isOnboarded status

  if (loading) {
    return <LoadingSpinner />;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return (
    <Suspense fallback={<LoadingSpinner />}>
      <Routes>
        {/* If user is not onboarded, only allow onboarding route */}
        {!isOnboarded ? (
          <>
            <Route path="/onboarding" element={<Onboarding />} />
            <Route path="*" element={<Navigate to="/onboarding" replace />} />
          </>
        ) : (
          <>
            {/* If user is onboarded, allow dashboard routes */}
            <Route path="/dashboard" element={<DashboardLayout />}>
              <Route index element={<Navigate to="/dashboard/overview" replace />} />
              <Route path="overview" element={<Overview />} />
              <Route path="portfolio" element={<Portfolio />} />
              <Route path="analytics" element={<Analytics />} />
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
              <Route path="/" element={<LandingPage />} />
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />
              
              {/* Protected routes */}
              <Route path="/*" element={<ProtectedLayout />} />
            </Routes>
          </Suspense>
          <Tooltip />
        </div>
      </AuthProvider>
    </Router>
  );
}

export default App;