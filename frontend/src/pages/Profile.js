import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Grid,
  TextField,
  Button,
  Alert,
  CircularProgress,
  Card,
  CardContent,
  Avatar,
  Divider,
  FormControl,
  InputLabel,
  Select,
  MenuItem
} from '@mui/material';
import {
  Person as PersonIcon,
  Save as SaveIcon,
  AccountCircle as AccountCircleIcon
} from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';

const Profile = () => {
  const { t, i18n } = useTranslation(['common', 'auth']);
  const navigate = useNavigate();
  
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  
  const [profile, setProfile] = useState({
    email: '',
    first_name: '',
    last_name: '',
    company_name: '',
    role: '',
    preferred_language: 'de',
    is_verified: false,
    created_at: null,
    last_login: null
  });

  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    company_name: '',
    preferred_language: 'de'
  });

  useEffect(() => {
    loadProfile();
  }, []);

  const loadProfile = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await api.get('/auth/profile');
      const profileData = response.data;
      
      setProfile(profileData);
      setFormData({
        first_name: profileData.first_name || '',
        last_name: profileData.last_name || '',
        company_name: profileData.company_name || '',
        preferred_language: profileData.preferred_language || 'de'
      });
      
    } catch (err) {
      console.error('Error loading profile:', err);
      setError(err.response?.data?.detail || 'Failed to load profile');
      
      // If unauthorized, redirect to login
      if (err.response?.status === 401) {
        navigate('/login');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
    
    // Clear success message when user starts editing
    if (success) {
      setSuccess(null);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setError(null);
      setSuccess(null);
      
      // Only send fields that have changed
      const changedFields = {};
      Object.keys(formData).forEach(key => {
        if (formData[key] !== (profile[key] || '')) {
          changedFields[key] = formData[key];
        }
      });
      
      if (Object.keys(changedFields).length === 0) {
        setSuccess(t('auth:profile.noChanges'));
        return;
      }
      
      const response = await api.put('/auth/profile', changedFields);
      const updatedProfile = response.data.profile;
      
      // Update local profile state
      setProfile(updatedProfile);
      
      // If language changed, update i18n
      if (changedFields.preferred_language && changedFields.preferred_language !== i18n.language) {
        await i18n.changeLanguage(changedFields.preferred_language);
      }
      
      setSuccess(t('auth:profile.updateSuccess'));
      
    } catch (err) {
      console.error('Error updating profile:', err);
      setError(err.response?.data?.detail || 'Failed to update profile');
    } finally {
      setSaving(false);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleDateString();
  };

  const getUserInitials = () => {
    const firstName = profile.first_name || '';
    const lastName = profile.last_name || '';
    return `${firstName.charAt(0)}${lastName.charAt(0)}`.toUpperCase() || profile.email.charAt(0).toUpperCase();
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', mt: 4 }}>
        <CircularProgress />
        <Typography sx={{ ml: 2 }}>{t('common:loading')}</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3, maxWidth: 800, mx: 'auto' }}>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <PersonIcon sx={{ mr: 2, fontSize: 32, color: 'primary.main' }} />
        <Typography variant="h4">
          {t('common:navigation.profile')}
        </Typography>
      </Box>

      {/* Error/Success Messages */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}
      
      {success && (
        <Alert severity="success" sx={{ mb: 3 }}>
          {success}
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* Profile Summary Card */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <Avatar
                sx={{
                  width: 80,
                  height: 80,
                  mx: 'auto',
                  mb: 2,
                  bgcolor: 'primary.main',
                  fontSize: '2rem'
                }}
              >
                {getUserInitials()}
              </Avatar>
              
              <Typography variant="h6" gutterBottom>
                {profile.first_name && profile.last_name 
                  ? `${profile.first_name} ${profile.last_name}`
                  : profile.email
                }
              </Typography>
              
              <Typography variant="body2" color="text.secondary" gutterBottom>
                {profile.email}
              </Typography>
              
              <Typography variant="body2" color="text.secondary" gutterBottom>
                {t(`auth:roles.${profile.role}`)}
              </Typography>
              
              {profile.company_name && (
                <Typography variant="body2" color="text.secondary">
                  {profile.company_name}
                </Typography>
              )}
              
              <Divider sx={{ my: 2 }} />
              
              <Box sx={{ textAlign: 'left' }}>
                <Typography variant="caption" color="text.secondary">
                  {t('auth:profile.memberSince')}: {formatDate(profile.created_at)}
                </Typography>
                <br />
                <Typography variant="caption" color="text.secondary">
                  {t('auth:profile.lastLogin')}: {formatDate(profile.last_login)}
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Profile Edit Form */}
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
              <AccountCircleIcon sx={{ mr: 1 }} />
              {t('auth:profile.editProfile')}
            </Typography>
            
            <Grid container spacing={3}>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label={t('auth:profile.firstName')}
                  value={formData.first_name}
                  onChange={(e) => handleInputChange('first_name', e.target.value)}
                  variant="outlined"
                />
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label={t('auth:profile.lastName')}
                  value={formData.last_name}
                  onChange={(e) => handleInputChange('last_name', e.target.value)}
                  variant="outlined"
                />
              </Grid>
              
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label={t('auth:profile.companyName')}
                  value={formData.company_name}
                  onChange={(e) => handleInputChange('company_name', e.target.value)}
                  variant="outlined"
                />
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth>
                  <InputLabel>{t('auth:profile.preferredLanguage')}</InputLabel>
                  <Select
                    value={formData.preferred_language}
                    onChange={(e) => handleInputChange('preferred_language', e.target.value)}
                    label={t('auth:profile.preferredLanguage')}
                  >
                    <MenuItem value="de">{t('common:languages.german')}</MenuItem>
                    <MenuItem value="en">{t('common:languages.english')}</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label={t('auth:profile.email')}
                  value={profile.email}
                  variant="outlined"
                  disabled
                  helperText={t('auth:profile.emailNotEditable')}
                />
              </Grid>
              
              <Grid item xs={12}>
                <Box sx={{ display: 'flex', gap: 2, justifyContent: 'flex-end' }}>
                  <Button
                    variant="outlined"
                    onClick={loadProfile}
                    disabled={saving}
                  >
                    {t('common:actions.cancel')}
                  </Button>
                  
                  <Button
                    variant="contained"
                    onClick={handleSave}
                    disabled={saving}
                    startIcon={saving ? <CircularProgress size={16} /> : <SaveIcon />}
                  >
                    {saving ? t('common:actions.saving') : t('common:actions.save')}
                  </Button>
                </Box>
              </Grid>
            </Grid>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Profile;