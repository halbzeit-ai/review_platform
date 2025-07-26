import React, { useState } from 'react';
import { Container, Paper, TextField, Button, Typography, Box, Link, Alert, Dialog, DialogTitle, DialogContent, DialogActions } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { login, forgotPassword } from '../services/api';
import i18n from '../i18n';

function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [forgotPasswordOpen, setForgotPasswordOpen] = useState(false);
  const [forgotPasswordEmail, setForgotPasswordEmail] = useState('');
  const [forgotPasswordSuccess, setForgotPasswordSuccess] = useState(false);
  const [forgotPasswordLoading, setForgotPasswordLoading] = useState(false);
  const navigate = useNavigate();
  const { t } = useTranslation('auth');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await login(email, password);
      const data = response.data;
      
      // Store user data in localStorage
      localStorage.clear();
      localStorage.setItem('user', JSON.stringify({
        email: data.email,
        role: data.role,
        token: data.access_token,
        companyName: data.company_name,
        preferred_language: data.preferred_language || 'de'
      }));

      // Set i18n language to user's preference
      if (data.preferred_language) {
        i18n.changeLanguage(data.preferred_language);
        localStorage.setItem('language', data.preferred_language);
      }

      // Redirect based on role - use generic dashboard redirect for consistency
      if (data.role === 'startup') {
        window.location.href = '/dashboard';
      } else {
        window.location.href = '/dashboard/gp';
      }
    } catch (error) {
      console.error('Login error:', error);
      setError(error.response?.data?.detail || t('login.errors.loginFailed'));
    } finally {
      setLoading(false);
    }
  };

  const handleForgotPassword = async (e) => {
    e.preventDefault();
    setForgotPasswordLoading(true);
    
    try {
      await forgotPassword(forgotPasswordEmail);
      setForgotPasswordSuccess(true);
    } catch (error) {
      console.error('Forgot password error:', error);
      // Don't show specific error for security - the API returns generic message
    } finally {
      setForgotPasswordLoading(false);
    }
  };

  const handleCloseForgotPassword = () => {
    setForgotPasswordOpen(false);
    setForgotPasswordEmail('');
    setForgotPasswordSuccess(false);
  };

  return (
    <Container maxWidth="sm" sx={{ mt: 8 }}>
      <Paper elevation={3} sx={{ p: 4 }}>
        <Box sx={{ textAlign: 'center', mb: 3 }}>
          <Typography variant="h4" component="h1" gutterBottom>
            {t('login.title')}
          </Typography>
          <Typography variant="subtitle1" color="text.secondary">
            {t('login.subtitle')}
          </Typography>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        <form onSubmit={handleSubmit}>
          <TextField
            fullWidth
            margin="normal"
            label={t('login.emailLabel')}
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            disabled={loading}
          />
          <TextField
            fullWidth
            margin="normal"
            label={t('login.passwordLabel')}
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            disabled={loading}
          />
          <Button
            fullWidth
            variant="contained"
            color="primary"
            type="submit"
            sx={{ mt: 3, mb: 2 }}
            disabled={loading}
          >
            {loading ? t('common:buttons.loading') : t('login.loginButton')}
          </Button>
        </form>

        <Box sx={{ textAlign: 'center', mt: 2 }}>
          <Typography variant="body2">
            {t('login.noAccount')}{' '}
            <Link
              component="button"
              variant="body2"
              onClick={() => navigate('/register')}
            >
              {t('login.registerLink')}
            </Link>
          </Typography>
          <Typography variant="body2" sx={{ mt: 1 }}>
            <Link
              component="button"
              variant="body2"
              onClick={() => setForgotPasswordOpen(true)}
            >
              {t('login.forgotPassword')}
            </Link>
          </Typography>
        </Box>
      </Paper>

      {/* Forgot Password Dialog */}
      <Dialog open={forgotPasswordOpen} onClose={handleCloseForgotPassword} maxWidth="sm" fullWidth>
        <DialogTitle>{t('login.forgotPasswordTitle')}</DialogTitle>
        <DialogContent>
          {forgotPasswordSuccess ? (
            <Alert severity="success" sx={{ mt: 2 }}>
              {t('login.forgotPasswordSuccess')}
            </Alert>
          ) : (
            <form onSubmit={handleForgotPassword}>
              <Typography variant="body2" sx={{ mb: 2 }}>
                {t('login.forgotPasswordDescription')}
              </Typography>
              <TextField
                fullWidth
                margin="normal"
                label={t('login.emailLabel')}
                type="email"
                value={forgotPasswordEmail}
                onChange={(e) => setForgotPasswordEmail(e.target.value)}
                required
                disabled={forgotPasswordLoading}
              />
            </form>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseForgotPassword}>
            {forgotPasswordSuccess ? t('common:buttons.close') : t('common:buttons.cancel')}
          </Button>
          {!forgotPasswordSuccess && (
            <Button
              onClick={handleForgotPassword}
              variant="contained"
              disabled={forgotPasswordLoading || !forgotPasswordEmail}
            >
              {forgotPasswordLoading ? t('common:buttons.loading') : t('login.sendResetLink')}
            </Button>
          )}
        </DialogActions>
      </Dialog>
    </Container>
  );
}

export default Login;