import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Typography,
  Box,
  Alert,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Grid,
  IconButton,
  Divider
} from '@mui/material';
import {
  Business,
  AccountBalance,
  Email,
  Close,
  Add,
  Delete
} from '@mui/icons-material';
import { createProject } from '../services/api';

const CreateProjectDialog = ({ open, onClose, onProjectCreated }) => {
  const [formData, setFormData] = useState({
    project_name: '',
    company_name: '',
    invite_emails: [''],
    invitation_language: 'en'
  });
  
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');


  const handleInputChange = (field) => (event) => {
    setFormData({
      ...formData,
      [field]: event.target.value
    });
  };

  const handleEmailChange = (index, value) => {
    const newEmails = [...formData.invite_emails];
    newEmails[index] = value;
    setFormData({
      ...formData,
      invite_emails: newEmails
    });
  };

  const addEmailField = () => {
    if (formData.invite_emails.length < 5) {
      setFormData({
        ...formData,
        invite_emails: [...formData.invite_emails, '']
      });
    }
  };

  const removeEmailField = (index) => {
    if (formData.invite_emails.length > 1) {
      const newEmails = formData.invite_emails.filter((_, i) => i !== index);
      setFormData({
        ...formData,
        invite_emails: newEmails
      });
    }
  };

  const validateForm = () => {
    if (!formData.project_name.trim()) {
      setError('Project name is required');
      return false;
    }
    if (!formData.company_name.trim()) {
      setError('Company name is required');
      return false;
    }
    
    // Validate emails (only non-empty ones)
    const validEmails = formData.invite_emails.filter(email => email.trim());
    for (const email of validEmails) {
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
        setError(`Invalid email address: ${email}`);
        return false;
      }
    }
    
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    setSubmitting(true);
    setError('');
    setSuccess('');

    try {
      // Filter out empty emails
      const validEmails = formData.invite_emails
        .map(email => email.trim())
        .filter(email => email);

      const projectData = {
        project_name: formData.project_name.trim(),
        company_name: formData.company_name.trim(),
        invite_emails: validEmails,
        invitation_language: formData.invitation_language
      };

      const response = await createProject(projectData);
      
      setSuccess(
        `Project "${projectData.project_name}" created successfully! ` +
        `${response.data.invitations_sent} invitation(s) sent.`
      );
      
      // Reset form
      setFormData({
        project_name: '',
        company_name: '',
        invite_emails: [''],
        invitation_language: 'en'
      });
      
      // Notify parent component
      if (onProjectCreated) {
        onProjectCreated(response.data);
      }
      
      // Close dialog after a short delay to show success message
      setTimeout(() => {
        setSuccess('');
        onClose();
      }, 2000);

    } catch (error) {
      console.error('Error creating project:', error);
      setError(
        error.response?.data?.detail || 
        'Failed to create project. Please try again.'
      );
    } finally {
      setSubmitting(false);
    }
  };

  const handleClose = () => {
    if (!submitting) {
      setError('');
      setSuccess('');
      onClose();
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Typography variant="h6">
            Create New Project
          </Typography>
          <IconButton onClick={handleClose} disabled={submitting}>
            <Close />
          </IconButton>
        </Box>
      </DialogTitle>

      <DialogContent>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {success && (
          <Alert severity="success" sx={{ mb: 2 }}>
            {success}
          </Alert>
        )}

        <form onSubmit={handleSubmit}>
          <Grid container spacing={3}>
            {/* Project Information */}
            <Grid item xs={12}>
              <Typography variant="h6" gutterBottom sx={{ mt: 2 }}>
                Project Information
              </Typography>
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Project Name"
                value={formData.project_name}
                onChange={handleInputChange('project_name')}
                required
                InputProps={{
                  startAdornment: <AccountBalance sx={{ color: 'action.active', mr: 1 }} />,
                }}
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Company Name"
                value={formData.company_name}
                onChange={handleInputChange('company_name')}
                required
                InputProps={{
                  startAdornment: <Business sx={{ color: 'action.active', mr: 1 }} />,
                }}
              />
            </Grid>


            {/* Invitation Section */}
            <Grid item xs={12}>
              <Divider sx={{ my: 2 }} />
              <Typography variant="h6" gutterBottom>
                Invite People (Optional)
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Invite up to 5 people to join this project. They will receive an email with a link to create their account.
              </Typography>
            </Grid>

            <Grid item xs={12} md={8}>
              <Typography variant="subtitle2" gutterBottom>
                Email Addresses
              </Typography>
              {formData.invite_emails.map((email, index) => (
                <Box key={index} sx={{ display: 'flex', mb: 1, alignItems: 'center' }}>
                  <TextField
                    fullWidth
                    type="email"
                    label={`Email ${index + 1}`}
                    value={email}
                    onChange={(e) => handleEmailChange(index, e.target.value)}
                    placeholder="startup@example.com"
                    InputProps={{
                      startAdornment: <Email sx={{ color: 'action.active', mr: 1 }} />,
                    }}
                  />
                  {formData.invite_emails.length > 1 && (
                    <IconButton 
                      onClick={() => removeEmailField(index)}
                      color="error"
                      sx={{ ml: 1 }}
                    >
                      <Delete />
                    </IconButton>
                  )}
                </Box>
              ))}
              
              {formData.invite_emails.length < 5 && (
                <Button
                  variant="outlined"
                  startIcon={<Add />}
                  onClick={addEmailField}
                  sx={{ mt: 1 }}
                >
                  Add Another Email
                </Button>
              )}
            </Grid>

            <Grid item xs={12} md={4}>
              <FormControl fullWidth>
                <InputLabel>Invitation Language</InputLabel>
                <Select
                  value={formData.invitation_language}
                  onChange={handleInputChange('invitation_language')}
                  label="Invitation Language"
                >
                  <MenuItem value="en">English</MenuItem>
                  <MenuItem value="de">Deutsch</MenuItem>
                </Select>
              </FormControl>
            </Grid>
          </Grid>
        </form>
      </DialogContent>

      <DialogActions>
        <Button onClick={handleClose} disabled={submitting}>
          Cancel
        </Button>
        <Button
          onClick={handleSubmit}
          variant="contained"
          disabled={submitting}
          sx={{ minWidth: 120 }}
        >
          {submitting ? 'Creating...' : 'Create Project'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default CreateProjectDialog;