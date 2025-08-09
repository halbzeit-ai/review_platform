import React, { useState, useEffect } from 'react';
import { 
  Container, 
  Paper, 
  TextField, 
  Button, 
  Typography, 
  Box, 
  Alert,
  InputAdornment,
  IconButton,
  List,
  ListItem,
  ListItemIcon,
  ListItemText
} from '@mui/material';
import { 
  Visibility, 
  VisibilityOff, 
  Lock, 
  Security, 
  CheckCircle, 
  Cancel 
} from '@mui/icons-material';
import { useNavigate, useLocation } from 'react-router-dom';
import { changeForcedPassword } from '../services/api';
import i18n from '../i18n';

function ChangePassword() {
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [userInfo, setUserInfo] = useState(null);
  const [passwordValidation, setPasswordValidation] = useState({
    length: false,
    complexity: false,
    noCommon: false,
    noSequential: false,
    noRepeated: false
  });
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    // Get temporary user data from localStorage
    const tempUser = localStorage.getItem('tempUser');
    if (!tempUser) {
      // If no temp user data, redirect to login
      navigate('/login');
      return;
    }
    
    const userData = JSON.parse(tempUser);
    setUserInfo(userData);
    
    // Set i18n language to user's preference
    if (userData.preferred_language) {
      i18n.changeLanguage(userData.preferred_language);
    }
  }, [navigate]);

  // Real-time password validation
  useEffect(() => {
    if (!newPassword) {
      setPasswordValidation({
        length: false,
        complexity: false,
        noCommon: false,
        noSequential: false,
        noRepeated: false
      });
      return;
    }

    const validation = {
      length: newPassword.length >= 8 && newPassword.length <= 128,
      complexity: validateComplexity(newPassword),
      noCommon: !isCommonPassword(newPassword),
      noSequential: !hasSequentialChars(newPassword),
      noRepeated: !hasRepeatedChars(newPassword)
    };

    setPasswordValidation(validation);
  }, [newPassword]);

  const validateComplexity = (password) => {
    const checks = {
      lowercase: /[a-z]/.test(password),
      uppercase: /[A-Z]/.test(password),
      digits: /[0-9]/.test(password),
      special: /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>/?`~]/.test(password)
    };
    
    return Object.values(checks).filter(Boolean).length >= 3;
  };

  const isCommonPassword = (password) => {
    const common = [
      'password', '123456', '123456789', 'qwerty', 'abc123', 
      'password123', '111111', '123123', 'admin', 'letmein',
      'welcome', 'monkey', '1234567890', 'password1'
    ];
    return common.includes(password.toLowerCase());
  };

  const hasSequentialChars = (password) => {
    return /(012|123|234|345|456|567|678|789|890|abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz)/i.test(password);
  };

  const hasRepeatedChars = (password) => {
    return /(.)\1{2,}/.test(password);
  };

  const isPasswordValid = () => {
    return Object.values(passwordValidation).every(Boolean);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    // Validation
    if (!newPassword || !confirmPassword) {
      setError('Please fill in all fields');
      return;
    }

    if (!isPasswordValid()) {
      setError('Please ensure all password requirements are met');
      return;
    }

    if (newPassword !== confirmPassword) {
      setError('New passwords do not match');
      return;
    }

    setLoading(true);

    try {
      const response = await changeForcedPassword(newPassword);
      const data = response.data;
      
      // Store user data in localStorage (remove temp data)
      localStorage.removeItem('tempUser');
      localStorage.setItem('user', JSON.stringify({
        email: data.email,
        role: data.role,
        token: data.access_token,
        companyName: userInfo.companyName,
        preferred_language: userInfo.preferred_language || 'de'
      }));

      // Check if there's a redirect URL from invitation acceptance
      const redirectUrl = location.state?.redirectUrl;
      const fromInvitation = location.state?.fromInvitation;
      
      if (redirectUrl && fromInvitation) {
        // Redirect to the specific project that user was invited to
        window.location.href = redirectUrl;
      } else {
        // Default redirect based on role
        if (data.role === 'startup') {
          window.location.href = '/dashboard';
        } else {
          window.location.href = '/dashboard/gp';
        }
      }
    } catch (error) {
      console.error('Change password error:', error);
      setError(error.response?.data?.detail || 'Failed to change password. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (!userInfo) {
    return null; // Will redirect to login
  }

  return (
    <Container component="main" maxWidth="sm">
      <Box
        sx={{
          marginTop: 8,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
        }}
      >
        <Paper elevation={3} sx={{ padding: 4, width: '100%' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
            <Security sx={{ mr: 2, color: 'primary.main', fontSize: 32 }} />
            <Typography component="h1" variant="h4" color="primary">
              Password Change Required
            </Typography>
          </Box>

          <Alert severity="info" sx={{ mb: 3 }}>
            <Typography variant="body2">
              <strong>Account Setup:</strong> Please create a secure password to complete your account setup. You won't need to enter your temporary password.
            </Typography>
          </Alert>

          <Typography variant="body1" sx={{ mb: 3 }}>
            Welcome <strong>{userInfo.email}</strong>! Create your secure password below.
          </Typography>

          <Box component="form" onSubmit={handleSubmit} sx={{ mt: 1 }}>
            {error && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {error}
              </Alert>
            )}

            <Typography variant="h6" sx={{ mb: 2, color: 'primary.main' }}>
              Password Requirements
            </Typography>
            
            <List dense sx={{ mb: 2, bgcolor: 'grey.50', borderRadius: 1, p: 1 }}>
              <ListItem>
                <ListItemIcon>
                  {passwordValidation.length ? <CheckCircle color="success" /> : <Cancel color="error" />}
                </ListItemIcon>
                <ListItemText primary="8-128 characters long" />
              </ListItem>
              <ListItem>
                <ListItemIcon>
                  {passwordValidation.complexity ? <CheckCircle color="success" /> : <Cancel color="error" />}
                </ListItemIcon>
                <ListItemText primary="At least 3 of: lowercase, uppercase, numbers, special chars" />
              </ListItem>
              <ListItem>
                <ListItemIcon>
                  {passwordValidation.noCommon ? <CheckCircle color="success" /> : <Cancel color="error" />}
                </ListItemIcon>
                <ListItemText primary="Not a common password" />
              </ListItem>
              <ListItem>
                <ListItemIcon>
                  {passwordValidation.noSequential ? <CheckCircle color="success" /> : <Cancel color="error" />}
                </ListItemIcon>
                <ListItemText primary="No sequential characters (123, abc, etc.)" />
              </ListItem>
              <ListItem>
                <ListItemIcon>
                  {passwordValidation.noRepeated ? <CheckCircle color="success" /> : <Cancel color="error" />}
                </ListItemIcon>
                <ListItemText primary="No more than 2 repeated characters" />
              </ListItem>
            </List>

            <TextField
              margin="normal"
              required
              fullWidth
              type={showNewPassword ? 'text' : 'password'}
              id="newPassword"
              label="New Secure Password"
              name="newPassword"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              error={newPassword && !isPasswordValid()}
              helperText={newPassword && !isPasswordValid() ? "Please meet all requirements above" : ""}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <Lock color="action" />
                  </InputAdornment>
                ),
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton
                      onClick={() => setShowNewPassword(!showNewPassword)}
                      edge="end"
                    >
                      {showNewPassword ? <VisibilityOff /> : <Visibility />}
                    </IconButton>
                  </InputAdornment>
                ),
              }}
            />

            <TextField
              margin="normal"
              required
              fullWidth
              type={showConfirmPassword ? 'text' : 'password'}
              id="confirmPassword"
              label="Confirm New Password"
              name="confirmPassword"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              error={confirmPassword && newPassword !== confirmPassword}
              helperText={confirmPassword && newPassword !== confirmPassword ? "Passwords do not match" : ""}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <Lock color="action" />
                  </InputAdornment>
                ),
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      edge="end"
                    >
                      {showConfirmPassword ? <VisibilityOff /> : <Visibility />}
                    </IconButton>
                  </InputAdornment>
                ),
              }}
            />

            <Button
              type="submit"
              fullWidth
              variant="contained"
              disabled={loading || !isPasswordValid() || !confirmPassword || newPassword !== confirmPassword}
              sx={{ mt: 3, mb: 2, py: 1.5 }}
            >
              {loading ? 'Setting Password...' : 'Set Password & Continue'}
            </Button>

            <Box sx={{ mt: 2, p: 2, bgcolor: 'success.light', borderRadius: 1, color: 'success.contrastText' }}>
              <Typography variant="body2">
                <strong>OWASP Security Standards:</strong> This password policy follows industry-standard security guidelines to protect your account.
              </Typography>
            </Box>
          </Box>
        </Paper>
      </Box>
    </Container>
  );
}

export default ChangePassword;