import React from 'react';
import { Typography, Paper, Box } from '@mui/material';

const Portfolios = () => {
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Portfolios
      </Typography>
      <Paper sx={{ p: 3, mt: 2 }}>
        <Typography variant="body1">
          Portfolio management interface will be implemented here.
        </Typography>
      </Paper>
    </Box>
  );
};

export default Portfolios;
