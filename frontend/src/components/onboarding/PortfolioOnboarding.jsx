import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { PieChart, DollarSign, TrendingUp, Target, DollarSign as DollarSignIcon } from 'lucide-react';

// Sample asset classes for the portfolio
const ASSET_CLASSES = [
  { id: 'stocks', name: 'Stocks', description: 'Individual company stocks and ETFs' },
  { id: 'bonds', name: 'Bonds', description: 'Government and corporate bonds' },
  { id: 'crypto', name: 'Cryptocurrency', description: 'Bitcoin, Ethereum, and other cryptocurrencies' },
  { id: 'real_estate', name: 'Real Estate', description: 'REITs and property investments' },
  { id: 'commodities', name: 'Commodities', description: 'Gold, silver, oil, and other commodities' },
  { id: 'cash', name: 'Cash', description: 'Cash and cash equivalents' },
];

const PortfolioOnboarding = ({ userData }) => {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState({
    portfolioName: `${userData?.username || 'My'}'s Portfolio`,
    initialInvestment: 10000,
    riskTolerance: 'moderate',
    investmentGoal: 'growth',
    timeHorizon: 10,
    assetAllocation: {
      stocks: 60,
      bonds: 30,
      crypto: 5,
      real_estate: 0,
      commodities: 0,
      cash: 5
    },
    recurringInvestment: 0,
    investmentFrequency: 'monthly',
  });
  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Auto-calculate other allocations when one changes
  useEffect(() => {
    const totalAllocated = Object.entries(formData.assetAllocation)
      .filter(([key]) => key !== 'cash')
      .reduce((sum, [_, value]) => sum + value, 0);

    const expectedCash = Math.max(0, 100 - totalAllocated);
    if (formData.assetAllocation.cash !== expectedCash) {
      setFormData(prev => ({
        ...prev,
        assetAllocation: {
          ...prev.assetAllocation,
          cash: expectedCash
        }
      }));
    }
    // Only update if cash is actually different
  }, [formData.assetAllocation]);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };
  const handleAllocationChange = (asset, value) => {
    const numValue = parseInt(value) || 0;
    setFormData(prev => ({
      ...prev,
      assetAllocation: {
        ...prev.assetAllocation,
        [asset]: numValue > 0 ? numValue : 0
      }
    }));
  };

  const validateStep = (currentStep) => {
    const newErrors = {};
    
    if (currentStep === 1) {
      if (!formData.portfolioName.trim()) {
        newErrors.portfolioName = 'Portfolio name is required';
      }
      if (formData.initialInvestment <= 0) {
        newErrors.initialInvestment = 'Initial investment must be greater than 0';
      }
    }
    
    if (currentStep === 2) {
      const totalAllocated = Object.values(formData.assetAllocation).reduce((a, b) => a + b, 0);
      if (totalAllocated !== 100) {
        newErrors.assetAllocation = 'Asset allocation must total 100%';
      }
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const nextStep = () => {
    if (validateStep(step)) {
      setStep(step + 1);
    }
  };

  const prevStep = () => {
    setStep(step - 1);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validateStep(step)) return;
    
    setIsSubmitting(true);
    
    try {
      // Here you would typically send the data to your backend
      console.log('Submitting portfolio data:', formData);
      
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Navigate to dashboard after successful submission
      navigate('/dashboard');
    } catch (error) {
      console.error('Error saving portfolio:', error);
      setErrors({ form: 'Failed to save portfolio. Please try again.' });
    } finally {
      setIsSubmitting(false);
    }
  };

  const renderStep1 = () => (
    <div className="space-y-6">
      <h3 className="text-lg font-medium text-gray-900 dark:text-white">Basic Information</h3>
      
      <div>
        <label htmlFor="portfolioName" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
          Portfolio Name
        </label>
        <input
          type="text"
          id="portfolioName"
          name="portfolioName"
          value={formData.portfolioName}
          onChange={handleChange}
          className={`mt-1 block w-full rounded-md ${errors.portfolioName ? 'border-red-300' : 'border-gray-300'} shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm`}
          placeholder="My Investment Portfolio"
        />
        {errors.portfolioName && <p className="mt-1 text-sm text-red-600">{errors.portfolioName}</p>}
      </div>
      
      <div>
        <label htmlFor="initialInvestment" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
          Initial Investment Amount ($)
        </label>
        <div className="mt-1 relative rounded-md shadow-sm">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <DollarSignIcon className="h-5 w-5 text-gray-400" />
          </div>
          <input
            type="number"
            id="initialInvestment"
            name="initialInvestment"
            min="0"
            step="0.01"
            value={formData.initialInvestment}
            onChange={handleChange}
            className={`pl-10 block w-full rounded-md ${errors.initialInvestment ? 'border-red-300' : 'border-gray-300'} shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm`}
            placeholder="10000"
          />
        </div>
        {errors.initialInvestment && <p className="mt-1 text-sm text-red-600">{errors.initialInvestment}</p>}
      </div>
      
      <div>
        <label htmlFor="riskTolerance" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
          Risk Tolerance
        </label>
        <select
          id="riskTolerance"
          name="riskTolerance"
          value={formData.riskTolerance}
          onChange={handleChange}
          className="mt-1 block w-full rounded-md border-gray-300 py-2 pl-3 pr-10 text-base focus:border-indigo-500 focus:outline-none focus:ring-indigo-500 sm:text-sm"
        >
          <option value="conservative">Conservative</option>
          <option value="moderate">Moderate</option>
          <option value="aggressive">Aggressive</option>
        </select>
      </div>
      
      <div>
        <label htmlFor="investmentGoal" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
          Investment Goal
        </label>
        <select
          id="investmentGoal"
          name="investmentGoal"
          value={formData.investmentGoal}
          onChange={handleChange}
          className="mt-1 block w-full rounded-md border-gray-300 py-2 pl-3 pr-10 text-base focus:border-indigo-500 focus:outline-none focus:ring-indigo-500 sm:text-sm"
        >
          <option value="preservation">Capital Preservation</option>
          <option value="income">Income</option>
          <option value="growth">Growth</option>
          <option value="speculation">Speculation</option>
        </select>
      </div>
      
      <div>
        <label htmlFor="timeHorizon" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
          Investment Time Horizon (years)
        </label>
        <input
          type="range"
          id="timeHorizon"
          name="timeHorizon"
          min="1"
          max="30"
          value={formData.timeHorizon}
          onChange={handleChange}
          className="mt-2 w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
        />
        <div className="flex justify-between text-xs text-gray-500">
          <span>1 year</span>
          <span>{formData.timeHorizon} years</span>
          <span>30+ years</span>
        </div>
      </div>
    </div>
  );

  const renderStep2 = () => (
    <div className="space-y-6">
      <h3 className="text-lg font-medium text-gray-900 dark:text-white">Asset Allocation</h3>
      <p className="text-sm text-gray-500 dark:text-gray-400">
        Allocate percentages to different asset classes. Total must equal 100%.
      </p>
      
      {errors.assetAllocation && (
        <div className="bg-red-50 border-l-4 border-red-500 p-4 mb-4">
          <p className="text-sm text-red-700">{errors.assetAllocation}</p>
        </div>
      )}
      
      <div className="space-y-4">
        {ASSET_CLASSES.map(asset => (
          <div key={asset.id} className="flex items-center">
            <div className="w-1/3">
              <label htmlFor={`allocation-${asset.id}`} className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                {asset.name}
              </label>
              <p className="text-xs text-gray-500 dark:text-gray-400">{asset.description}</p>
            </div>
            <div className="w-1/3 px-4">
              <input
                type="range"
                id={`allocation-${asset.id}`}
                min="0"
                max="100"
                value={formData.assetAllocation[asset.id] || 0}
                onChange={(e) => handleAllocationChange(asset.id, e.target.value)}
                className="w-full"
              />
            </div>
            <div className="w-1/3">
              <div className="relative rounded-md shadow-sm">
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={formData.assetAllocation[asset.id] || 0}
                  onChange={(e) => handleAllocationChange(asset.id, e.target.value)}
                  className="block w-full rounded-md border-gray-300 pl-3 pr-12 focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
                />
                <div className="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none">
                  <span className="text-gray-500 sm:text-sm">%</span>
                </div>
              </div>
            </div>
          </div>
        ))}
        
        <div className="pt-2 border-t border-gray-200">
          <div className="flex justify-between text-sm font-medium">
            <span>Total Allocated:</span>
            <span>
              {Object.values(formData.assetAllocation).reduce((a, b) => a + b, 0)}%
            </span>
          </div>
        </div>
      </div>
    </div>
  );

  const renderStep3 = () => (
    <div className="space-y-6">
      <div className="text-center">
        <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-green-100">
          <TrendingUp className="h-6 w-6 text-green-600" />
        </div>
        <h3 className="mt-3 text-lg font-medium text-gray-900 dark:text-white">You're all set!</h3>
        <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
          Review your portfolio details below. You can always adjust these settings later.
        </p>
      </div>
      
      <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
        <h4 className="font-medium text-gray-900 dark:text-white">Portfolio Summary</h4>
        <dl className="mt-2 space-y-2 text-sm">
          <div className="flex justify-between">
            <dt className="text-gray-500 dark:text-gray-400">Portfolio Name</dt>
            <dd className="font-medium">{formData.portfolioName}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-gray-500 dark:text-gray-400">Initial Investment</dt>
            <dd className="font-medium">${formData.initialInvestment.toLocaleString()}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-gray-500 dark:text-gray-400">Risk Tolerance</dt>
            <dd className="font-medium capitalize">{formData.riskTolerance}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-gray-500 dark:text-gray-400">Investment Goal</dt>
            <dd className="font-medium capitalize">{formData.investmentGoal}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-gray-500 dark:text-gray-400">Time Horizon</dt>
            <dd className="font-medium">{formData.timeHorizon} years</dd>
          </div>
        </dl>
        
        <div className="mt-4">
          <h5 className="text-sm font-medium text-gray-700 dark:text-gray-300">Asset Allocation</h5>
          <div className="mt-2 space-y-2">
            {Object.entries(formData.assetAllocation)
              .filter(([_, value]) => value > 0)
              .map(([key, value]) => {
                const asset = ASSET_CLASSES.find(a => a.id === key) || { name: key };
                return (
                  <div key={key} className="flex items-center justify-between text-sm">
                    <span className="text-gray-600 dark:text-gray-400">{asset.name}</span>
                    <span className="font-medium">{value}%</span>
                  </div>
                );
              })}
          </div>
        </div>
      </div>
      
      <div className="flex items-center">
        <input
          id="terms"
          name="terms"
          type="checkbox"
          required
          className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
        />
        <label htmlFor="terms" className="ml-2 block text-sm text-gray-700 dark:text-gray-300">
          I agree to the <a href="#" className="text-indigo-600 hover:text-indigo-500 dark:text-indigo-400 dark:hover:text-indigo-300">Terms of Service</a> and <a href="#" className="text-indigo-600 hover:text-indigo-500 dark:text-indigo-400 dark:hover:text-indigo-300">Privacy Policy</a>
        </label>
      </div>
    </div>
  );

  const renderStepIndicator = () => (
    <div className="flex justify-between mb-8">
      {[1, 2, 3].map((i) => (
        <div key={i} className="flex flex-col items-center">
          <div
            className={`flex items-center justify-center w-10 h-10 rounded-full ${
              i === step
                ? 'bg-indigo-600 text-white'
                : i < step
                ? 'bg-green-100 text-green-600'
                : 'bg-gray-200 text-gray-600'
            }`}
          >
            {i < step ? <span>✓</span> : i}
          </div>
          <span className="mt-2 text-xs font-medium text-gray-500 dark:text-gray-400">
            {i === 1 ? 'Details' : i === 2 ? 'Allocation' : 'Review'}
          </span>
        </div>
      ))}
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto">
        <div className="text-center mb-8">
          <h2 className="text-3xl font-extrabold text-gray-900 dark:text-white">Set Up Your Portfolio</h2>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
            Let's get started by setting up your investment portfolio.
          </p>
        </div>
        
        <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6 sm:p-8">
          {renderStepIndicator()}
          
          <form onSubmit={handleSubmit} className="mt-6">
            {step === 1 && renderStep1()}
            {step === 2 && renderStep2()}
            {step === 3 && renderStep3()}
            
            <div className="mt-8 flex justify-between">
              <button
                type="button"
                onClick={prevStep}
                disabled={step === 1}
                className={`inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 ${
                  step === 1 ? 'opacity-50 cursor-not-allowed' : ''
                }`}
              >
                Back
              </button>
              
              {step < 3 ? (
                <button
                  type="button"
                  onClick={nextStep}
                  className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                >
                  Next
                </button>
              ) : (
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isSubmitting ? 'Creating Portfolio...' : 'Complete Setup'}
                </button>
              )}
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default PortfolioOnboarding;
