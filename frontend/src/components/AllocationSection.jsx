import React, { useState, useEffect } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';
import { useAuth } from '../contexts/AuthContext';
import { TrendingUp, DollarSign, Percent, PieChart as PieChartIcon } from 'lucide-react';

const AllocationSection = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { api, portfolioId } = useAuth(); // CRITICAL FIX: Get portfolioId from context

  useEffect(() => {
    const fetchData = async () => {
      if (!portfolioId) return; // Wait for portfolioId to load

      try {
        const response = await api.get(`/analysis/portfolios/${portfolioId}/sector-allocation`); // CRITICAL FIX: Use dynamic portfolioId
        setData(response.data);
      } catch (err) {
        setError('Failed to fetch allocation data');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [api, portfolioId]); // CRITICAL FIX: Add portfolioId to dependencies
  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2" style={{ borderColor: 'var(--color-primary)' }}></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg p-6" style={{ backgroundColor: 'var(--color-surface)', color: 'var(--color-text)' }}>
        <p style={{ color: 'var(--color-error)' }}>{error}</p>
      </div>
    );
  }

  if (!data) return null;

  const assetAllocation = data || {};

  const formatPercentage = (value) => {
    if (typeof value !== 'number') return 'N/A';
    return `${value.toFixed(1)}%`;
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  // Prepare data for pie chart
  const pieData = Object.entries(assetAllocation).map(([sector, allocation]) => ({
    name: sector,
    value: allocation.percentage,
    amount: allocation.value
  }));

  // Modern, professional color palette
  const COLORS = [
    '#3B82F6', // Blue
    '#10B981', // Green  
    '#F59E0B', // Amber
    '#EF4444', // Red
    '#8B5CF6', // Purple
    '#06B6D4', // Cyan
    '#F97316', // Orange
    '#84CC16', // Lime
    '#EC4899', // Pink
    '#14B8A6', // Teal
  ];

  // FIXED: Custom tooltip that properly shows PERCENTAGE (not dollar amount)
  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div 
          className="rounded-lg p-3 border shadow-lg" 
          style={{ 
            backgroundColor: 'var(--color-surface)', 
            borderColor: 'var(--color-border)',
            color: 'var(--color-text)'
          }}
        >
          <p className="font-semibold mb-1" style={{ color: 'var(--color-text)' }}>{data.name}</p>
          <p className="text-sm font-medium" style={{ color: 'var(--color-primary)' }}>
            {formatPercentage(data.value)}
          </p>
          <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
            {formatCurrency(data.amount)}
          </p>
        </div>
      );
    }
    return null;
  };

  // FIXED: Custom Legend with proper wrapping to prevent text cutoff
  const renderCustomLegend = (props) => {
    const { payload } = props;
    return (
      <div className="flex flex-wrap justify-center gap-x-6 gap-y-3 mt-6 px-4">
        {payload.map((entry, index) => (
          <div key={`legend-${index}`} className="flex items-center gap-2 min-w-0">
            <div 
              className="w-3 h-3 rounded-full flex-shrink-0"
              style={{ backgroundColor: entry.color }}
            />
            <span className="text-sm whitespace-nowrap" style={{ color: 'var(--color-text)' }}>
              {entry.value}
            </span>
            <span className="text-sm font-medium" style={{ color: 'var(--color-text-secondary)' }}>
              {formatPercentage(entry.payload.value)}
            </span>
          </div>
        ))}
      </div>
    );
  };

  const totalSectors = Object.keys(assetAllocation).length;
  const totalValue = Object.values(assetAllocation).reduce((acc, a) => acc + a.value, 0);
  const largestAllocation = Math.max(...Object.values(assetAllocation).map(a => a.percentage));
  const largestSector = Object.entries(assetAllocation).find(([_, a]) => a.percentage === largestAllocation)?.[0] || 'N/A';

  return (
    <div className="space-y-6">
      {/* Stats Cards - Polished Design */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Total Portfolio Value */}
        <div 
          className="rounded-xl p-5 border transition-all hover:shadow-lg" 
          style={{ 
            backgroundColor: 'var(--color-surface)', 
            borderColor: 'var(--color-border)'
          }}
        >
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm font-medium" style={{ color: 'var(--color-text-secondary)' }}>
              Total Value
            </p>
            <div className="p-2 rounded-lg" style={{ backgroundColor: 'var(--color-primary-light)' }}>
              <DollarSign className="h-4 w-4" style={{ color: 'var(--color-primary)' }} />
            </div>
          </div>
          <p className="text-2xl font-bold" style={{ color: 'var(--color-text)' }}>
            {formatCurrency(totalValue)}
          </p>
        </div>

        {/* Total Sectors */}
        <div 
          className="rounded-xl p-5 border transition-all hover:shadow-lg" 
          style={{ 
            backgroundColor: 'var(--color-surface)', 
            borderColor: 'var(--color-border)'
          }}
        >
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm font-medium" style={{ color: 'var(--color-text-secondary)' }}>
              Total Sectors
            </p>
            <div className="p-2 rounded-lg" style={{ backgroundColor: 'var(--color-primary-light)' }}>
              <PieChartIcon className="h-4 w-4" style={{ color: 'var(--color-primary)' }} />
            </div>
          </div>
          <p className="text-2xl font-bold" style={{ color: 'var(--color-text)' }}>
            {totalSectors}
          </p>
        </div>

        {/* Largest Allocation */}
        <div 
          className="rounded-xl p-5 border transition-all hover:shadow-lg" 
          style={{ 
            backgroundColor: 'var(--color-surface)', 
            borderColor: 'var(--color-border)'
          }}
        >
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm font-medium" style={{ color: 'var(--color-text-secondary)' }}>
              Largest Sector
            </p>
            <div className="p-2 rounded-lg" style={{ backgroundColor: 'var(--color-primary-light)' }}>
              <TrendingUp className="h-4 w-4" style={{ color: 'var(--color-primary)' }} />
            </div>
          </div>
          <p className="text-lg font-bold mb-1" style={{ color: 'var(--color-text)' }}>
            {largestSector}
          </p>
          <p className="text-sm font-medium" style={{ color: 'var(--color-primary)' }}>
            {formatPercentage(largestAllocation)}
          </p>
        </div>
      </div>

      {/* Pie Chart - Improved Design */}
      <div 
        className="rounded-xl p-6 border" 
        style={{ 
          backgroundColor: 'var(--color-surface)', 
          borderColor: 'var(--color-border)'
        }}
      >
        <div className="flex items-center gap-2 mb-6">
          <PieChartIcon className="h-5 w-5" style={{ color: 'var(--color-primary)' }} />
          <h3 className="text-lg font-semibold" style={{ color: 'var(--color-text)' }}>
            Sector Allocation
          </h3>
        </div>
        
        <div style={{ height: '400px' }}>
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                labelLine={false}
                outerRadius={120}
                innerRadius={60}
                fill="#8884d8"
                dataKey="value"
                animationDuration={800}
              >
                {pieData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
              <Legend content={renderCustomLegend} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Sector Breakdown Table - Modern Design */}
      <div 
        className="rounded-xl border overflow-hidden" 
        style={{ 
          backgroundColor: 'var(--color-surface)', 
          borderColor: 'var(--color-border)'
        }}
      >
        <div className="p-6 border-b" style={{ borderColor: 'var(--color-border)' }}>
          <div className="flex items-center gap-2">
            <Percent className="h-5 w-5" style={{ color: 'var(--color-primary)' }} />
            <h3 className="text-lg font-semibold" style={{ color: 'var(--color-text)' }}>
              Detailed Breakdown
            </h3>
          </div>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr style={{ backgroundColor: 'var(--color-background)' }}>
                <th className="px-6 py-4 text-left text-sm font-semibold" style={{ color: 'var(--color-text)' }}>
                  Sector
                </th>
                <th className="px-6 py-4 text-right text-sm font-semibold" style={{ color: 'var(--color-text)' }}>
                  Allocation
                </th>
                <th className="px-6 py-4 text-right text-sm font-semibold" style={{ color: 'var(--color-text)' }}>
                  Value
                </th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(assetAllocation)
                .sort((a, b) => b[1].percentage - a[1].percentage)
                .map(([sector, allocation], index) => (
                <tr 
                  key={sector}
                  className="border-t hover:bg-opacity-50 transition-colors"
                  style={{ 
                    borderColor: 'var(--color-border)',
                    backgroundColor: index % 2 === 0 ? 'transparent' : 'var(--color-background)'
                  }}
                >
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div 
                        className="w-3 h-3 rounded-full flex-shrink-0"
                        style={{ backgroundColor: COLORS[index % COLORS.length] }}
                      />
                      <span className="font-medium" style={{ color: 'var(--color-text)' }}>
                        {sector}
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <span className="font-semibold" style={{ color: 'var(--color-primary)' }}>
                      {formatPercentage(allocation.percentage)}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <span className="font-medium" style={{ color: 'var(--color-text)' }}>
                      {formatCurrency(allocation.value)}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default AllocationSection;
