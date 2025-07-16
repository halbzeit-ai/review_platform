import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Tabs,
  Tab,
  Grid,
  Card,
  CardContent,
  CardActions,
  Button,
  Breadcrumbs,
  Link,
  Alert,
  CircularProgress,
  Chip,
  Divider
} from '@mui/material';
import {
  Visibility as VisibilityIcon,
  Assessment as AssessmentIcon,
  Upload as UploadIcon,
  ArrowBack as ArrowBackIcon
} from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';

import { 
  getProjectDeckAnalysis,
  getProjectResults,
  getProjectUploads,
  getPitchDecks
} from '../services/api';

const ProjectDashboard = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { companyId } = useParams();
  
  const [activeTab, setActiveTab] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Project data
  const [projectDecks, setProjectDecks] = useState([]);
  const [uploads, setUploads] = useState([]);
  const [selectedDeck, setSelectedDeck] = useState(null);
  
  const [breadcrumbs, setBreadcrumbs] = useState([
    { label: t('navigation.dashboard'), path: '/dashboard' },
    { label: 'Project Dashboard', path: null }
  ]);

  useEffect(() => {
    loadProjectData();
  }, [companyId]);

  const loadProjectData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Load project decks and uploads
      const [decksResponse, uploadsResponse] = await Promise.all([
        getPitchDecks(),
        getProjectUploads(companyId)
      ]);
      
      const decksData = decksResponse.data || decksResponse;
      const uploadsData = uploadsResponse.data || uploadsResponse;
      
      setProjectDecks(Array.isArray(decksData) ? decksData : []);
      setUploads(uploadsData.uploads || []);
      
      // Set first deck as selected if available
      if (decksData && decksData.length > 0) {
        setSelectedDeck(decksData[0]);
      }
      
      // Update breadcrumbs
      setBreadcrumbs([
        { label: t('navigation.dashboard'), path: '/dashboard' },
        { label: `Project: ${companyId}`, path: null }
      ]);
      
    } catch (err) {
      console.error('Error loading project data:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to load project data');
    } finally {
      setLoading(false);
    }
  };

  const handleDeckSelect = (deck) => {
    setSelectedDeck(deck);
  };

  const handleViewDeckAnalysis = (deck) => {
    navigate(`/project/${companyId}/deck-viewer/${deck.id}`);
  };

  const handleViewResults = (deck) => {
    navigate(`/project/${companyId}/results/${deck.id}`);
  };

  const TabPanel = ({ children, value, index }) => (
    <div hidden={value !== index}>
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );

  const DeckCard = ({ deck }) => (
    <Card 
      sx={{ 
        cursor: 'pointer',
        transition: 'all 0.2s',
        '&:hover': { 
          transform: 'translateY(-2px)',
          boxShadow: 3 
        },
        border: selectedDeck?.id === deck.id ? 2 : 1,
        borderColor: selectedDeck?.id === deck.id ? 'primary.main' : 'grey.300'
      }}
      onClick={() => handleDeckSelect(deck)}
    >
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <AssessmentIcon sx={{ mr: 1, color: 'primary.main' }} />
          <Typography variant="h6">
            {deck.filename || `Deck ${deck.id}`}
          </Typography>
        </Box>
        
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Uploaded: {new Date(deck.created_at).toLocaleDateString()}
        </Typography>
        
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 2 }}>
          <Chip 
            label={deck.results_file_path ? 'Analyzed' : 'Processing'} 
            color={deck.results_file_path ? 'success' : 'warning'}
            size="small"
          />
          <Chip 
            label="PDF" 
            variant="outlined"
            size="small"
          />
        </Box>
      </CardContent>
      
      <CardActions>
        <Button
          size="small"
          startIcon={<VisibilityIcon />}
          onClick={(e) => {
            e.stopPropagation();
            handleViewDeckAnalysis(deck);
          }}
          disabled={!deck.results_file_path}
        >
          Deck Viewer
        </Button>
        <Button
          size="small"
          startIcon={<AssessmentIcon />}
          onClick={(e) => {
            e.stopPropagation();
            handleViewResults(deck);
          }}
          disabled={!deck.results_file_path}
        >
          Results
        </Button>
      </CardActions>
    </Card>
  );

  const OverviewContent = () => (
    <Box>
      <Typography variant="h5" sx={{ mb: 3 }}>
        Project Overview
      </Typography>
      
      <Grid container spacing={3}>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2, textAlign: 'center' }}>
            <Typography variant="h3" color="primary">
              {projectDecks.length}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Total Decks
            </Typography>
          </Paper>
        </Grid>
        
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2, textAlign: 'center' }}>
            <Typography variant="h3" color="success.main">
              {projectDecks.filter(d => d.results_file_path).length}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Analyzed
            </Typography>
          </Paper>
        </Grid>
        
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2, textAlign: 'center' }}>
            <Typography variant="h3" color="warning.main">
              {projectDecks.filter(d => !d.results_file_path).length}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Processing
            </Typography>
          </Paper>
        </Grid>
      </Grid>
      
      <Divider sx={{ my: 4 }} />
      
      <Typography variant="h6" sx={{ mb: 2 }}>
        Recent Decks
      </Typography>
      
      <Grid container spacing={3}>
        {projectDecks.slice(0, 6).map((deck) => (
          <Grid item xs={12} md={6} lg={4} key={deck.id}>
            <DeckCard deck={deck} />
          </Grid>
        ))}
      </Grid>
    </Box>
  );

  const DecksContent = () => (
    <Box>
      <Typography variant="h5" sx={{ mb: 3 }}>
        All Decks
      </Typography>
      
      <Grid container spacing={3}>
        {projectDecks.map((deck) => (
          <Grid item xs={12} md={6} lg={4} key={deck.id}>
            <DeckCard deck={deck} />
          </Grid>
        ))}
      </Grid>
      
      {projectDecks.length === 0 && (
        <Alert severity="info" sx={{ mt: 2 }}>
          No decks found for this project. Upload a pitch deck to get started.
        </Alert>
      )}
    </Box>
  );

  const UploadsContent = () => (
    <Box>
      <Typography variant="h5" sx={{ mb: 3 }}>
        File Uploads
      </Typography>
      
      <Grid container spacing={2}>
        {uploads.map((upload, index) => (
          <Grid item xs={12} key={index}>
            <Paper sx={{ p: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  <UploadIcon sx={{ mr: 2, color: 'text.secondary' }} />
                  <Box>
                    <Typography variant="subtitle1">
                      {upload.filename}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {(upload.file_size / 1024 / 1024).toFixed(2)} MB • {upload.file_type} • {new Date(upload.upload_date).toLocaleDateString()}
                    </Typography>
                  </Box>
                </Box>
                
                <Chip 
                  label={upload.file_type} 
                  variant="outlined"
                  size="small"
                />
              </Box>
            </Paper>
          </Grid>
        ))}
      </Grid>
      
      {uploads.length === 0 && (
        <Alert severity="info" sx={{ mt: 2 }}>
          No uploads found for this project.
        </Alert>
      )}
    </Box>
  );

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <Button
          startIcon={<ArrowBackIcon />}
          onClick={() => navigate('/dashboard')}
          sx={{ mr: 2 }}
        >
          Back to Dashboard
        </Button>
        <Typography variant="h4">
          Project Dashboard
        </Typography>
      </Box>

      {/* Breadcrumbs */}
      <Breadcrumbs sx={{ mb: 3 }}>
        {breadcrumbs.map((crumb, index) => (
          crumb.path ? (
            <Link 
              key={index} 
              component="button" 
              variant="body2" 
              onClick={() => navigate(crumb.path)}
              sx={{ textDecoration: 'none' }}
            >
              {crumb.label}
            </Link>
          ) : (
            <Typography key={index} variant="body2" color="text.primary">
              {crumb.label}
            </Typography>
          )
        ))}
      </Breadcrumbs>

      {/* Error Alert */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Main Content */}
      <Paper sx={{ width: '100%' }}>
        <Tabs value={activeTab} onChange={(e, newValue) => setActiveTab(newValue)}>
          <Tab label="Overview" />
          <Tab label="All Decks" />
          <Tab label="Uploads" />
        </Tabs>

        <TabPanel value={activeTab} index={0}>
          <OverviewContent />
        </TabPanel>

        <TabPanel value={activeTab} index={1}>
          <DecksContent />
        </TabPanel>

        <TabPanel value={activeTab} index={2}>
          <UploadsContent />
        </TabPanel>
      </Paper>
    </Box>
  );
};

export default ProjectDashboard;