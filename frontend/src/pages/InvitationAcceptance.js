import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Container,
  Paper,
  Typography,
  TextField,
  Button,
  Box,
  Alert,
  CircularProgress,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Divider
} from '@mui/material';
import { Business, Email, Person, VpnKey } from '@mui/icons-material';
import { getInvitationDetails, acceptInvitation } from '../services/api';

const InvitationAcceptance = () => {
  const { token } = useParams();
  const navigate = useNavigate();
  
  const [invitation, setInvitation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    company_name: '',
    password: '',
    confirm_password: '',
    preferred_language: 'en'
  });

  useEffect(() => {
    fetchInvitationDetails();
  }, [token]);

  const fetchInvitationDetails = async () => {
    try {
      setLoading(true);
      const response = await getInvitationDetails(token);
      setInvitation(response.data);
      setError('');
    } catch (error) {
      console.error('Error fetching invitation details:', error);
      setError(
        error.response?.status === 404 
          ? 'Invalid, expired, or already used invitation link.'
          : 'Failed to load invitation details. Please try again.'
      );
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (field) => (event) => {
    setFormData({
      ...formData,
      [field]: event.target.value
    });
  };

  const validateForm = () => {
    if (!formData.first_name.trim()) {
      setError('First name is required');
      return false;
    }
    if (!formData.last_name.trim()) {
      setError('Last name is required');
      return false;
    }
    if (!formData.company_name.trim()) {
      setError('Company name is required');
      return false;
    }
    if (formData.password.length < 6) {
      setError('Password must be at least 6 characters long');
      return false;
    }
    if (formData.password !== formData.confirm_password) {
      setError('Passwords do not match');
      return false;
    }
    return true;
  };

  const handleAcceptInvitation = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    setSubmitting(true);
    setError('');

    try {
      const acceptData = {
        first_name: formData.first_name.trim(),
        last_name: formData.last_name.trim(),
        company_name: formData.company_name.trim(),
        password: formData.password,
        preferred_language: formData.preferred_language
      };

      const response = await acceptInvitation(token, acceptData);
      
      setSuccess('Account created successfully! You will be redirected to your project.');
      
      // Redirect after a short delay
      setTimeout(() => {
        if (response.data.redirect_url) {
          navigate(response.data.redirect_url);
        } else {
          navigate('/login');
        }
      }, 2000);

    } catch (error) {
      console.error('Error accepting invitation:', error);
      setError(
        error.response?.data?.detail || 
        'Failed to accept invitation. Please try again.'
      );
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <Container maxWidth="sm" sx={{ mt: 8, display: 'flex', justifyContent: 'center' }}>
        <CircularProgress />
      </Container>
    );
  }

  if (error && !invitation) {
    return (
      <Container maxWidth="sm" sx={{ mt: 8 }}>
        <Paper elevation={3} sx={{ p: 4 }}>
          <Alert severity="error">{error}</Alert>
          <Box sx={{ mt: 2, textAlign: 'center' }}>
            <Button variant="outlined" onClick={() => navigate('/login')}>
              Go to Login
            </Button>
          </Box>
        </Paper>
      </Container>
    );
  }

  return (
    <Container maxWidth="sm" sx={{ mt: 4 }}>
      <Paper elevation={3} sx={{ p: 4 }}>
        <Box sx={{ textAlign: 'center', mb: 3 }}>
          <Typography variant="h4" component="h1" gutterBottom color="primary">
            🚀 Welcome to HALBZEIT AI
          </Typography>
          <Typography variant="h6" color="text.secondary">
            You're invited to join: {invitation?.project_name}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            Invited by: {invitation?.gp_name}
          </Typography>
        </Box>

        <Divider sx={{ my: 3 }} />

        {success && (
          <Alert severity="success" sx={{ mb: 3 }}>
            {success}
          </Alert>
        )}

        {error && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {error}
          </Alert>
        )}

        <form onSubmit={handleAcceptInvitation}>
          <Typography variant="h6" gutterBottom sx={{ mt: 2 }}>
            Create Your Account
          </Typography>

          <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
            <TextField
              fullWidth
              label="First Name"
              value={formData.first_name}
              onChange={handleInputChange('first_name')}
              required
              InputProps={{
                startAdornment: <Person sx={{ color: 'action.active', mr: 1 }} />,
              }}
            />
            <TextField
              fullWidth
              label="Last Name"
              value={formData.last_name}
              onChange={handleInputChange('last_name')}
              required
              InputProps={{
                startAdornment: <Person sx={{ color: 'action.active', mr: 1 }} />,
              }}
            />
          </Box>

          <TextField
            fullWidth
            label="Company Name"
            value={formData.company_name}
            onChange={handleInputChange('company_name')}
            required
            sx={{ mb: 2 }}
            InputProps={{
              startAdornment: <Business sx={{ color: 'action.active', mr: 1 }} />,
            }}
          />

          <TextField
            fullWidth
            label="Email"
            value={invitation?.email || ''}
            disabled
            sx={{ mb: 2 }}
            InputProps={{
              startAdornment: <Email sx={{ color: 'action.active', mr: 1 }} />,
            }}
            helperText="This email is pre-filled from your invitation"
          />

          <TextField
            fullWidth
            type="password"
            label="Password"
            value={formData.password}
            onChange={handleInputChange('password')}
            required
            sx={{ mb: 2 }}
            helperText="Minimum 6 characters"
            InputProps={{
              startAdornment: <VpnKey sx={{ color: 'action.active', mr: 1 }} />,
            }}
          />

          <TextField
            fullWidth
            type="password"
            label="Confirm Password"
            value={formData.confirm_password}
            onChange={handleInputChange('confirm_password')}
            required
            sx={{ mb: 2 }}
            InputProps={{
              startAdornment: <VpnKey sx={{ color: 'action.active', mr: 1 }} />,
            }}
          />

          <FormControl fullWidth sx={{ mb: 3 }}>
            <InputLabel>Preferred Language</InputLabel>
            <Select
              value={formData.preferred_language}
              onChange={handleInputChange('preferred_language')}
              label="Preferred Language"
            >
              <MenuItem value="en">English</MenuItem>
              <MenuItem value="de">Deutsch</MenuItem>
            </Select>
          </FormControl>

          <Button
            type="submit"
            fullWidth
            variant="contained"
            size="large"
            disabled={submitting}
            sx={{ mb: 2 }}
          >
            {submitting ? (
              <>
                <CircularProgress size={20} sx={{ mr: 1 }} />
                Creating Account...
              </>
            ) : (
              'Accept Invitation & Create Account'
            )}
          </Button>

          <Box sx={{ textAlign: 'center' }}>
            <Typography variant="body2" color="text.secondary">
              Already have an account?{' '}
              <Button variant="text" onClick={() => navigate('/login')}>
                Sign In
              </Button>
            </Typography>
          </Box>
        </form>
      </Paper>
    </Container>
  );
};

export default InvitationAcceptance;