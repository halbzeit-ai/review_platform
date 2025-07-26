
import React from 'react';
import { AppBar, Toolbar, Typography, Button } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import LanguageSwitcher from './LanguageSwitcher';

function Navigation() {
  const navigate = useNavigate();
  const { t } = useTranslation('common');
  let user = null;
  try {
    user = JSON.parse(localStorage.getItem('user') || 'null');
  } catch (error) {
    // Handle corrupted localStorage data
    localStorage.removeItem('user');
  }
  const isLoggedIn = !!user;

  return (
    <AppBar position="static">
      <Toolbar>
        <Typography variant="h6" sx={{ flexGrow: 1 }}>
          HALBZEIT AI Review Platform
        </Typography>
        <LanguageSwitcher />
        {!isLoggedIn ? (
          <>
            <Button color="inherit" onClick={() => navigate('/login')}>
              {t('navigation.login')}
            </Button>
            <Button color="inherit" onClick={() => navigate('/register')}>
              {t('navigation.register')}
            </Button>
          </>
        ) : (
          <>
            <Button color="inherit" onClick={() => navigate('/profile')}>
              {t('navigation.profile')}
            </Button>
            <Button color="inherit" onClick={() => {
              localStorage.removeItem('user');
              window.location.href = '/login';
            }}>
              {t('navigation.logout')}
            </Button>
          </>
        )}
      </Toolbar>
    </AppBar>
  );
}

export default Navigation;
