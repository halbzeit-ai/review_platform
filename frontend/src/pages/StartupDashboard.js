
import React, { useState, useEffect } from 'react';
import { Container, Paper, Typography, Button, Grid, Alert, CircularProgress, List, ListItem, ListItemText, Divider, Chip } from '@mui/material';
import { Upload, CheckCircle, Pending, Error } from '@mui/icons-material';
import { uploadPitchDeck, getPitchDecks } from '../services/api';

function StartupDashboard() {
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [pitchDecks, setPitchDecks] = useState([]);
  const [loading, setLoading] = useState(true);

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setUploading(true);
    setUploadStatus(null);

    try {
      const response = await uploadPitchDeck(file);
      setUploadStatus({ type: 'success', message: 'Pitch deck uploaded successfully!' });
      // Refresh the pitch decks list
      fetchPitchDecks();
    } catch (error) {
      setUploadStatus({ 
        type: 'error', 
        message: error.response?.data?.detail || 'Upload failed. Please try again.' 
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
        return 'success';
      case 'processing':
        return 'primary';
      case 'failed':
        return 'error';
      default:
        return 'default';
    }
  };

  useEffect(() => {
    fetchPitchDecks();
  }, []);

  return (
    <Container maxWidth="lg" sx={{ mt: 4 }}>
      <Typography variant="h4" gutterBottom>Dashboard</Typography>
      <Grid container spacing={3}>
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
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
                {uploading ? 'Uploading...' : 'Upload Pitch Deck'}
              </Button>
            </label>
          </Paper>
        </Grid>
        
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>Your Uploaded Pitch Decks</Typography>
            {loading ? (
              <CircularProgress />
            ) : pitchDecks.length === 0 ? (
              <Typography color="text.secondary">No pitch decks uploaded yet.</Typography>
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
                              label={deck.processing_status || 'pending'}
                              color={getStatusColor(deck.processing_status)}
                              size="small"
                            />
                          </div>
                        }
                        secondary={`Uploaded on ${new Date(deck.created_at).toLocaleDateString()}`}
                      />
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
