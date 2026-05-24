import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import toast from 'react-hot-toast';
import { getApiBaseUrl } from '../utils/apiConfig';

const AuthContext = createContext(null);

const API_BASE_URL = getApiBaseUrl();

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
    if (error.response?.status === 401 || error.response?.status === 403) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
    }
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
    if (error.response?.status === 401 && originalRequest && !originalRequest._retry) {
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

        if (refreshError.response?.status === 401 || refreshError.response?.status === 403) {
          window.dispatchEvent(new CustomEvent('auth:sessionExpired', {
            detail: { message: 'Session expired. Please log in again.' }
          }));
        }
        
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [portfolioId, setPortfolioId] = useState(null); // CRITICAL FIX: Store portfolio ID
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isOnboarded, setIsOnboarded] = useState(false); // Initialize as false to prevent premature dashboard access
  const [hasAuthToken, setHasAuthToken] = useState(() => Boolean(localStorage.getItem('access_token')));
  const navigate = useNavigate();

  const markOnboarded = useCallback((maybePortfolio) => {
    const id = maybePortfolio?.id;
    if (id) {
      setPortfolioId(id);
    }
    setIsOnboarded((prev) => prev || !!id);
  }, []);

  const clearAuthState = useCallback(() => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setHasAuthToken(false);
    setUser(null);
    setPortfolioId(null);
    setIsOnboarded(false);
  }, []);

  const applyBootstrapPayload = useCallback((payload) => {
    setUser(payload.user);
    setPortfolioId(payload.portfolio_id || null);
    setIsOnboarded(Boolean(payload.is_onboarded));
    setHasAuthToken(true);
    setError(null);
  }, []);

  const initializeAuth = useCallback(async ({ showToast = false } = {}) => {
    const token = localStorage.getItem('access_token');
    setHasAuthToken(Boolean(token));

    if (!token) {
      setUser(null);
      setPortfolioId(null);
      setIsOnboarded(false);
      setError(null);
      setLoading(false);
      return;
    }

    setLoading(true);

    try {
      const response = await api.get('/auth/bootstrap', { timeout: 15000 });
      applyBootstrapPayload(response.data);
      if (showToast) {
        toast.success('Dashboard connection restored');
      }
    } catch (err) {
      console.error('Auth bootstrap failed:', err);

      if (err.response?.status === 401) {
        clearAuthState();
        setError(null);
        return;
      }

      setUser(null);
      setPortfolioId(null);
      setIsOnboarded(false);
      setError('We could not reach the server. Please check your connection and try again.');
    } finally {
      setLoading(false);
    }
  }, [applyBootstrapPayload, clearAuthState]);

  // Handle session expiration from interceptor
  useEffect(() => {
    const handleSessionExpired = (event) => {
      console.log('Session expired, redirecting to login...');
      clearAuthState();
      toast.error(event.detail?.message || 'Session expired. Please log in again.');
      navigate('/login');
    };

    window.addEventListener('auth:sessionExpired', handleSessionExpired);
    return () => {
      window.removeEventListener('auth:sessionExpired', handleSessionExpired);
    };
  }, [clearAuthState, navigate]);

  useEffect(() => {
    initializeAuth();
  }, [initializeAuth]);

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
      const { default: PortfolioService } = await import('../services/portfolioService');
      const portfolioService = new PortfolioService(api);
      const portfolio = await portfolioService.getPortfolio();
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

      localStorage.setItem('access_token', access_token);
      localStorage.setItem('refresh_token', refresh_token);
      setHasAuthToken(true);

      const bootstrapResponse = await api.get('/auth/bootstrap', { timeout: 15000 });
      applyBootstrapPayload(bootstrapResponse.data);

      toast.success('Login successful!');

      return {
        success: true,
        isOnboarded: Boolean(bootstrapResponse.data.is_onboarded)
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
      clearAuthState();
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
    isAuthenticated: hasAuthToken,
    isOnboarded, // Expose onboarding status
    checkOnboardingStatus, // Expose function to refresh onboarding status
    retryBootstrap: () => initializeAuth({ showToast: true }),
    api, // Expose the configured axios instance
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
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
