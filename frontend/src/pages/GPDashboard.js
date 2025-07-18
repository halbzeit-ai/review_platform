import React, { useState, useEffect } from 'react';
import { Container, Typography, Grid, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Button, CircularProgress, IconButton, Box, Snackbar, Alert } from '@mui/material';
import { Delete as DeleteIcon, Settings, Assignment, CleaningServices, Storage } from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { getAllUsers, getPitchDecks, updateUserRole, deleteUser, cleanupOrphanedDecks } from '../services/api';
import ConfirmDialog from '../components/ConfirmDialog';

function GPDashboard() {
  const { t } = useTranslation('dashboard');
  const navigate = useNavigate();
  const [users, setUsers] = useState([]);
  const [pitchDecks, setPitchDecks] = useState([]);
  const [loadingDecks, setLoadingDecks] = useState(true);
  const [deleteDialog, setDeleteDialog] = useState({ open: false, user: null });
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' });
  const [cleanupLoading, setCleanupLoading] = useState(false);

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

  const fetchPitchDecks = async () => {
    try {
      const response = await getPitchDecks();
      setPitchDecks(response.data.decks);
    } catch (error) {
      console.error('Error fetching pitch decks:', error);
    } finally {
      setLoadingDecks(false);
    }
  };

  const handleCleanupOrphanedDecks = async () => {
    setCleanupLoading(true);
    try {
      const response = await cleanupOrphanedDecks();
      
      setSnackbar({
        open: true,
        message: response.data.message || t('gp.adminActions.cleanupSuccess'),
        severity: 'success'
      });
      
      // Refresh the decks list
      await fetchPitchDecks();
      
    } catch (error) {
      console.error('Error cleaning up orphaned decks:', error);
      
      setSnackbar({
        open: true,
        message: `${t('gp.adminActions.cleanupError')}: ${error.response?.data?.detail || error.message}`,
        severity: 'error'
      });
    } finally {
      setCleanupLoading(false);
    }
  };

  useEffect(() => {
    const fetchUsers = async () => {
      try {
        const response = await getAllUsers();
        if (response.data) {
          setUsers(response.data);
        } else {
          console.error('No user data received');
        }
      } catch (error) {
        console.error('Failed to fetch users:', error);
        alert(t('common:messages.connectionError'));
      }
    };
    fetchUsers();
    fetchPitchDecks();
  }, []);

  return (
    <Container maxWidth="lg" sx={{ mt: 4 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">{t('gp.title')}</Typography>
        <Box display="flex" gap={2}>
          <Button
            variant="outlined"
            startIcon={<Assignment />}
            onClick={() => navigate('/templates')}
          >
            {t('gp.adminActions.analysisTemplates')}
          </Button>
          <Button
            variant="outlined"
            startIcon={<Storage />}
            onClick={() => navigate('/dojo')}
          >
            {t('gp.adminActions.dojo')}
          </Button>
          <Button
            variant="outlined"
            startIcon={<Settings />}
            onClick={() => navigate('/config')}
          >
            {t('gp.adminActions.modelConfiguration')}
          </Button>
          <Button
            variant="outlined"
            startIcon={<CleaningServices />}
            onClick={handleCleanupOrphanedDecks}
            disabled={cleanupLoading}
          >
            {cleanupLoading ? t('gp.adminActions.cleanupInProgress') : t('gp.adminActions.cleanupOrphanedData')}
          </Button>
        </Box>
      </Box>
      <Grid container spacing={3}>
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>{t('gp.reviewsSection.title')}</Typography>
            {loadingDecks ? (
              <CircularProgress />
            ) : pitchDecks.length === 0 ? (
              <Typography color="text.secondary">{t('gp.reviewsSection.noReviews')}</Typography>
            ) : (
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>{t('gp.reviewsSection.columns.deck')}</TableCell>
                      <TableCell>{t('gp.reviewsSection.columns.company')}</TableCell>
                      <TableCell>{t('common:forms.email')}</TableCell>
                      <TableCell>{t('gp.reviewsSection.columns.date')}</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {pitchDecks.map((deck) => (
                      <TableRow key={deck.id}>
                        <TableCell>{deck.file_name}</TableCell>
                        <TableCell>{deck.user?.company_name || 'N/A'}</TableCell>
                        <TableCell>{deck.user?.email || 'N/A'}</TableCell>
                        <TableCell>{new Date(deck.created_at).toLocaleDateString()}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </Paper>
        </Grid>
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>{t('gp.usersSection.title')}</Typography>
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
                        >
                          {user.role.toUpperCase()} ({t('gp.usersSection.actions.changeRole')})
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
    </Container>
  );
}

export default GPDashboard;