import React, { createContext, useState, useContext, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';
import PortfolioService from '../services/portfolioService'; // Import PortfolioService
import { getApiBaseUrl } from '../utils/apiConfig';

const AuthContext = createContext(null);

const API_BASE_URL = getApiBaseUrl();

// Retry configuration for handling deployment restarts
const MAX_RETRIES = 3;
const RETRY_DELAY = 2000; // 2 seconds

// Helper function to wait
const wait = (ms) => new Promise(resolve => setTimeout(resolve, ms));

// Helper function to retry requests with exponential backoff
const retryRequest = async (fn, retries = MAX_RETRIES, delay = RETRY_DELAY) => {
  try {
    return await fn();
  } catch (error) {
    if (retries > 0 && (error.code === 'ECONNABORTED' || error.code === 'ERR_NETWORK' || !error.response)) {
      console.log(`Request failed, retrying in ${delay}ms... (${retries} retries left)`);
      await wait(delay);
      return retryRequest(fn, retries - 1, delay * 1.5); // Exponential backoff
    }
    throw error;
  }
};

// Create axios instance with interceptors
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000, // Increased to 120 seconds for portfolio analysis with currency conversion
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  }
);

const LoadingSpinner = () => (
  <div className="flex items-center justify-center min-h-screen">
    <Loader2 className="h-12 w-12 text-indigo-600 animate-spin" />
  </div>
);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [portfolioId, setPortfolioId] = useState(null); // CRITICAL FIX: Store portfolio ID
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isOnboarded, setIsOnboarded] = useState(false); // Initialize as false to prevent premature dashboard access
  const navigate = useNavigate();

  const portfolioService = new PortfolioService(api); // Initialize portfolio service

  useEffect(() => {
    const initAuth = async () => {
      const token = localStorage.getItem('access_token');
      if (!token) {
        setLoading(false);
        return;
      }

      try {
        // CRITICAL FIX: Fetch both user data and portfolio info in parallel
        const [userResponse, portfolioResponse] = await Promise.allSettled([
          api.get('/users/me'),
          api.get('/portfolios')
        ]);

        if (userResponse.status === 'fulfilled') {
          const userData = userResponse.value.data;
          setUser(userData);
        }

        if (portfolioResponse.status === 'fulfilled') {
          const portfolioData = portfolioResponse.value.data;
          setPortfolioId(portfolioData.id); // Store portfolio ID
          
          await checkOnboardingStatus(userResponse.value?.data, portfolioData); // Pass portfolioData to avoid extra call
        } else {
          await checkOnboardingStatus(userResponse.value?.data);
        }
      } catch (err) {
        console.error('Token validation failed:', err);
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        setUser(null);
        setPortfolioId(null);
        setIsOnboarded(false); // Not onboarded if token validation fails
      } finally {
        setLoading(false);
      }
    };

    initAuth();
  }, []);

  // Function to check onboarding status
  const checkOnboardingStatus = async (currentUser, existingPortfolio = null) => {
    if (!currentUser) {
      setIsOnboarded(false);
      return;
    }
    
    // Optimization: Use existing portfolio data if provided to avoid redundant API calls
    if (existingPortfolio) {
      const hasPortfolio = !!(existingPortfolio && existingPortfolio.id);
      setIsOnboarded(hasPortfolio);
      if (hasPortfolio) {
        setPortfolioId(existingPortfolio.id);
      } else {
        setPortfolioId(null);
      }
      return;
    }

    try {
      // Use portfolio summary instead of analysis for onboarding check
      // This is simpler and doesn't require heavy computation
      // Wrap in retry logic to handle Railway cold starts
      const portfolio = await retryRequest(() => portfolioService.getPortfolio());
      
      // Check if portfolio exists to determine onboarding status
      const hasPortfolio = !!(portfolio && portfolio.id);
      setIsOnboarded(hasPortfolio);

      if (hasPortfolio) {
        setPortfolioId(portfolio.id); // Store portfolio ID
      } else {
        setPortfolioId(null);
      }
    } catch (err) {
      console.error('AuthContext: Error checking onboarding status:', err);
      // If we can't check, assume not onboarded or handle gracefully
      // For now, if we fail to get portfolio, we assume false to provoke retry or onboarding
      setIsOnboarded(false); 
      setPortfolioId(null);
    }
  };

  const login = async (username, password) => {
    try {
      setError(null);

      // Create form data for OAuth2 login
      const formData = new FormData();
      formData.append('username', username);
      formData.append('password', password);
      formData.append('grant_type', 'password');

      const response = await axios.post(
        `${API_BASE_URL}/auth/login`,
        formData,
        {
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          }
        }
      );

      const { access_token, refresh_token } = response.data;

      // Store tokens
      localStorage.setItem('access_token', access_token);
      localStorage.setItem('refresh_token', refresh_token);

      // PERFORMANCE FIX: Only fetch user and portfolio data during login
      // Portfolio analysis is expensive and should be lazy loaded by dashboard components
      const [userResponse, portfolioResponse] = await Promise.allSettled([
        api.get('/users/me'),
        api.get('/portfolios')
      ]);

      if (userResponse.status === 'fulfilled') {
        const userData = userResponse.value.data;
        setUser(userData);
      }

      if (portfolioResponse.status === 'fulfilled') {
        const portfolioData = portfolioResponse.value.data;
        setPortfolioId(portfolioData.id); // Store portfolio ID
      }

      // Check onboarding status from portfolio existence (not expensive analysis)
      const hasPortfolio = portfolioResponse.status === 'fulfilled' &&
                          portfolioResponse.value?.data?.id;
      setIsOnboarded(hasPortfolio);

      toast.success('Login successful!');

      return {
        success: true,
        isOnboarded: hasPortfolio
      };
    } catch (err) {
      console.error('Login error:', err);
      const errorMsg = err.response?.data?.detail || 'Login failed. Please check your credentials.';
      setError(errorMsg);
      toast.error(errorMsg);
      return { success: false, error: errorMsg };
    }
  };

  const register = async (userData) => {
    try {
      setError(null);
      setLoading(true);
      
      await api.post('/auth/register', userData);
      
      toast.success('Registration successful! Please log in.');
      navigate('/login');
      
      return { success: true };
    } catch (err) {
      console.error('Registration error:', err);
      const errorMsg = err.response?.data?.detail || 'Registration failed. Please try again.';
      setError(errorMsg);
      toast.error(errorMsg);
      return { success: false, error: errorMsg };
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    try {
      await api.post('/auth/logout');
    } catch (err) {
      console.error('Logout error:', err);
    } finally {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      setUser(null);
      setPortfolioId(null); // CRITICAL FIX: Clear portfolio ID on logout
      navigate('/login');
      toast.success('Logged out successfully');
    }
  };

  const changePassword = async (currentPassword, newPassword) => {
    try {
      await api.post('/auth/change-password', {
        current_password: currentPassword,
        new_password: newPassword,
      });
      
      toast.success('Password changed successfully');
      return { success: true };
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Failed to change password';
      toast.error(errorMsg);
      return { success: false, error: errorMsg };
    }
  };

  const value = {
    user,
    portfolioId, // CRITICAL FIX: Expose portfolio ID
    loading,
    error,
    login,
    register,
    logout,
    changePassword,
    isAuthenticated: !!user,
    isOnboarded, // Expose onboarding status
    checkOnboardingStatus, // Expose function to refresh onboarding status
    api, // Expose the configured axios instance
  };

  return (
    <AuthContext.Provider value={value}>
      {loading ? <LoadingSpinner /> : children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export default AuthContext;