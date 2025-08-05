import React, { useState } from 'react';
import { Container, Paper, TextField, Button, Typography, Box, Link, Alert, Dialog, DialogTitle, DialogContent, DialogActions, Grid, Divider } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { login, forgotPassword } from '../services/api';
import LanguageSwitcher from '../components/LanguageSwitcher';
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
      
      // Check if password change is required
      if (data.must_change_password) {
        // Store temporary user data for password change
        localStorage.clear();
        localStorage.setItem('tempUser', JSON.stringify({
          email: data.email,
          role: data.role,
          token: data.access_token,
          companyName: data.company_name,
          preferred_language: data.preferred_language || 'de'
        }));
        
        // Redirect to change password page
        navigate('/change-password');
        return;
      }
      
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
    <Box sx={{ minHeight: '100vh', backgroundColor: '#f8f9fa' }}>
      {/* Header */}
      <Box sx={{ backgroundColor: 'primary.main', color: 'white', py: 2 }}>
        <Container maxWidth="lg">
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography variant="h5" component="h1" sx={{ fontWeight: 600 }}>
              HALBZEIT AI: Funding Health Innovations Together
            </Typography>
            <LanguageSwitcher />
          </Box>
        </Container>
      </Box>

      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Grid container spacing={4}>
          {/* Mission Content - Left Side */}
          <Grid item xs={12} md={7}>
            <Paper elevation={2} sx={{ p: 4, height: 'fit-content' }}>
              <Typography variant="h4" component="h2" gutterBottom sx={{ color: 'primary.main', fontWeight: 700 }}>
                {t('homepage.welcomeTitle')}
              </Typography>

              <Typography variant="body1" paragraph sx={{ lineHeight: 1.8 }}>
                {t('homepage.missionIntro')}
              </Typography>

              <Typography variant="body1" paragraph sx={{ lineHeight: 1.8 }}>
                {t('homepage.missionProblem')}
              </Typography>

              <Typography variant="h6" sx={{ color: 'primary.main', fontWeight: 600, mt: 3 }}>
                {t('homepage.missionTransition')}
              </Typography>

              <Typography variant="h5" component="h3" gutterBottom sx={{ mt: 4, mb: 2, color: 'primary.main', fontWeight: 600 }}>
                {t('homepage.purposeTitle')}
              </Typography>

              <Typography variant="body1" paragraph sx={{ lineHeight: 1.8 }}>
                {t('homepage.purposeText')}
              </Typography>

              <Typography variant="body1" paragraph sx={{ lineHeight: 1.8 }}>
                {t('homepage.purposeText2')}
              </Typography>

              <Typography variant="h5" component="h3" gutterBottom sx={{ mt: 4, mb: 2, color: 'primary.main', fontWeight: 600 }}>
                {t('homepage.approachTitle')}
              </Typography>

              <Typography variant="body1" paragraph sx={{ lineHeight: 1.8 }}>
                {t('homepage.approachIntro')}
              </Typography>

              <Box sx={{ mt: 3 }}>
                <Typography variant="body1" paragraph sx={{ lineHeight: 1.8, mb: 2 }}>
                  • <strong>{t('homepage.valueCollaborationTitle')}</strong>: {t('homepage.valueCollaborationText')}
                </Typography>
                <Typography variant="body1" paragraph sx={{ lineHeight: 1.8, mb: 2 }}>
                  • <strong>{t('homepage.valueIntegrityTitle')}</strong>: {t('homepage.valueIntegrityText')}
                </Typography>
                <Typography variant="body1" paragraph sx={{ lineHeight: 1.8, mb: 2 }}>
                  • <strong>{t('homepage.valueEmpowermentTitle')}</strong>: {t('homepage.valueEmpowermentText')}
                </Typography>
                <Typography variant="body1" paragraph sx={{ lineHeight: 1.8, mb: 2 }}>
                  • <strong>{t('homepage.valueLongTermTitle')}</strong>: {t('homepage.valueLongTermText')}
                </Typography>
              </Box>

              <Typography variant="h5" component="h3" gutterBottom sx={{ mt: 4, mb: 2, color: 'primary.main', fontWeight: 600 }}>
                {t('homepage.whyNowTitle')}
              </Typography>

              <Typography variant="body1" paragraph sx={{ lineHeight: 1.8 }}>
                {t('homepage.whyNowText')}
              </Typography>

              <Typography variant="body1" paragraph sx={{ lineHeight: 1.8 }}>
                {t('homepage.whyNowConclusion')}
              </Typography>
            </Paper>
          </Grid>

          {/* Login Form - Right Side */}
          <Grid item xs={12} md={5}>
            <Paper elevation={3} sx={{ p: 4, position: 'sticky', top: 20 }}>
              <Box sx={{ textAlign: 'center', mb: 3 }}>
                <Alert severity="info" sx={{ mb: 3 }}>
                  {t('homepage.invitationOnly')}
                </Alert>
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
                    sx={{ 
                      color: 'text.disabled', 
                      cursor: 'not-allowed',
                      textDecoration: 'none',
                      '&:hover': {
                        textDecoration: 'none'
                      }
                    }}
                    disabled
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
          </Grid>
        </Grid>
      </Container>

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
    </Box>
  );
}

export default Login;