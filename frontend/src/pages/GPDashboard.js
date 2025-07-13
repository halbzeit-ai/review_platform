import React, { useState, useEffect } from 'react';
import { Container, Typography, Grid, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Button, CircularProgress } from '@mui/material';
import { useTranslation } from 'react-i18next';
import { getAllUsers, getPitchDecks, updateUserRole } from '../services/api';

function GPDashboard() {
  const { t } = useTranslation('dashboard');
  const [users, setUsers] = useState([]);
  const [pitchDecks, setPitchDecks] = useState([]);
  const [loadingDecks, setLoadingDecks] = useState(true);

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
      <Typography variant="h4" gutterBottom>{t('gp.title')}</Typography>
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
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Paper>
        </Grid>
      </Grid>
    </Container>
  );
}

export default GPDashboard;