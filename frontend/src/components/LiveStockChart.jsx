import React from 'react';
import { Area, AreaChart, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const LiveStockChart = ({ 
  selectedStock, 
  chartData, 
  stockInfo, 
  wsConnected, 
  formatCurrency, 
  formatPercentage, 
  getColorClass 
}) => {
  if (!selectedStock || !chartData || chartData.length === 0) return null;

  const currentPrice = stockInfo?.current_price || chartData[chartData.length - 1].price;
  const dayChangePercent = stockInfo?.change_percent || 0;

  return (
    <div>
      <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-4 gap-2">
        <div>
          <h4 className="text-lg font-semibold" style={{ color: 'var(--color-text)' }}>
            {stockInfo?.asset?.name || selectedStock}
          </h4>
          <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
            {selectedStock}
          </p>
        </div>
        <div className="text-left sm:text-right">
          <p className="text-2xl font-bold" style={{ color: 'var(--color-text)' }}>
            {formatCurrency(currentPrice)}
          </p>
          <p className={`text-sm font-medium ${getColorClass(dayChangePercent)}`}>
            {formatPercentage(dayChangePercent)}
          </p>
        </div>
      </div>

      <div className="h-[250px] sm:h-[300px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData}>
            <defs>
              <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="var(--color-primary)" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="var(--color-primary)" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
            <XAxis 
              dataKey="time" 
              stroke="var(--color-text-secondary)"
              style={{ fontSize: '10px' }}
              interval="preserveStartEnd"
              tick={{ fontSize: 10 }}
            />
            <YAxis 
              stroke="var(--color-text-secondary)"
              style={{ fontSize: '10px' }}
              domain={['auto', 'auto']}
              tickFormatter={(value) => `$${value.toFixed(2)}`}
              tick={{ fontSize: 10 }}
              width={50}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'var(--color-surface)',
                border: '1px solid var(--color-border)',
                borderRadius: '8px',
                color: 'var(--color-text)'
              }}
              formatter={(value) => [formatCurrency(value), 'Price']}
            />
            <Area 
              type="monotone" 
              dataKey="price" 
              stroke="var(--color-primary)" 
              strokeWidth={2}
              fill="url(#colorPrice)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
      
      <p className="text-xs text-center mt-2" style={{ color: 'var(--color-text-secondary)' }}>
        {wsConnected ? 'Chart shows historical + live WebSocket updates' : 'Chart shows real-time price updates'}
      </p>
    </div>
  );
};

export default LiveStockChart;
