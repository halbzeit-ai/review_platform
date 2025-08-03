import React, { useState, useEffect } from 'react';
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
  Chip,
  IconButton,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Divider,
  CircularProgress,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Grid,
  Paper,
  Autocomplete
} from '@mui/material';
import {
  Add,
  Delete,
  Email,
  Person,
  Business,
  Send,
  Close,
  ContentCopy,
  CheckCircle,
  Cancel,
  AccessTime
} from '@mui/icons-material';
import { sendProjectInvitations, getProjectInvitations, cancelInvitation } from '../services/api';

const ProjectInvitationManager = ({ open, onClose, project }) => {
  const [emails, setEmails] = useState(['']);
  const [language, setLanguage] = useState('en');
  const [invitations, setInvitations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [activeTab, setActiveTab] = useState(0);

  useEffect(() => {
    if (open && project) {
      fetchInvitations();
    }
  }, [open, project]);

  const fetchInvitations = async () => {
    try {
      setLoading(true);
      const response = await getProjectInvitations(project.id);
      setInvitations(response.data);
    } catch (error) {
      console.error('Error fetching invitations:', error);
      setError('Failed to load invitations');
    } finally {
      setLoading(false);
    }
  };

  const handleEmailChange = (index, value) => {
    const newEmails = [...emails];
    newEmails[index] = value;
    setEmails(newEmails);
  };

  const addEmailField = () => {
    if (emails.length < 5) {
      setEmails([...emails, '']);
    }
  };

  const removeEmailField = (index) => {
    if (emails.length > 1) {
      setEmails(emails.filter((_, i) => i !== index));
    }
  };

  const validateEmails = () => {
    const validEmails = emails.filter(email => 
      email.trim() && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())
    );
    
    if (validEmails.length === 0) {
      setError('Please enter at least one valid email address');
      return false;
    }
    
    return validEmails;
  };

  const handleSendInvitations = async () => {
    const validEmails = validateEmails();
    if (!validEmails) return;

    setSubmitting(true);
    setError('');
    setSuccess('');

    try {
      const invitationData = {
        emails: validEmails,
        language: language
      };

      await sendProjectInvitations(project.id, invitationData);
      setSuccess(`Invitations sent successfully to ${validEmails.length} email(s)`);
      setEmails(['']);
      await fetchInvitations(); // Refresh the list
      
      setTimeout(() => setSuccess(''), 5000);
    } catch (error) {
      console.error('Error sending invitations:', error);
      setError(error.response?.data?.detail || 'Failed to send invitations');
    } finally {
      setSubmitting(false);
    }
  };

  const handleCancelInvitation = async (invitationId) => {
    try {
      await cancelInvitation(invitationId);
      setSuccess('Invitation cancelled successfully');
      await fetchInvitations();
      setTimeout(() => setSuccess(''), 3000);
    } catch (error) {
      console.error('Error cancelling invitation:', error);
      setError('Failed to cancel invitation');
    }
  };

  const copyInvitationLink = (token) => {
    const invitationUrl = `${window.location.origin}/invitation/${token}`;
    navigator.clipboard.writeText(invitationUrl);
    setSuccess('Invitation link copied to clipboard');
    setTimeout(() => setSuccess(''), 3000);
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'pending':
        return <AccessTime color="warning" />;
      case 'accepted':
        return <CheckCircle color="success" />;
      case 'expired':
        return <Cancel color="error" />;
      case 'cancelled':
        return <Cancel color="disabled" />;
      default:
        return <AccessTime color="disabled" />;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'pending':
        return 'warning';
      case 'accepted':
        return 'success';
      case 'expired':
        return 'error';
      case 'cancelled':
        return 'default';
      default:
        return 'default';
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Typography variant="h6">
            Manage Invitations: {project?.project_name}
          </Typography>
          <IconButton onClick={onClose}>
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

        <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
          <Box sx={{ display: 'flex', gap: 2 }}>
            <Button
              variant={activeTab === 0 ? 'contained' : 'text'}
              onClick={() => setActiveTab(0)}
              startIcon={<Send />}
            >
              Send Invitations
            </Button>
            <Button
              variant={activeTab === 1 ? 'contained' : 'text'}
              onClick={() => setActiveTab(1)}
              startIcon={<Person />}
            >
              Manage Invitations ({invitations.length})
            </Button>
          </Box>
        </Box>

        {activeTab === 0 && (
          <Box>
            <Typography variant="h6" gutterBottom>
              Invite Person to Your Project
            </Typography>
            
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              Send up to 5 invitations. Invited startups will receive an email with a link to create their account and join your project.
            </Typography>

            <Grid container spacing={2} sx={{ mb: 3 }}>
              <Grid item xs={12} md={8}>
                <Typography variant="subtitle2" gutterBottom>
                  Email Addresses
                </Typography>
                {emails.map((email, index) => (
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
                    {emails.length > 1 && (
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
                
                {emails.length < 5 && (
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
                  <InputLabel>Language</InputLabel>
                  <Select
                    value={language}
                    onChange={(e) => setLanguage(e.target.value)}
                    label="Language"
                  >
                    <MenuItem value="en">English</MenuItem>
                    <MenuItem value="de">Deutsch</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
            </Grid>

            <Button
              variant="contained"
              size="large"
              startIcon={submitting ? <CircularProgress size={20} /> : <Send />}
              onClick={handleSendInvitations}
              disabled={submitting}
              fullWidth
            >
              {submitting ? 'Sending Invitations...' : 'Send Invitations'}
            </Button>
          </Box>
        )}

        {activeTab === 1 && (
          <Box>
            <Typography variant="h6" gutterBottom>
              Project Invitations
            </Typography>

            {loading ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
                <CircularProgress />
              </Box>
            ) : invitations.length === 0 ? (
              <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', py: 3 }}>
                No invitations sent yet. Switch to "Send Invitations" tab to invite startups.
              </Typography>
            ) : (
              <List>
                {invitations.map((invitation, index) => (
                  <React.Fragment key={invitation.id}>
                    <ListItem>
                      <Box sx={{ display: 'flex', alignItems: 'center', mr: 2 }}>
                        {getStatusIcon(invitation.status)}
                      </Box>
                      <ListItemText
                        primary={invitation.email}
                        secondary={
                          <Box>
                            <Typography variant="body2" color="text.secondary">
                              Sent: {new Date(invitation.created_at).toLocaleDateString()}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                              Expires: {new Date(invitation.expires_at).toLocaleDateString()}
                            </Typography>
                          </Box>
                        }
                      />
                      <Box sx={{ display: 'flex', gap: 1 }}>
                        <Chip
                          label={invitation.status}
                          color={getStatusColor(invitation.status)}
                          size="small"
                        />
                        {invitation.status === 'pending' && (
                          <>
                            <IconButton
                              onClick={() => copyInvitationLink(invitation.invitation_token)}
                              title="Copy invitation link"
                              size="small"
                            >
                              <ContentCopy />
                            </IconButton>
                            <IconButton
                              onClick={() => handleCancelInvitation(invitation.id)}
                              title="Cancel invitation"
                              size="small"
                              color="error"
                            >
                              <Cancel />
                            </IconButton>
                          </>
                        )}
                      </Box>
                    </ListItem>
                    {index < invitations.length - 1 && <Divider />}
                  </React.Fragment>
                ))}
              </List>
            )}
          </Box>
        )}
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
};

export default ProjectInvitationManager;