
import React, { useState, useEffect } from 'react';
import { Container, Paper, Typography, Button, Grid, Alert, CircularProgress, List, ListItem, ListItemText, Divider, Chip, Box, Card, CardContent } from '@mui/material';
import { Upload, CheckCircle, Pending, Error, Visibility, Schedule, Folder, Timeline, Psychology, Business, AttachMoney, DateRange, Category } from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { uploadPitchDeck, getPitchDecks, getExtractionResults } from '../services/api';

function StartupDashboard() {
  const { t } = useTranslation('dashboard');
  const navigate = useNavigate();
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [pitchDecks, setPitchDecks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [extractionResults, setExtractionResults] = useState([]);
  const [extractionLoading, setExtractionLoading] = useState(true);

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

  const fetchExtractionResults = async () => {
    try {
      console.log('Fetching extraction results...');
      const response = await getExtractionResults();
      console.log('Extraction results response:', response.data);
      setExtractionResults(response.data);
    } catch (error) {
      console.error('Error fetching extraction results:', error);
    } finally {
      setExtractionLoading(false);
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
        return t('startup.decksSection.status.completed');
      case 'reviewed':
        return t('startup.decksSection.status.reviewed');
      case 'processing':
        return t('startup.decksSection.status.processing');
      case 'failed':
        return t('startup.decksSection.status.failed');
      case 'pending':
        return t('startup.decksSection.status.pending');
      case 'uploaded':
        return t('startup.decksSection.status.uploaded');
      default:
        return t('startup.decksSection.status.uploaded');
    }
  };

  const handleViewResults = (deckId) => {
    navigate(`/results/${deckId}`);
  };

  const getCompanyId = () => {
    const user = JSON.parse(localStorage.getItem('user'));
    if (user?.companyName) {
      // Convert company name to a URL-safe slug (same logic as backend)
      return user.companyName.toLowerCase().replace(' ', '-').replace(/[^a-z0-9-]/g, '');
    }
    // Fallback to email prefix if company name is not available
    return user?.email?.split('@')[0] || 'unknown';
  };

  const handleViewProject = () => {
    const companyId = getCompanyId();
    navigate(`/project/${companyId}`);
  };

  const handleViewFundingJourney = () => {
    navigate('/funding-journey');
  };

  // Check if there are any decks currently processing
  const hasProcessingDecks = pitchDecks.some(deck => 
    deck.processing_status === 'processing' || deck.processing_status === 'pending'
  );

  useEffect(() => {
    fetchPitchDecks();
    fetchExtractionResults();
    
    // Adaptive polling - faster when processing, slower when idle
    const interval = setInterval(() => {
      fetchPitchDecks();
      fetchExtractionResults();
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

        {/* Project Dashboard and Funding Journey Links */}
        <Grid item xs={12}>
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <Paper sx={{ p: 3, h: 1 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: '100%' }}>
                  <Box>
                    <Typography variant="h6" gutterBottom>
                      Project Dashboard
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      View all your decks, slide-by-slide analysis, and project files.
                    </Typography>
                  </Box>
                  <Button
                    variant="outlined"
                    startIcon={<Folder />}
                    onClick={handleViewProject}
                    size="large"
                  >
                    View Project
                  </Button>
                </Box>
              </Paper>
            </Grid>
            <Grid item xs={12} md={6}>
              <Paper sx={{ p: 3, h: 1 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: '100%' }}>
                  <Box>
                    <Typography variant="h6" gutterBottom>
                      Funding Journey
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Track your progress through the 14-stage funding process.
                    </Typography>
                  </Box>
                  <Button
                    variant="contained"
                    startIcon={<Timeline />}
                    onClick={handleViewFundingJourney}
                    size="large"
                  >
                    View Journey
                  </Button>
                </Box>
              </Paper>
            </Grid>
          </Grid>
        </Grid>

        {/* Extraction Results Display */}
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              <Psychology sx={{ mr: 1, verticalAlign: 'middle' }} />
              AI Extraction Results
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Key information extracted from your pitch decks by our AI analysis.
            </Typography>
            
            {extractionLoading ? (
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <CircularProgress size={16} />
                <Typography variant="body2" color="text.secondary">Loading extraction results...</Typography>
              </Box>
            ) : extractionResults.length === 0 ? (
              <Alert severity="info" sx={{ mb: 2 }}>
                No extraction results available yet. Upload and analyze a deck to see extracted information.
              </Alert>
            ) : (
              <Grid container spacing={2}>
                {extractionResults.map((result, index) => (
                  <Grid item xs={12} md={6} key={index}>
                    <Card variant="outlined">
                      <CardContent>
                        <Typography variant="subtitle1" gutterBottom sx={{ fontWeight: 'bold' }}>
                          {result.deck_name}
                        </Typography>
                        
                        {result.company_name && (
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                            <Business sx={{ fontSize: 16, color: 'primary.main' }} />
                            <Typography variant="body2">
                              <strong>Company:</strong> {result.company_name}
                            </Typography>
                          </Box>
                        )}
                        
                        {result.classification && (
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                            <Category sx={{ fontSize: 16, color: 'secondary.main' }} />
                            <Typography variant="body2">
                              <strong>Sector:</strong> {result.classification}
                            </Typography>
                          </Box>
                        )}
                        
                        {result.funding_amount && (
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                            <AttachMoney sx={{ fontSize: 16, color: 'success.main' }} />
                            <Typography variant="body2">
                              <strong>Funding:</strong> {result.funding_amount}
                            </Typography>
                          </Box>
                        )}
                        
                        {result.deck_date && (
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                            <DateRange sx={{ fontSize: 16, color: 'info.main' }} />
                            <Typography variant="body2">
                              <strong>Date:</strong> {result.deck_date}
                            </Typography>
                          </Box>
                        )}
                        
                        {result.company_offering && (
                          <Box sx={{ mt: 2 }}>
                            <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                              Company Offering:
                            </Typography>
                            <Typography variant="body2" color="text.secondary" sx={{ 
                              maxHeight: 100, 
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              display: '-webkit-box',
                              WebkitLineClamp: 4,
                              WebkitBoxOrient: 'vertical'
                            }}>
                              {result.company_offering}
                            </Typography>
                          </Box>
                        )}
                        
                        {result.extracted_at && (
                          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
                            Extracted: {new Date(result.extracted_at).toLocaleDateString()}
                          </Typography>
                        )}
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            )}
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
                      {(deck.processing_status === 'completed' || deck.visual_analysis_completed) && (
                        <Button
                          variant="outlined"
                          size="small"
                          startIcon={<Visibility />}
                          onClick={() => handleViewResults(deck.id)}
                          sx={{ ml: 1 }}
                        >
                          {deck.processing_status === 'completed' ? t('startup.decksSection.viewResults') : 'View Deck'}
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
