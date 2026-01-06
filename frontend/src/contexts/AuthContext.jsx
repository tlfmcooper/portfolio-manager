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

// Track if we're currently refreshing the token
let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

// Function to attempt token refresh
const refreshAccessToken = async () => {
  const refreshToken = localStorage.getItem('refresh_token');
  if (!refreshToken) {
    throw new Error('No refresh token available');
  }

  try {
    const response = await axios.post(
      `${API_BASE_URL}/auth/refresh`,
      { refresh_token: refreshToken },
      { timeout: 30000 }
    );
    
    const { access_token, refresh_token: newRefreshToken } = response.data;
    localStorage.setItem('access_token', access_token);
    if (newRefreshToken) {
      localStorage.setItem('refresh_token', newRefreshToken);
    }
    
    return access_token;
  } catch (error) {
    // Refresh failed - clear tokens
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    throw error;
  }
};

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

// Response interceptor to handle 401 errors and token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // If error is 401 and we haven't already tried to refresh
    if (error.response?.status === 401 && !originalRequest._retry) {
      // Skip token refresh for auth endpoints
      if (originalRequest.url?.includes('/auth/login') || 
          originalRequest.url?.includes('/auth/register') ||
          originalRequest.url?.includes('/auth/refresh')) {
        return Promise.reject(error);
      }

      if (isRefreshing) {
        // Queue this request to retry after token refresh
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            return api(originalRequest);
          })
          .catch((err) => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const newToken = await refreshAccessToken();
        processQueue(null, newToken);
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        return api(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);
        
        // Token refresh failed - trigger logout by dispatching event
        // Components will listen for this to redirect to login
        window.dispatchEvent(new CustomEvent('auth:sessionExpired', { 
          detail: { message: 'Session expired. Please log in again.' }
        }));
        
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
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

  const markOnboarded = (maybePortfolio) => {
    const id = maybePortfolio?.id;
    if (id) {
      setPortfolioId(id);
    }
    setIsOnboarded((prev) => prev || !!id);
  };

  // Handle session expiration from interceptor
  useEffect(() => {
    const handleSessionExpired = (event) => {
      console.log('Session expired, redirecting to login...');
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      setUser(null);
      setPortfolioId(null);
      setIsOnboarded(false);
      toast.error(event.detail?.message || 'Session expired. Please log in again.');
      navigate('/login');
    };

    window.addEventListener('auth:sessionExpired', handleSessionExpired);
    return () => {
      window.removeEventListener('auth:sessionExpired', handleSessionExpired);
    };
  }, [navigate]);

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
          markOnboarded(portfolioData);
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
      markOnboarded(existingPortfolio);
      return;
    }

    try {
      // Use portfolio summary instead of analysis for onboarding check
      // This is simpler and doesn't require heavy computation
      // Wrap in retry logic to handle Railway cold starts
      const portfolio = await retryRequest(() => portfolioService.getPortfolio());

      markOnboarded(portfolio);
    } catch (err) {
      console.error('AuthContext: Error checking onboarding status:', err);
      // Preserve current onboarding state on transient errors
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
      if (portfolioResponse.status === 'fulfilled') {
        markOnboarded(portfolioResponse.value?.data);
      }

      toast.success('Login successful!');

      const hasPortfolio = portfolioResponse.status === 'fulfilled' && Boolean(portfolioResponse.value?.data?.id);

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
      // Dispatch event to clear data cache
      window.dispatchEvent(new CustomEvent('auth:logout'));
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