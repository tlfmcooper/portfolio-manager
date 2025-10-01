import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import PortfolioOnboarding from '../components/onboarding/PortfolioOnboarding';
import { Loader2 } from 'lucide-react';
import PortfolioService from '../services/portfolioService';
import axios from 'axios';

const Onboarding = () => {
  const { user, loading } = useAuth();
  const navigate = useNavigate();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [checkingOnboarded, setCheckingOnboarded] = useState(true);
  const [shouldShowForm, setShouldShowForm] = useState(false);

  useEffect(() => {
    if (!loading && !user) {
      navigate('/login');
      return;
    }
    
    const checkOnboarded = async () => {
      if (!loading && user) {
        try {
          const api = axios.create({
            baseURL: import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v1',
            timeout: 10000,
            headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` }
          });
          const portfolioService = new PortfolioService(api);
          const analysis = await portfolioService.getPortfolioAnalysis();
          const hasPortfolioData = analysis && Object.keys(analysis).length > 0;
          if (hasPortfolioData) {
            navigate('/dashboard');
          } else {
            setShouldShowForm(true);
          }
        } catch (err) {
          console.error('Error checking onboarding status:', err);
          setShouldShowForm(true); // Show form if we can't determine status
        } finally {
          setCheckingOnboarded(false);
        }
      }
    };
    checkOnboarded();
  }, [user, loading, navigate]);

  const handleOnboardingComplete = async (portfolioData) => {
    setIsSubmitting(true);
    setError('');
    
    try {
      // Here you would typically send the portfolio data to your backend
      console.log('Portfolio data to save:', portfolioData);
      
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Navigate to dashboard after successful submission
      navigate('/dashboard');
    } catch (err) {
      console.error('Error saving portfolio:', err);
      setError('Failed to save portfolio. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading || checkingOnboarded) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <Loader2 className="h-12 w-12 text-indigo-600 animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {error && (
        <div className="bg-red-50 border-l-4 border-red-500 p-4 mb-6">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-500" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          </div>
        </div>
      )}
      {shouldShowForm && <PortfolioOnboarding />}
      {!shouldShowForm && !checkingOnboarded && (
        <div className="max-w-2xl mx-auto text-center py-12">
          <p className="text-gray-600 dark:text-gray-400">Loading onboarding...</p>
        </div>
      )}
    </div>
  );
};

export default Onboarding;
