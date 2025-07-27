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
  Divider,
  Stepper,
  Step,
  StepLabel,
  StepContent,
  LinearProgress
} from '@mui/material';
import {
  Visibility as VisibilityIcon,
  Assessment as AssessmentIcon,
  Upload as UploadIcon,
  ArrowBack as ArrowBackIcon,
  Timeline as TimelineIcon,
  CheckCircle,
  RadioButtonUnchecked,
  Schedule
} from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';

import { 
  getPitchDecks,
  getMyProjects,
  getProjectJourney
} from '../services/api';
import ProjectUploads from '../components/ProjectUploads';

const ProjectDashboard = () => {
  const { t } = useTranslation('dashboard');
  const navigate = useNavigate();
  const { companyId } = useParams();
  
  const [activeTab, setActiveTab] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Project data
  const [projectDecks, setProjectDecks] = useState([]);
  const [selectedDeck, setSelectedDeck] = useState(null);
  
  // Funding journey data
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState(null);
  const [projectJourney, setProjectJourney] = useState(null);
  const [journeyLoading, setJourneyLoading] = useState(false);
  
  const [breadcrumbs, setBreadcrumbs] = useState([
    { label: t('navigation.dashboard'), path: '/dashboard' },
    { label: 'Project Dashboard', path: null }
  ]);

  useEffect(() => {
    loadProjectData();
    loadFundingData();
  }, [companyId]);

  // Function to refresh project data (can be called after upload)
  const refreshProjectData = () => {
    loadProjectData();
  };

  const loadProjectData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Load project decks
      const decksResponse = await getPitchDecks();
      
      const decksData = decksResponse.data || decksResponse;
      
      // Handle the response structure: {decks: [...]}
      const decks = decksData.decks || decksData;
      setProjectDecks(Array.isArray(decks) ? decks : []);
      
      // Set first deck as selected if available
      if (decks && decks.length > 0) {
        setSelectedDeck(decks[0]);
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

  // Funding journey functions
  const loadFundingData = async () => {
    try {
      setJourneyLoading(true);
      
      // Load my projects
      const projectsResponse = await getMyProjects();
      const projectsData = projectsResponse.data || [];
      setProjects(projectsData);
      
      // Find the project matching this company ID
      const matchingProject = projectsData.find(p => p.company_id === companyId);
      if (matchingProject) {
        setSelectedProject(matchingProject);
        
        // Load the journey for this project
        const journeyResponse = await getProjectJourney(matchingProject.id);
        setProjectJourney(journeyResponse.data);
      }
    } catch (err) {
      console.error('Error loading funding data:', err);
    } finally {
      setJourneyLoading(false);
    }
  };

  // Helper functions for funding journey
  const getStatusColor = (status) => {
    switch (status) {
      case 'completed': return 'success';
      case 'active': return 'primary';
      case 'pending': return 'default';
      case 'skipped': return 'warning';
      default: return 'default';
    }
  };

  const getActiveStep = () => {
    if (!projectJourney?.stages) return 0;
    const activeStage = projectJourney.stages.find(stage => stage.status === 'active');
    return activeStage ? activeStage.stage_order - 1 : 0;
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
            {deck.filename || `${t('project.labels.deckDefault')} ${deck.id}`}
          </Typography>
        </Box>
        
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {t('project.labels.uploaded')} {new Date(deck.created_at).toLocaleDateString()}
        </Typography>
        
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 2 }}>
          <Chip 
            label={deck.results_file_path ? t('project.status.analyzed') : t('project.status.processing')} 
            color={deck.results_file_path ? 'success' : 'warning'}
            size="small"
          />
          <Chip 
            label={t('project.status.pdf')} 
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
          disabled={!deck.visual_analysis_completed && !deck.results_file_path}
        >
          {t('project.actions.deckViewer')}
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
          {t('project.actions.viewResults')}
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
      
      {/* Funding Progress Card */}
      {selectedProject && projectJourney && (
        <>
          <Typography variant="h6" sx={{ mb: 2 }}>
            Funding Progress
          </Typography>
          <Card sx={{ mb: 4, bgcolor: 'primary.50', border: '1px solid', borderColor: 'primary.200' }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box>
                  <Typography variant="h6" gutterBottom>
                    {selectedProject.project_name} - Funding Journey
                  </Typography>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    Track your progress through the 14-stage funding process
                  </Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mt: 2 }}>
                    <LinearProgress 
                      variant="determinate" 
                      value={projectJourney.completion_percentage}
                      sx={{ width: 200, height: 8, borderRadius: 4 }}
                    />
                    <Typography variant="body2" color="text.secondary">
                      {Math.round(projectJourney.completion_percentage)}% Complete
                    </Typography>
                    <Chip 
                      label={`${projectJourney.completed_stages}/${projectJourney.total_stages} Stages`} 
                      color="primary" 
                      size="small"
                    />
                  </Box>
                </Box>
                <Button
                  variant="contained"
                  startIcon={<TimelineIcon />}
                  onClick={() => setActiveTab(3)}
                  size="large"
                >
                  View Journey
                </Button>
              </Box>
            </CardContent>
          </Card>
        </>
      )}
      
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
    <ProjectUploads companyId={companyId} onUploadComplete={refreshProjectData} />
  );

  const FundingJourneyContent = () => {
    if (journeyLoading) {
      return (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
          <CircularProgress />
        </Box>
      );
    }

    if (!selectedProject || !projectJourney) {
      return (
        <Alert severity="info">
          No funding journey data available for this project yet.
        </Alert>
      );
    }

    return (
      <Box>
        <Typography variant="h5" sx={{ mb: 3 }}>
          Funding Journey - {selectedProject.project_name}
        </Typography>
        
        {/* Progress Overview */}
        <Grid container spacing={3} sx={{ mb: 4 }}>
          <Grid item xs={6} sm={3}>
            <Paper sx={{ p: 2, textAlign: 'center' }}>
              <Typography variant="h3" color="primary">
                {Math.round(projectJourney.completion_percentage)}%
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Complete
              </Typography>
            </Paper>
          </Grid>
          <Grid item xs={6} sm={3}>
            <Paper sx={{ p: 2, textAlign: 'center' }}>
              <Typography variant="h3" color="success.main">
                {projectJourney.completed_stages}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Completed
              </Typography>
            </Paper>
          </Grid>
          <Grid item xs={6} sm={3}>
            <Paper sx={{ p: 2, textAlign: 'center' }}>
              <Typography variant="h3" color="primary">
                {projectJourney.active_stages}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Active
              </Typography>
            </Paper>
          </Grid>
          <Grid item xs={6} sm={3}>
            <Paper sx={{ p: 2, textAlign: 'center' }}>
              <Typography variant="h3" color="text.secondary">
                {projectJourney.pending_stages}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Pending
              </Typography>
            </Paper>
          </Grid>
        </Grid>
        
        {/* Overall Progress Bar */}
        <Box sx={{ mb: 4 }}>
          <Typography variant="h6" gutterBottom>
            Overall Progress
          </Typography>
          <LinearProgress 
            variant="determinate" 
            value={projectJourney.completion_percentage}
            sx={{ height: 12, borderRadius: 6 }}
          />
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            {Math.round(projectJourney.completion_percentage)}% Complete
          </Typography>
        </Box>

        {/* Funding Journey Stepper */}
        <Typography variant="h6" gutterBottom>
          Funding Process Steps
        </Typography>
        <Stepper 
          activeStep={getActiveStep()} 
          orientation="vertical"
          sx={{ mt: 2 }}
        >
          {projectJourney.stages.map((stage) => (
            <Step key={stage.id}>
              <StepLabel 
                optional={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 1 }}>
                    <Chip 
                      label={stage.status} 
                      color={getStatusColor(stage.status)}
                      size="small"
                    />
                    {stage.status === 'completed' && stage.completed_at && (
                      <Typography variant="caption" color="text.secondary">
                        Completed: {new Date(stage.completed_at).toLocaleDateString()}
                      </Typography>
                    )}
                    {stage.status === 'active' && stage.started_at && (
                      <Typography variant="caption" color="text.secondary">
                        Started: {new Date(stage.started_at).toLocaleDateString()}
                      </Typography>
                    )}
                  </Box>
                }
              >
                <Typography variant="body1" fontWeight="medium">
                  {stage.stage_name}
                </Typography>
              </StepLabel>
              <StepContent>
                <Box sx={{ pb: 2 }}>
                  {/* Show estimated completion if pending/active */}
                  {stage.estimated_completion && ['pending', 'active'].includes(stage.status) && (
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                      <Schedule fontSize="small" color="action" />
                      <Typography variant="caption" color="text.secondary">
                        Estimated completion: {new Date(stage.estimated_completion).toLocaleDateString()}
                      </Typography>
                    </Box>
                  )}

                  {/* Show completion notes if available */}
                  {stage.stage_metadata?.completion_notes && (
                    <Alert severity="info" sx={{ mt: 1 }}>
                      <Typography variant="body2">
                        {stage.stage_metadata.completion_notes}
                      </Typography>
                    </Alert>
                  )}
                </Box>
              </StepContent>
            </Step>
          ))}
        </Stepper>
      </Box>
    );
  };

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
          onClick={() => {
            const user = JSON.parse(localStorage.getItem('user'));
            if (user?.role === 'gp') {
              navigate('/dashboard/gp');
            } else {
              navigate('/dashboard');
            }
          }}
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
          <Tab label={t('project.tabs.overview')} />
          <Tab label={t('project.tabs.allDecks')} />
          <Tab label={t('project.tabs.uploads')} />
          <Tab label="Funding Journey" icon={<TimelineIcon />} />
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

        <TabPanel value={activeTab} index={3}>
          <FundingJourneyContent />
        </TabPanel>
      </Paper>
    </Box>
  );
};

export default ProjectDashboard;