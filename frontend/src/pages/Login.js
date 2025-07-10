import React, { useState } from 'react';
import { Container, Paper, TextField, Button, Typography } from '@mui/material';
import { login } from '../services/api';

function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const response = await login(email, password);
      const data = response.data;
      
      // Store user data in localStorage
      localStorage.clear();
      // Store new user data
      localStorage.setItem('user', JSON.stringify({
        email: data.email,
        role: data.role,
        token: data.access_token,
        companyName: data.company_name
      }));

      // Redirect based on role
      window.location.href = data.role === 'startup' ? '/dashboard/startup' : '/dashboard/gp';
    } catch (error) {
      console.error('Login error:', error);
      alert(`Login failed: ${error.response?.data?.detail || 'Invalid credentials'}`);
    }
  };

  return (
    <Container maxWidth="sm">
      <Paper sx={{ p: 3, mt: 4 }}>
        <Typography variant="h5" gutterBottom>Login</Typography>
        <form onSubmit={handleSubmit}>
          <TextField
            fullWidth
            margin="normal"
            label="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <TextField
            fullWidth
            margin="normal"
            label="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <Button
            fullWidth
            variant="contained"
            color="primary"
            type="submit"
            sx={{ mt: 2 }}
          >
            Login
          </Button>
        </form>
      </Paper>
    </Container>
  );
}

export default Login;