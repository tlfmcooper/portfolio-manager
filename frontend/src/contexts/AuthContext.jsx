import React, { createContext, useState, useContext, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';
import PortfolioService from '../services/portfolioService'; // Import PortfolioService

const AuthContext = createContext(null);

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v1';

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
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken
          });
          
          const { access_token, refresh_token: newRefreshToken } = response.data;
          localStorage.setItem('access_token', access_token);
          localStorage.setItem('refresh_token', newRefreshToken);
          
          original.headers.Authorization = `Bearer ${access_token}`;
          return api(original);
        } catch (refreshError) {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/login';
        }
      }
    }
    
    return Promise.reject(error);
  }
);

// Loading component for authentication
const LoadingSpinner = () => (
  <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
    <Loader2 className="h-12 w-12 text-indigo-600 animate-spin" />
  </div>
);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [portfolioId, setPortfolioId] = useState(null); // CRITICAL FIX: Store portfolio ID
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isOnboarded, setIsOnboarded] = useState(true); // New state for onboarding status
  const navigate = useNavigate();

  const portfolioService = new PortfolioService(api); // Initialize portfolio service

  // Function to check onboarding status
  const checkOnboardingStatus = async (currentUser) => {
    if (!currentUser) {
      setIsOnboarded(false);
      return;
    }
    try {
      // Use portfolio summary instead of analysis for onboarding check
      // This is simpler and doesn't require heavy computation
      // Wrap in retry logic to handle Railway cold starts
      const portfolio = await retryRequest(() => portfolioService.getPortfolio());
      // Check if portfolio exists to determine onboarding status
      const hasPortfolio = portfolio && portfolio.id;
      setIsOnboarded(hasPortfolio);

      if (hasPortfolio) {
        setPortfolioId(portfolio.id); // Store portfolio ID
      }
    } catch (err) {
      console.error('AuthContext: Error checking onboarding status:', err);
      console.error('AuthContext: Error details:', err.response?.data || err.message);
      // If portfolio endpoint fails, user likely needs to onboard
      setIsOnboarded(false);
    }
  };

  // Check if user is logged in on initial load
  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (token) {
      validateToken();
    } else {
      setLoading(false);
      setIsOnboarded(false); // No token, so not onboarded
    }
  }, []);

  const validateToken = async () => {
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
      }

      setError(null);
      await checkOnboardingStatus(userResponse.value?.data); // Check onboarding status after setting user
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

      // CRITICAL FIX: Fetch user data, portfolio info, and onboarding status in parallel
      const [userResponse, portfolioResponse, analysisResponse] = await Promise.allSettled([
        api.get('/users/me'),
        api.get('/portfolios'),
        portfolioService.getPortfolioAnalysis()
      ]);

      if (userResponse.status === 'fulfilled') {
        const userData = userResponse.value.data;
        setUser(userData);
      }

      if (portfolioResponse.status === 'fulfilled') {
        const portfolioData = portfolioResponse.value.data;
        setPortfolioId(portfolioData.id); // Store portfolio ID
      }

      // Check onboarding status from analysis response
      const hasPortfolioData = analysisResponse.status === 'fulfilled' &&
                               analysisResponse.value &&
                               Object.keys(analysisResponse.value).length > 0;
      setIsOnboarded(hasPortfolioData);

      toast.success('Login successful!');

      return {
        success: true,
        isOnboarded: hasPortfolioData
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