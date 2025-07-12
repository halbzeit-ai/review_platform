
import React, { useState } from 'react';
import { Container, Paper, TextField, Button, Typography, Box, Alert } from '@mui/material';
import { Email, CheckCircle } from '@mui/icons-material';
import { register } from '../services/api';

function Register() {
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
      alert(`Registration failed: ${error.response?.data?.detail || error.message || 'Unknown error'}`);
    }
    
    setLoading(false);
  };

  if (registrationComplete) {
    return (
      <Container maxWidth="sm">
        <Paper sx={{ p: 4, mt: 4, textAlign: 'center' }}>
          <CheckCircle sx={{ fontSize: 60, color: 'success.main', mb: 2 }} />
          <Typography variant="h5" gutterBottom>
            Registration Successful!
          </Typography>
          
          <Alert severity="info" sx={{ mb: 3, textAlign: 'left' }}>
            <Typography variant="body1" gutterBottom>
              <strong>Please check your email to verify your account</strong>
            </Typography>
            <Typography variant="body2">
              We've sent a verification email to <strong>{registrationData?.email}</strong>
            </Typography>
          </Alert>

          <Box sx={{ mb: 3 }}>
            <Typography variant="body1" gutterBottom>
              <strong>Account Details:</strong>
            </Typography>
            <Typography variant="body2">Email: {registrationData?.email}</Typography>
            <Typography variant="body2">Company: {registrationData?.company_name}</Typography>
            <Typography variant="body2">Role: {registrationData?.role}</Typography>
          </Box>

          <Alert severity="warning" sx={{ mb: 3 }}>
            <Typography variant="body2">
              You must verify your email before you can log in. 
              The verification link will expire in 24 hours.
            </Typography>
          </Alert>

          <Button
            variant="contained"
            startIcon={<Email />}
            onClick={() => window.location.href = '/login'}
            sx={{ mt: 2 }}
          >
            Go to Login
          </Button>
        </Paper>
      </Container>
    );
  }

  return (
    <Container maxWidth="sm">
      <Paper sx={{ p: 3, mt: 4 }}>
        <Typography variant="h5" gutterBottom>Register</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          Create your HALBZEIT AI account. You'll need to verify your email before you can log in.
        </Typography>
        
        <form onSubmit={handleSubmit}>
          <TextField
            fullWidth
            margin="normal"
            label="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            disabled={loading}
          />
          <TextField
            fullWidth
            margin="normal"
            label="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            disabled={loading}
          />
          <TextField
            fullWidth
            margin="normal"
            label="Company Name"
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
            sx={{ mt: 2 }}
            disabled={loading}
          >
            {loading ? 'Creating Account...' : 'Register'}
          </Button>
        </form>
      </Paper>
    </Container>
  );
}

export default Register;
