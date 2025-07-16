
import React, { useState, useEffect } from 'react';
import { Container, Paper, Typography, Button, Grid, Alert, CircularProgress, List, ListItem, ListItemText, Divider, Chip, Box } from '@mui/material';
import { Upload, CheckCircle, Pending, Error, Visibility, Schedule } from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { uploadPitchDeck, getPitchDecks } from '../services/api';

function StartupDashboard() {
  const { t } = useTranslation('dashboard');
  const navigate = useNavigate();
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [pitchDecks, setPitchDecks] = useState([]);
  const [loading, setLoading] = useState(true);

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
      
      // Immediately add the deck to the list for better UX
      if (response.data && response.data.pitch_deck_id) {
        const newDeck = {
          id: response.data.pitch_deck_id,
          file_name: response.data.filename,
          processing_status: response.data.processing_status || 'processing',
          created_at: new Date().toISOString(),
          user_id: null // Will be filled by next fetch
        };
        setPitchDecks(prev => [newDeck, ...prev]);
      }
      
      // Also refresh the pitch decks list
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
      console.log('Fetching pitch decks...');
      const response = await getPitchDecks();
      console.log('Pitch decks response:', response.data.decks);
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
        return <CheckCircle />;
      case 'processing':
        return <CircularProgress size={16} />;
      case 'failed':
        return <Error />;
      case 'pending':
        return <Schedule />;
      default:
        return <Pending />;
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
      case 'pending':
        return 'warning';
      default:
        return 'default';
    }
  };

  const getStatusLabel = (status) => {
    switch (status) {
      case 'completed':
      case 'reviewed':
        return 'Bewertet';
      case 'processing':
        return 'Wird analysiert...';
      case 'failed':
        return 'Fehlgeschlagen';
      case 'pending':
        return 'Warte auf Verarbeitung';
      case 'uploaded':
        return 'Hochgeladen';
      default:
        return 'Hochgeladen';
    }
  };

  const handleViewResults = (deckId) => {
    navigate(`/results/${deckId}`);
  };

  // Check if there are any decks currently processing
  const hasProcessingDecks = pitchDecks.some(deck => 
    deck.processing_status === 'processing' || deck.processing_status === 'pending'
  );

  useEffect(() => {
    fetchPitchDecks();
    
    // Adaptive polling - faster when processing, slower when idle
    const interval = setInterval(() => {
      fetchPitchDecks();
    }, hasProcessingDecks ? 2000 : 10000); // 2s when processing, 10s when idle
    
    return () => clearInterval(interval);
  }, [hasProcessingDecks]);

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
    </Container>
  );
}

export default StartupDashboard;
