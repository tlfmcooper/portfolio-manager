import React from 'react';
import { Typography, Paper, Box } from '@mui/material';

const Dashboard = () => {
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Dashboard
      </Typography>
      <Paper sx={{ p: 3, mt: 2 }}>
        <Typography variant="body1">
          Welcome to your Portfolio Manager dashboard. Use the navigation to
          manage your portfolios or chat with the AI assistant.
        </Typography>
      </Paper>
    </Box>
  );
};

export default Dashboard;
