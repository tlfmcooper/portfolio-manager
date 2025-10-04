import { Container, Typography, Paper, Box, Grid } from '@mui/material'

const Dashboard = () => {
  return (
    <Container maxWidth="lg">
      <Typography variant="h4" component="h1" gutterBottom>
        Portfolio Dashboard
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Portfolio Summary
            </Typography>
            <Box>
              <Typography variant="body2" color="text.secondary">
                Total Value: $100,000
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Holdings: 5 assets
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Annual Return: 12.1%
              </Typography>
            </Box>
          </Paper>
        </Grid>

        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Risk Metrics
            </Typography>
            <Box>
              <Typography variant="body2" color="text.secondary">
                Volatility: 18.5%
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Sharpe Ratio: 0.65
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Max Drawdown: -15%
              </Typography>
            </Box>
          </Paper>
        </Grid>

        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Quick Actions
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Use the AI Chat Assistant to analyze your portfolio, run simulations, and explore rebalancing scenarios.
            </Typography>
          </Paper>
        </Grid>
      </Grid>
    </Container>
  )
}

export default Dashboard
