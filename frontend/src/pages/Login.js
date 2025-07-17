import React, { useState } from 'react';
import { Container, Paper, TextField, Button, Typography, Box, Link, Alert } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { login } from '../services/api';
import i18n from '../i18n';

function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
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

      // Redirect based on role
      if (data.role === 'startup') {
        // Generate company ID using same logic as backend
        const getCompanyId = () => {
          if (data.company_name) {
            // Convert company name to a URL-safe slug (same logic as backend)
            return data.company_name.toLowerCase().replace(' ', '-').replace(/[^a-z0-9-]/g, '');
          }
          // Fallback to email prefix if company name is not available
          return data.email.split('@')[0];
        };
        
        const companyId = getCompanyId();
        window.location.href = `/project/${companyId}`;
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
        </Box>
      </Paper>
    </Container>
  );
}

export default Login;