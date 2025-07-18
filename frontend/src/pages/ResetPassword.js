import React, { useState, useEffect } from 'react';
import { Container, Paper, TextField, Button, Typography, Box, Alert } from '@mui/material';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { resetPassword } from '../services/api';

function ResetPassword() {
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { t } = useTranslation('auth');

  const token = searchParams.get('token');

  useEffect(() => {
    if (!token) {
      setError(t('resetPassword.invalidToken'));
    }
  }, [token, t]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (password !== confirmPassword) {
      setError(t('resetPassword.passwordMismatch'));
      return;
    }

    if (password.length < 6) {
      setError(t('resetPassword.passwordTooShort'));
      return;
    }

    setLoading(true);

    try {
      await resetPassword(token, password);
      setSuccess(true);
    } catch (error) {
      console.error('Reset password error:', error);
      setError(error.response?.data?.detail || t('resetPassword.resetFailed'));
    } finally {
      setLoading(false);
    }
  };

  const handleGoToLogin = () => {
    navigate('/login');
  };

  if (success) {
    return (
      <Container maxWidth="sm" sx={{ mt: 8 }}>
        <Paper elevation={3} sx={{ p: 4 }}>
          <Box sx={{ textAlign: 'center', mb: 3 }}>
            <Typography variant="h4" component="h1" gutterBottom>
              {t('resetPassword.successTitle')}
            </Typography>
          </Box>

          <Alert severity="success" sx={{ mb: 3 }}>
            {t('resetPassword.successMessage')}
          </Alert>

          <Button
            fullWidth
            variant="contained"
            color="primary"
            onClick={handleGoToLogin}
            sx={{ mt: 2 }}
          >
            {t('resetPassword.goToLogin')}
          </Button>
        </Paper>
      </Container>
    );
  }

  return (
    <Container maxWidth="sm" sx={{ mt: 8 }}>
      <Paper elevation={3} sx={{ p: 4 }}>
        <Box sx={{ textAlign: 'center', mb: 3 }}>
          <Typography variant="h4" component="h1" gutterBottom>
            {t('resetPassword.title')}
          </Typography>
          <Typography variant="subtitle1" color="text.secondary">
            {t('resetPassword.subtitle')}
          </Typography>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {!token ? (
          <Alert severity="error" sx={{ mb: 2 }}>
            {t('resetPassword.invalidToken')}
          </Alert>
        ) : (
          <form onSubmit={handleSubmit}>
            <TextField
              fullWidth
              margin="normal"
              label={t('resetPassword.newPasswordLabel')}
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              disabled={loading}
            />
            <TextField
              fullWidth
              margin="normal"
              label={t('resetPassword.confirmPasswordLabel')}
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              disabled={loading}
            />
            <Button
              fullWidth
              variant="contained"
              color="primary"
              type="submit"
              sx={{ mt: 3, mb: 2 }}
              disabled={loading || !password || !confirmPassword}
            >
              {loading ? t('common:buttons.loading') : t('resetPassword.resetButton')}
            </Button>
          </form>
        )}

        <Box sx={{ textAlign: 'center', mt: 2 }}>
          <Button
            variant="text"
            onClick={handleGoToLogin}
          >
            {t('resetPassword.backToLogin')}
          </Button>
        </Box>
      </Paper>
    </Container>
  );
}

export default ResetPassword;