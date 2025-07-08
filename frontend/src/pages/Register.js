
import React, { useState } from 'react';
import { Container, Paper, TextField, Button, Typography } from '@mui/material';

function Register() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [role, setRole] = useState('startup');

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const response = await fetch('http://0.0.0.0:5001/api/auth/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email,
          password,
          company_name: companyName,
          role
        })
      });
      
      const data = await response.json();
      if (response.ok) {
        alert(`Registration successful!\nEmail: ${data.email}\nCompany: ${data.company_name}\nRole: ${data.role}`);
        // Redirect to login page after successful registration
        window.location.href = '/login';
      } else {
        alert(`Registration failed: ${data.detail || data.message || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Registration error:', error);
      alert(`Registration failed: ${error.message}`);
    }
  };

  return (
    <Container maxWidth="sm">
      <Paper sx={{ p: 3, mt: 4 }}>
        <Typography variant="h5" gutterBottom>Register</Typography>
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
          <TextField
            fullWidth
            margin="normal"
            label="Company Name"
            value={companyName}
            onChange={(e) => setCompanyName(e.target.value)}
          />
          <Button
            fullWidth
            variant="contained"
            color="primary"
            type="submit"
            sx={{ mt: 2 }}
          >
            Register
          </Button>
        </form>
      </Paper>
    </Container>
  );
}

export default Register;
