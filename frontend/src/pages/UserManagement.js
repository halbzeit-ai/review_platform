import React, { useState, useEffect } from 'react';
import { Container, Typography, Grid, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Button, IconButton, Box, Snackbar, Alert, Dialog, DialogActions, DialogContent, DialogTitle, TextField } from '@mui/material';
import { Delete as DeleteIcon, People, PersonAdd } from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { getAllUsers, updateUserRole, deleteUser, inviteGP, getPendingInvitations, cancelInvitation } from '../services/api';
import ConfirmDialog from '../components/ConfirmDialog';

function UserManagement() {
  const { t } = useTranslation('dashboard');
  const navigate = useNavigate();
  const [users, setUsers] = useState([]);
  const [pendingInvitations, setPendingInvitations] = useState([]);
  const [deleteDialog, setDeleteDialog] = useState({ open: false, user: null });
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' });
  const [inviteDialog, setInviteDialog] = useState({ open: false });
  const [inviteForm, setInviteForm] = useState({ email: '', name: '', preferred_language: 'de' });
  const [inviteLoading, setInviteLoading] = useState(false);

  const handleRoleChange = async (userEmail, newRole) => {
    try {
      await updateUserRole(userEmail, newRole);
      // Update local state to reflect the change
      setUsers(users.map(user => 
        user.email === userEmail ? { ...user, role: newRole } : user
      ));
    } catch (error) {
      console.error('Error updating role:', error);
      alert(`${t('gp.usersSection.actions.changeRole')} ${t('common:messages.error')}: ${error.response?.data?.detail || t('common:messages.connectionError')}`);
    }
  };

  const handleDeleteUser = (user) => {
    setDeleteDialog({ open: true, user });
  };

  const refreshUsers = async () => {
    try {
      const response = await getAllUsers();
      if (response.data) {
        setUsers(response.data);
      }
    } catch (error) {
      console.error('Failed to refresh users:', error);
    }
  };

  const refreshPendingInvitations = async () => {
    try {
      const response = await getPendingInvitations();
      if (response.data) {
        setPendingInvitations(response.data);
      }
    } catch (error) {
      console.error('Failed to refresh pending invitations:', error);
    }
  };

  const handleCancelInvitation = async (invitationId) => {
    try {
      await cancelInvitation(invitationId);
      setSnackbar({
        open: true,
        message: 'Invitation cancelled successfully',
        severity: 'success'
      });
      // Refresh pending invitations list
      await refreshPendingInvitations();
    } catch (error) {
      console.error('Error cancelling invitation:', error);
      setSnackbar({
        open: true,
        message: error.response?.data?.detail || 'Failed to cancel invitation',
        severity: 'error'
      });
    }
  };

  const confirmDeleteUser = async () => {
    const userToDelete = deleteDialog.user;
    if (!userToDelete) return;

    try {
      await deleteUser(userToDelete.email);
      
      // Show success message
      setSnackbar({
        open: true,
        message: t('gp.usersSection.deleteConfirm.success'),
        severity: 'success'
      });
      
      // Refresh the user list to ensure UI is in sync
      await refreshUsers();
    } catch (error) {
      console.error('Error deleting user:', error);
      console.error('Full error response:', error.response);
      
      let errorMessage = t('gp.usersSection.deleteConfirm.error');
      if (error.response?.status === 404) {
        errorMessage = `${t('gp.usersSection.deleteConfirm.error')}: ${error.response.data.detail}`;
      } else if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      }
      
      setSnackbar({
        open: true,
        message: errorMessage,
        severity: 'error'
      });
      
      // Always refresh the user list after error to ensure UI consistency
      await refreshUsers();
    } finally {
      setDeleteDialog({ open: false, user: null });
    }
  };

  const handleInviteGP = async () => {
    if (!inviteForm.email || !inviteForm.name) {
      setSnackbar({
        open: true,
        message: 'Please fill in all required fields',
        severity: 'error'
      });
      return;
    }

    setInviteLoading(true);
    try {
      const response = await inviteGP(inviteForm);
      setSnackbar({
        open: true,
        message: 'GP invitation sent successfully!',
        severity: 'success'
      });
      setInviteDialog({ open: false });
      setInviteForm({ email: '', name: '', preferred_language: 'de' });
      // Refresh the user list
      await refreshUsers();
    } catch (error) {
      console.error('Error inviting GP:', error);
      let errorMessage = 'Failed to send invitation';
      if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      }
      setSnackbar({
        open: true,
        message: errorMessage,
        severity: 'error'
      });
    } finally {
      setInviteLoading(false);
    }
  };

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch both users and pending invitations
        const [usersResponse, invitationsResponse] = await Promise.all([
          getAllUsers(),
          getPendingInvitations()
        ]);
        
        if (usersResponse.data) {
          setUsers(usersResponse.data);
        } else {
          console.error('No user data received');
        }
        
        if (invitationsResponse.data) {
          setPendingInvitations(invitationsResponse.data);
        }
        
      } catch (error) {
        console.error('Failed to fetch data:', error);
        alert(t('common:messages.connectionError'));
      }
    };
    fetchData();
  }, []);

  return (
    <Container maxWidth="lg" sx={{ mt: 4 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">
          <People sx={{ mr: 1, verticalAlign: 'middle' }} />
          {t('gp.usersSection.title')}
        </Typography>
        <Button
          variant="outlined"
          onClick={() => navigate('/gp-dashboard')}
        >
          Back to Dashboard
        </Button>
      </Box>
      
      <Grid container spacing={3}>
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
              <Typography variant="h6" gutterBottom>{t('gp.usersSection.title')}</Typography>
              <Button
                variant="contained"
                startIcon={<PersonAdd />}
                onClick={() => setInviteDialog({ open: true })}
              >
                Invite GP
              </Button>
            </Box>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>{t('gp.usersSection.columns.email')}</TableCell>
                    <TableCell>{t('gp.usersSection.columns.company')}</TableCell>
                    <TableCell>{t('gp.usersSection.columns.role')}</TableCell>
                    <TableCell>{t('gp.usersSection.columns.lastLogin')}</TableCell>
                    <TableCell>{t('gp.usersSection.columns.actions')}</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {users.map((user) => (
                    <TableRow key={user.email}>
                      <TableCell>{user.email}</TableCell>
                      <TableCell>{user.company_name}</TableCell>
                      <TableCell>
                        <Button
                          variant="outlined"
                          size="small"
                          onClick={() => handleRoleChange(user.email, user.role === 'startup' ? 'gp' : 'startup')}
                          disabled={user.email.toLowerCase() === 'ramin@halbzeit.ai'}
                        >
                          {user.role.toUpperCase()} {user.email.toLowerCase() === 'ramin@halbzeit.ai' ? '(Protected)' : `(${t('gp.usersSection.actions.changeRole')})`}
                        </Button>
                      </TableCell>
                      <TableCell>{user.last_login ? new Date(user.last_login).toLocaleString('de-DE', { timeZone: 'Europe/Berlin' }) : t('common:messages.never')}</TableCell>
                      <TableCell>
                        <Box sx={{ display: 'flex', gap: 1 }}>
                          <IconButton
                            color="error"
                            size="small"
                            onClick={() => handleDeleteUser(user)}
                            title={t('gp.usersSection.actions.delete')}
                            disabled={user.email.toLowerCase() === 'ramin@halbzeit.ai'}
                          >
                            <DeleteIcon />
                          </IconButton>
                        </Box>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Paper>
        </Grid>
        
        {/* Pending Invitations Section */}
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Pending Project Invitations ({pendingInvitations.length})
            </Typography>
            {pendingInvitations.length === 0 ? (
              <Typography color="text.secondary" sx={{ py: 2 }}>
                No pending invitations
              </Typography>
            ) : (
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Email</TableCell>
                      <TableCell>Project</TableCell>
                      <TableCell>Company</TableCell>
                      <TableCell>Invited</TableCell>
                      <TableCell>Expires</TableCell>
                      <TableCell>Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {pendingInvitations.map((invitation) => (
                      <TableRow key={invitation.id}>
                        <TableCell>{invitation.email}</TableCell>
                        <TableCell>{invitation.project_name}</TableCell>
                        <TableCell>{invitation.company_id}</TableCell>
                        <TableCell>
                          {new Date(invitation.created_at).toLocaleDateString()}
                        </TableCell>
                        <TableCell>
                          <Typography 
                            color={new Date(invitation.expires_at) < new Date() ? 'error' : 'inherit'}
                            variant="body2"
                          >
                            {new Date(invitation.expires_at).toLocaleDateString()}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Box display="flex" gap={1}>
                            <Button
                              size="small"
                              variant="outlined"
                              color="error"
                              onClick={() => handleCancelInvitation(invitation.id)}
                            >
                              Cancel
                            </Button>
                          </Box>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </Paper>
        </Grid>
      </Grid>

      {/* Delete User Confirmation Dialog */}
      <ConfirmDialog
        open={deleteDialog.open}
        onClose={() => setDeleteDialog({ open: false, user: null })}
        onConfirm={confirmDeleteUser}
        title={t('gp.usersSection.deleteConfirm.title')}
        message={`${t('gp.usersSection.deleteConfirm.message').replace('{email}', deleteDialog.user?.email || '')}

${t('gp.cascadeDeletion.warning')}`}
        confirmText={t('gp.usersSection.deleteConfirm.confirmButton')}
        cancelText={t('gp.usersSection.deleteConfirm.cancelButton')}
        severity="error"
      />

      {/* Success/Error Snackbar */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert
          onClose={() => setSnackbar({ ...snackbar, open: false })}
          severity={snackbar.severity}
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>

      {/* Invite GP Dialog */}
      <Dialog
        open={inviteDialog.open}
        onClose={() => setInviteDialog({ open: false })}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Invite New GP</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              label="Email Address"
              type="email"
              fullWidth
              value={inviteForm.email}
              onChange={(e) => setInviteForm({ ...inviteForm, email: e.target.value })}
              required
            />
            <TextField
              label="Full Name"
              fullWidth
              value={inviteForm.name}
              onChange={(e) => setInviteForm({ ...inviteForm, name: e.target.value })}
              required
            />
            <TextField
              label="Language Preference"
              select
              fullWidth
              value={inviteForm.preferred_language}
              onChange={(e) => setInviteForm({ ...inviteForm, preferred_language: e.target.value })}
              SelectProps={{ native: true }}
            >
              <option value="de">Deutsch</option>
              <option value="en">English</option>
            </TextField>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setInviteDialog({ open: false })} disabled={inviteLoading}>
            Cancel
          </Button>
          <Button
            onClick={handleInviteGP}
            variant="contained"
            disabled={inviteLoading}
          >
            {inviteLoading ? 'Sending...' : 'Send Invitation'}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
}

export default UserManagement;