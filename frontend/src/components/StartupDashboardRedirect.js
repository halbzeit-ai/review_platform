import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, CircularProgress, Typography } from '@mui/material';

const StartupDashboardRedirect = () => {
  const navigate = useNavigate();

  useEffect(() => {
    // Get user info from localStorage
    const user = JSON.parse(localStorage.getItem('user'));
    
    if (user && user.role === 'startup') {
      // Generate company ID using same logic as backend
      const getCompanyId = () => {
        if (user?.companyName) {
          // Convert company name to a URL-safe slug (same logic as backend)
          return user.companyName.toLowerCase().replace(' ', '-').replace(/[^a-z0-9-]/g, '');
        }
        // Fallback to email prefix if company name is not available
        return user?.email?.split('@')[0] || 'unknown';
      };
      
      const companyId = getCompanyId();
      
      // Redirect to project dashboard
      navigate(`/project/${companyId}`, { replace: true });
    } else {
      // Fallback to login if no user data
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
        Redirecting to your project dashboard...
      </Typography>
    </Box>
  );
};

export default StartupDashboardRedirect;