
import React from 'react';
import { AppBar, Toolbar, Typography, Button } from '@mui/material';
import { useNavigate } from 'react-router-dom';

function Navigation() {
  const navigate = useNavigate();
  const user = JSON.parse(localStorage.getItem('user') || 'null');
  const isLoggedIn = !!user;

  return (
    <AppBar position="static">
      <Toolbar>
        <Typography variant="h6" sx={{ flexGrow: 1 }}>
          Startup Review Platform
        </Typography>
        {!isLoggedIn ? (
          <>
            <Button color="inherit" onClick={() => navigate('/login')}>Login</Button>
            <Button color="inherit" onClick={() => navigate('/register')}>Register</Button>
          </>
        ) : (
          <Button color="inherit" onClick={() => {
            localStorage.removeItem('user');
            window.location.href = '/login';
          }}>Logout</Button>
        )}
      </Toolbar>
    </AppBar>
  );
}

export default Navigation;
