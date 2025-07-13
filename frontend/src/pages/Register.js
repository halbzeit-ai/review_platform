
import React, { useState } from 'react';
import { Container, Paper, TextField, Button, Typography, Box, Alert } from '@mui/material';
import { Email, CheckCircle } from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import { register } from '../services/api';

function Register() {
  const { t } = useTranslation('auth');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [role, setRole] = useState('startup');
  const [registrationComplete, setRegistrationComplete] = useState(false);
  const [registrationData, setRegistrationData] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      const response = await register(email, password, companyName, role);
      const data = response.data;
      
      setRegistrationData(data);
      setRegistrationComplete(true);
    } catch (error) {
      console.error('Registration error:', error);
      alert(`${t('register.errors.registrationFailed')}: ${error.response?.data?.detail || error.message || t('common:messages.connectionError')}`);
    }
    
    setLoading(false);
  };

  if (registrationComplete) {
    return (
      <Container maxWidth="sm">
        <Paper sx={{ p: 4, mt: 4, textAlign: 'center' }}>
          <CheckCircle sx={{ fontSize: 60, color: 'success.main', mb: 2 }} />
          <Typography variant="h5" gutterBottom>
            {t('register.success')}
          </Typography>
          
          <Alert severity="info" sx={{ mb: 3, textAlign: 'left' }}>
            <Typography variant="body1" gutterBottom>
              <strong>{t('register.emailSent')}</strong>
            </Typography>
            <Typography variant="body2">
              {t('register.emailSentTo')} <strong>{registrationData?.email}</strong>
            </Typography>
          </Alert>

          <Box sx={{ mb: 3 }}>
            <Typography variant="body1" gutterBottom>
              <strong>{t('register.accountDetails')}</strong>
            </Typography>
            <Typography variant="body2">{t('register.emailLabel')} {registrationData?.email}</Typography>
            <Typography variant="body2">{t('register.companyLabel')} {registrationData?.company_name}</Typography>
            <Typography variant="body2">{t('register.roleLabel')} {registrationData?.role}</Typography>
          </Box>

          <Alert severity="warning" sx={{ mb: 3 }}>
            <Typography variant="body2">
              {t('register.verificationReminder')}
            </Typography>
          </Alert>

          <Button
            variant="contained"
            startIcon={<Email />}
            onClick={() => window.location.href = '/login'}
            sx={{ mt: 2 }}
          >
            {t('verification.goToLogin')}
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
            {t('register.title')}
          </Typography>
          <Typography variant="subtitle1" color="text.secondary">
            {t('register.subtitle')}
          </Typography>
        </Box>
        
        <form onSubmit={handleSubmit}>
          <TextField
            fullWidth
            margin="normal"
            label={t('register.emailLabel')}
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            disabled={loading}
          />
          <TextField
            fullWidth
            margin="normal"
            label={t('register.passwordLabel')}
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            disabled={loading}
          />
          <TextField
            fullWidth
            margin="normal"
            label={t('register.companyNameLabel')}
            value={companyName}
            onChange={(e) => setCompanyName(e.target.value)}
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
            {loading ? t('common:buttons.loading') : t('register.registerButton')}
          </Button>
        </form>

        <Box sx={{ textAlign: 'center', mt: 2 }}>
          <Typography variant="body2">
            {t('register.hasAccount')}{' '}
            <Button
              variant="text"
              onClick={() => window.location.href = '/login'}
            >
              {t('register.loginLink')}
            </Button>
          </Typography>
        </Box>
      </Paper>
    </Container>
  );
}

export default Register;
