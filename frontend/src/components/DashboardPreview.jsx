import { Paper, Typography, Box } from '@mui/material'
import {
  LineChart,
  Line,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'

const DashboardPreview = ({ update }) => {
  if (!update || !update.data) return null

  const renderChart = () => {
    switch (update.type) {
      case 'run_efficient_frontier':
        const frontierData = update.data.frontier.returns.map((ret, idx) => ({
          return: ret * 100,
          volatility: update.data.frontier.volatilities[idx] * 100,
        }))

        return (
          <ResponsiveContainer width="100%" height={300}>
            <ScatterChart>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="volatility" name="Volatility (%)" />
              <YAxis dataKey="return" name="Return (%)" />
              <Tooltip />
              <Legend />
              <Scatter name="Efficient Frontier" data={frontierData} fill="#8884d8" />
            </ScatterChart>
          </ResponsiveContainer>
        )

      case 'run_monte_carlo':
        const percentiles = update.data.percentiles
        const percentileData = Object.entries(percentiles).map(([key, value]) => ({
          percentile: key,
          value: value,
        }))

        return (
          <Box>
            <Typography variant="body2" gutterBottom>
              Monte Carlo Simulation Results ({update.data.scenarios} scenarios)
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={percentileData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="percentile" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="value" stroke="#82ca9d" />
              </LineChart>
            </ResponsiveContainer>
          </Box>
        )

      case 'simulate_rebalancing':
        return (
          <Box>
            <Typography variant="body2" gutterBottom>
              Rebalancing Analysis
            </Typography>
            <Box sx={{ display: 'flex', justifyContent: 'space-around', mt: 2 }}>
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Current Return
                </Typography>
                <Typography variant="h6">
                  {(update.data.current.return * 100).toFixed(2)}%
                </Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Proposed Return
                </Typography>
                <Typography variant="h6" color="primary">
                  {(update.data.proposed.return * 100).toFixed(2)}%
                </Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Sharpe Ratio Change
                </Typography>
                <Typography
                  variant="h6"
                  color={update.data.changes.sharpe_change > 0 ? 'success.main' : 'error.main'}
                >
                  {update.data.changes.sharpe_change > 0 ? '+' : ''}
                  {update.data.changes.sharpe_change.toFixed(3)}
                </Typography>
              </Box>
            </Box>
          </Box>
        )

      default:
        return (
          <Typography variant="body2">
            Dashboard update: {update.type}
          </Typography>
        )
    }
  }

  return (
    <Paper
      elevation={2}
      sx={{
        p: 2,
        my: 2,
        backgroundColor: 'background.default',
        border: '1px solid',
        borderColor: 'primary.light',
      }}
    >
      <Typography variant="subtitle2" color="primary" gutterBottom>
        📊 Dashboard Update
      </Typography>
      {renderChart()}
    </Paper>
  )
}

export default DashboardPreview
