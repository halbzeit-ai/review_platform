import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, CircularProgress, Typography } from '@mui/material';
import { getCurrentUserCompanyInfo } from '../utils/companyUtils';

const StartupDashboardRedirect = () => {
  const navigate = useNavigate();

  useEffect(() => {
    const redirectUser = async () => {
      // Get user info from localStorage
      const user = JSON.parse(localStorage.getItem('user') || 'null');
      
      if (user && user.role === 'startup') {
        // Get company info from backend for consistent routing
        try {
          const companyInfo = await getCurrentUserCompanyInfo();
          navigate(companyInfo.dashboard_path, { replace: true });
        } catch (error) {
          console.error('Error getting company info:', error);
          // Fallback to login if company info fails
          navigate('/login', { replace: true });
        }
      } else {
        // Fallback to login if no user data or wrong role
        navigate('/login', { replace: true });
      }
    };

    redirectUser();
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