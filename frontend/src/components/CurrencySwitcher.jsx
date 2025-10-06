import React from 'react';
import { DollarSign, RefreshCw } from 'lucide-react';
import { useCurrency } from '../contexts/CurrencyContext';

const CurrencySwitcher = () => {
  const { currency, toggleCurrency, exchangeRate, exchangeRateLoading, lastUpdated } = useCurrency();

  const formatLastUpdated = () => {
    if (!lastUpdated) return '';
    const now = new Date();
    const diff = Math.floor((now - lastUpdated) / 1000); // seconds

    if (diff < 60) return 'just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    return `${Math.floor(diff / 3600)}h ago`;
  };

  const getExchangeRateDisplay = () => {
    if (!exchangeRate) return '';
    const fromCurrency = currency === 'USD' ? 'CAD' : 'USD';
    const toCurrency = currency;
    return `1 ${fromCurrency} = ${exchangeRate.toFixed(4)} ${toCurrency}`;
  };

  return (
    <div className="flex items-center gap-2">
      {/* Currency Toggle Button */}
      <button
        onClick={toggleCurrency}
        className="flex items-center gap-2 px-3 py-2 rounded-lg bg-indigo-100 dark:bg-indigo-900 hover:bg-indigo-200 dark:hover:bg-indigo-800 transition-colors text-indigo-700 dark:text-indigo-300 font-medium"
        title={`Switch to ${currency === 'USD' ? 'CAD' : 'USD'}`}
      >
        <DollarSign className="h-4 w-4" />
        <span className="text-sm font-semibold">{currency}</span>
        <RefreshCw className={`h-3 w-3 ${exchangeRateLoading ? 'animate-spin' : ''}`} />
      </button>

      {/* Exchange Rate Info - Desktop only */}
      {exchangeRate && (
        <div className="hidden md:flex flex-col text-xs text-gray-600 dark:text-gray-400">
          <span className="font-medium">{getExchangeRateDisplay()}</span>
          {lastUpdated && (
            <span className="text-gray-500 dark:text-gray-500">
              Updated {formatLastUpdated()}
            </span>
          )}
        </div>
      )}

      {/* Exchange Rate Tooltip - Mobile */}
      {exchangeRate && (
        <div className="md:hidden" title={`${getExchangeRateDisplay()} • Updated ${formatLastUpdated()}`}>
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {exchangeRate.toFixed(2)}
          </span>
        </div>
      )}
    </div>
  );
};

export default CurrencySwitcher;
