
import React, { useState, useEffect } from 'react';
import { Container, Paper, Typography, Button, Grid, Alert, CircularProgress, List, ListItem, ListItemText, Divider, Chip, Dialog, DialogTitle, DialogContent, DialogActions, IconButton, Box } from '@mui/material';
import { Upload, CheckCircle, Pending, Error, Visibility, Close } from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import { uploadPitchDeck, getPitchDecks } from '../services/api';
import ReviewResults from '../components/ReviewResults';

function StartupDashboard() {
  const { t } = useTranslation('dashboard');
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [pitchDecks, setPitchDecks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedDeckId, setSelectedDeckId] = useState(null);
  const [showResults, setShowResults] = useState(false);

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    // Check file size (50MB limit)
    const maxSize = 50 * 1024 * 1024; // 50MB in bytes
    if (file.size > maxSize) {
      setUploadStatus({ 
        type: 'error', 
        message: `${t('startup.uploadSection.errors.fileTooLarge')}. ${t('startup.uploadSection.maxSize')}. Your file is ${(file.size / (1024 * 1024)).toFixed(1)}MB.` 
      });
      event.target.value = '';
      return;
    }

    // Check file type
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setUploadStatus({ 
        type: 'error', 
        message: t('startup.uploadSection.errors.invalidType') 
      });
      event.target.value = '';
      return;
    }

    setUploading(true);
    setUploadStatus(null);

    try {
      const response = await uploadPitchDeck(file);
      setUploadStatus({ type: 'success', message: t('startup.uploadSection.success') });
      // Refresh the pitch decks list
      fetchPitchDecks();
    } catch (error) {
      let errorMessage = t('startup.uploadSection.errors.uploadFailed');
      
      // Handle specific error cases
      if (error.response?.status === 413) {
        errorMessage = t('startup.uploadSection.errors.fileTooLarge');
      } else if (error.response?.status === 400) {
        errorMessage = error.response.data?.detail || t('startup.uploadSection.errors.invalidType');
      } else if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      }
      
      setUploadStatus({ 
        type: 'error', 
        message: errorMessage
      });
    } finally {
      setUploading(false);
      // Reset file input
      event.target.value = '';
    }
  };

  const fetchPitchDecks = async () => {
    try {
      const response = await getPitchDecks();
      setPitchDecks(response.data.decks);
    } catch (error) {
      console.error('Error fetching pitch decks:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed':
      case 'reviewed':
        return <CheckCircle color="success" />;
      case 'processing':
        return <CircularProgress size={20} />;
      case 'failed':
        return <Error color="error" />;
      default:
        return <Pending color="action" />;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed':
      case 'reviewed':
        return 'success';
      case 'processing':
        return 'primary';
      case 'failed':
        return 'error';
      default:
        return 'default';
    }
  };

  const getStatusLabel = (status) => {
    switch (status) {
      case 'completed':
      case 'reviewed':
        return t('startup.decksSection.status.reviewed');
      case 'processing':
        return t('startup.decksSection.status.processing');
      case 'failed':
        return t('startup.decksSection.status.failed');
      case 'uploaded':
        return t('startup.decksSection.status.uploaded');
      default:
        return t('startup.decksSection.status.uploaded');
    }
  };

  const handleViewResults = (deckId) => {
    setSelectedDeckId(deckId);
    setShowResults(true);
  };

  const handleCloseResults = () => {
    setShowResults(false);
    setSelectedDeckId(null);
  };

  useEffect(() => {
    fetchPitchDecks();
  }, []);

  return (
    <Container maxWidth="lg" sx={{ mt: 4 }}>
      <Typography variant="h4" gutterBottom>{t('startup.title')}</Typography>
      <Grid container spacing={3}>
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>{t('startup.uploadSection.title')}</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              {t('startup.uploadSection.description')}. {t('startup.uploadSection.maxSize')}.
            </Typography>
            {uploadStatus && (
              <Alert severity={uploadStatus.type} sx={{ mb: 2 }}>
                {uploadStatus.message}
              </Alert>
            )}
            <input
              accept="application/pdf"
              style={{ display: 'none' }}
              id="pitch-deck-upload"
              type="file"
              onChange={handleFileUpload}
              disabled={uploading}
            />
            <label htmlFor="pitch-deck-upload">
              <Button
                variant="contained"
                component="span"
                startIcon={uploading ? <CircularProgress size={20} /> : <Upload />}
                disabled={uploading}
              >
                {uploading ? t('startup.uploadSection.uploading') : t('startup.uploadSection.title')}
              </Button>
            </label>
          </Paper>
        </Grid>
        
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>{t('startup.decksSection.title')}</Typography>
            {loading ? (
              <CircularProgress />
            ) : pitchDecks.length === 0 ? (
              <Typography color="text.secondary">{t('startup.decksSection.noDecks')}.</Typography>
            ) : (
              <List>
                {pitchDecks.map((deck, index) => (
                  <React.Fragment key={deck.id}>
                    <ListItem>
                      <ListItemText
                        primary={
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            {deck.file_name}
                            <Chip
                              icon={getStatusIcon(deck.processing_status)}
                              label={getStatusLabel(deck.processing_status)}
                              color={getStatusColor(deck.processing_status)}
                              size="small"
                            />
                          </div>
                        }
                        secondary={`${t('startup.decksSection.columns.uploadDate')}: ${new Date(deck.created_at).toLocaleDateString()}`}
                      />
                      {deck.processing_status === 'completed' && (
                        <Button
                          variant="outlined"
                          size="small"
                          startIcon={<Visibility />}
                          onClick={() => handleViewResults(deck.id)}
                          sx={{ ml: 1 }}
                        >
                          {t('startup.decksSection.viewResults')}
                        </Button>
                      )}
                    </ListItem>
                    {index < pitchDecks.length - 1 && <Divider />}
                  </React.Fragment>
                ))}
              </List>
            )}
          </Paper>
        </Grid>
      </Grid>

      {/* Results Dialog */}
      <Dialog
        open={showResults}
        onClose={handleCloseResults}
        maxWidth="lg"
        fullWidth
        PaperProps={{
          sx: { minHeight: '80vh' }
        }}
      >
        <DialogTitle>
          <Box display="flex" alignItems="center" justifyContent="space-between">
            <Typography variant="h6">{t('startup.decksSection.reviewResults')}</Typography>
            <IconButton onClick={handleCloseResults}>
              <Close />
            </IconButton>
          </Box>
        </DialogTitle>
        <DialogContent>
          {selectedDeckId && (
            <ReviewResults
              pitchDeckId={selectedDeckId}
              onClose={handleCloseResults}
            />
          )}
        </DialogContent>
      </Dialog>
    </Container>
  );
}

export default StartupDashboard;
