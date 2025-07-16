import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, CircularProgress, Typography } from '@mui/material';

const DashboardRedirect = () => {
  const navigate = useNavigate();

  useEffect(() => {
    // Get user info from localStorage
    const user = JSON.parse(localStorage.getItem('user'));
    
    if (user) {
      if (user.role === 'startup') {
        // Extract company ID from email and redirect to project dashboard
        const companyId = user.email.split('@')[0];
        navigate(`/project/${companyId}`, { replace: true });
      } else if (user.role === 'gp') {
        // Redirect to GP dashboard
        navigate('/dashboard/gp', { replace: true });
      } else {
        // Unknown role, redirect to login
        navigate('/login', { replace: true });
      }
    } else {
      // No user data, redirect to login
      navigate('/login', { replace: true });
    }
  }, [navigate]);

  return (
    <Box sx={{ 
      display: 'flex', 
      flexDirection: 'column', 
      alignItems: 'center', 
      justifyContent: 'center', 
      minHeight: '50vh',
      gap: 2
    }}>
      <CircularProgress />
      <Typography variant="body1" color="text.secondary">
        Redirecting to your dashboard...
      </Typography>
    </Box>
  );
};

export default DashboardRedirect;