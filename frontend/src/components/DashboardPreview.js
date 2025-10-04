import React from 'react';
import { Paper, Typography, Box, Divider } from '@mui/material';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';

const DashboardPreview = ({ dashboardUpdate }) => {
  if (!dashboardUpdate) return null;

  const { tool, data } = dashboardUpdate;

  // Render different visualizations based on tool type
  const renderContent = () => {
    if (tool === 'calculate_portfolio_metrics' || tool === 'get_portfolio_summary') {
      return (
        <Box>
          <Typography variant="h6" gutterBottom>
            Portfolio Metrics
          </Typography>
          <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 2 }}>
            {Object.entries(data.metrics || data.summary || {}).map(([key, value]) => (
              <Box key={key}>
                <Typography variant="caption" color="text.secondary">
                  {key.replace(/_/g, ' ').toUpperCase()}
                </Typography>
                <Typography variant="body1">
                  {typeof value === 'number' ? value.toFixed(4) : value}
                </Typography>
              </Box>
            ))}
          </Box>
        </Box>
      );
    }

    if (tool === 'get_risk_metrics') {
      const riskData = data.risk_metrics || {};
      return (
        <Box>
          <Typography variant="h6" gutterBottom>
            Risk Metrics
          </Typography>
          <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 2 }}>
            <Box>
              <Typography variant="caption" color="text.secondary">
                95% VaR
              </Typography>
              <Typography variant="body1">{riskData.var_95?.toFixed(4)}</Typography>
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary">
                99% VaR
              </Typography>
              <Typography variant="body1">{riskData.var_99?.toFixed(4)}</Typography>
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary">
                Volatility
              </Typography>
              <Typography variant="body1">{riskData.volatility?.toFixed(4)}</Typography>
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary">
                Max Drawdown
              </Typography>
              <Typography variant="body1">{riskData.max_drawdown?.toFixed(4)}</Typography>
            </Box>
          </Box>
        </Box>
      );
    }

    if (tool === 'simulate_rebalancing') {
      const { current, proposed, differences } = data;
      const comparisonData = Object.keys(current || {}).map(key => ({
        metric: key.replace(/_/g, ' '),
        current: current[key],
        proposed: proposed[key],
      }));

      return (
        <Box>
          <Typography variant="h6" gutterBottom>
            Rebalancing Simulation
          </Typography>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={comparisonData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="metric" angle={-45} textAnchor="end" height={100} />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="current" fill="#8884d8" name="Current" />
              <Bar dataKey="proposed" fill="#82ca9d" name="Proposed" />
            </BarChart>
          </ResponsiveContainer>
        </Box>
      );
    }

    if (tool === 'run_monte_carlo') {
      return (
        <Box>
          <Typography variant="h6" gutterBottom>
            Monte Carlo Simulation Results
          </Typography>
          <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 2 }}>
            <Box>
              <Typography variant="caption" color="text.secondary">
                Mean Return
              </Typography>
              <Typography variant="body1">{(data.mean_return * 100).toFixed(2)}%</Typography>
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary">
                Median Return
              </Typography>
              <Typography variant="body1">{(data.median_return * 100).toFixed(2)}%</Typography>
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary">
                5th Percentile
              </Typography>
              <Typography variant="body1">{(data.percentile_5 * 100).toFixed(2)}%</Typography>
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary">
                95th Percentile
              </Typography>
              <Typography variant="body1">{(data.percentile_95 * 100).toFixed(2)}%</Typography>
            </Box>
          </Box>
        </Box>
      );
    }

    // Default: Show raw JSON
    return (
      <Box>
        <Typography variant="h6" gutterBottom>
          {tool}
        </Typography>
        <Typography
          variant="body2"
          component="pre"
          sx={{
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
            bgcolor: 'background.default',
            p: 2,
            borderRadius: 1,
          }}
        >
          {JSON.stringify(data, null, 2)}
        </Typography>
      </Box>
    );
  };

  return (
    <Paper sx={{ p: 2, mb: 2, bgcolor: 'action.hover' }}>
      {renderContent()}
    </Paper>
  );
};

export default DashboardPreview;
