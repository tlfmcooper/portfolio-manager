import React, { createContext, useContext, useState, useEffect } from 'react';
import { useAuth } from './AuthContext';

const CurrencyContext = createContext();

export const CurrencyProvider = ({ children }) => {
  // Get default currency from localStorage or use USD
  const [currency, setCurrency] = useState(() => {
    return localStorage.getItem('selectedCurrency') || 'USD';
  });

  const [exchangeRate, setExchangeRate] = useState(null);
  const [exchangeRateLoading, setExchangeRateLoading] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);
  const { api } = useAuth();

  // Fetch current exchange rate when currency changes
  useEffect(() => {
    const fetchExchangeRate = async () => {
      if (!api) return;

      try {
        setExchangeRateLoading(true);
        const fromCurrency = currency === 'USD' ? 'CAD' : 'USD';
        const toCurrency = currency;

        const response = await api.get(`/exchange/rate`, {
          params: {
            from_currency: fromCurrency,
            to_currency: toCurrency
          },
          timeout: 15000 // 15 second timeout for exchange rate
        });

        if (response.data.success) {
          setExchangeRate(response.data.data.rate);
          setLastUpdated(new Date(response.data.data.timestamp));
        }
      } catch (error) {
        console.error('Failed to fetch exchange rate:', error);
        // Set a default exchange rate if fetch fails (approximate CAD/USD rate)
        // This allows the app to continue working even if exchange API is down
        if (currency === 'USD') {
          setExchangeRate(1.36); // Approximate CAD to USD
        } else {
          setExchangeRate(0.74); // Approximate USD to CAD
        }
        setLastUpdated(new Date());
      } finally {
        setExchangeRateLoading(false);
      }
    };

    fetchExchangeRate();

    // Refresh exchange rate every 5 minutes
    const interval = setInterval(fetchExchangeRate, 5 * 60 * 1000);

    return () => clearInterval(interval);
  }, [currency, api]);

  // Save to localStorage whenever currency changes
  useEffect(() => {
    localStorage.setItem('selectedCurrency', currency);
  }, [currency]);

  const toggleCurrency = () => {
    setCurrency(prev => prev === 'USD' ? 'CAD' : 'USD');
  };

  const formatCurrency = (value, options = {}) => {
    const {
      showSymbol = true,
      minimumFractionDigits = 2,
      maximumFractionDigits = 2
    } = options;

    if (value === null || value === undefined || isNaN(value)) {
      return 'N/A';
    }

    const formattedValue = new Intl.NumberFormat('en-US', {
      style: showSymbol ? 'currency' : 'decimal',
      currency: currency,
      minimumFractionDigits,
      maximumFractionDigits,
    }).format(value);

    // For CAD, we want to show C$ instead of CA$
    if (currency === 'CAD' && showSymbol) {
      return formattedValue.replace('CA', 'C');
    }

    return formattedValue;
  };

  const getCurrencySymbol = () => {
    return currency === 'USD' ? '$' : 'C$';
  };

  const value = {
    currency,
    setCurrency,
    toggleCurrency,
    formatCurrency,
    getCurrencySymbol,
    exchangeRate,
    exchangeRateLoading,
    lastUpdated,
  };

  return (
    <CurrencyContext.Provider value={value}>
      {children}
    </CurrencyContext.Provider>
  );
};

export const useCurrency = () => {
  const context = useContext(CurrencyContext);
  if (!context) {
    throw new Error('useCurrency must be used within a CurrencyProvider');
  }
  return context;
};

export default CurrencyContext;
