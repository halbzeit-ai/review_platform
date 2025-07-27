import React, { useState, useEffect } from 'react';
import { Container, Typography, Grid, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Button, CircularProgress, Box, Snackbar, Alert } from '@mui/material';
import { Settings, Assignment, CleaningServices, Storage, People } from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { getPitchDecks, cleanupOrphanedDecks } from '../services/api';

function GPDashboard() {
  const { t } = useTranslation('dashboard');
  const navigate = useNavigate();
  const [pitchDecks, setPitchDecks] = useState([]);
  const [loadingDecks, setLoadingDecks] = useState(true);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' });
  const [cleanupLoading, setCleanupLoading] = useState(false);


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
    fetchPitchDecks();
  }, []);

  return (
    <Container maxWidth="lg" sx={{ mt: 4 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">{t('gp.title')}</Typography>
        <Box display="flex" gap={2}>
          <Button
            variant="outlined"
            startIcon={<People />}
            onClick={() => navigate('/users')}
          >
            Manage Users
          </Button>
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
      </Grid>


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