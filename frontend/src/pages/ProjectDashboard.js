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
  LinearProgress,
} from '@mui/material';
import {
  Visibility as VisibilityIcon,
  Assessment as AssessmentIcon,
  Upload as UploadIcon,
  ArrowBack as ArrowBackIcon,
  Timeline as TimelineIcon,
  CheckCircle,
  RadioButtonUnchecked,
  Schedule,
  Info as InfoIcon
} from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';

import { 
  getPitchDecks,
  getMyProjects,
  getAllProjects,
  getProjectJourney,
  getProjectDecks
} from '../services/api';
import ProjectUploads from '../components/ProjectUploads';

const ProjectDashboard = () => {
  const { t } = useTranslation('dashboard');
  const navigate = useNavigate();
  const { companyId, projectId } = useParams();
  
  // Determine if this is GP admin view
  const isAdminView = window.location.pathname.includes('/admin/project/');
  
  const [activeTab, setActiveTab] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Project data
  const [projectDecks, setProjectDecks] = useState([]);
  const [selectedDeck, setSelectedDeck] = useState(null);
  const [actualCompanyId, setActualCompanyId] = useState(null);
  
  // Funding journey data
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState(null);
  const [projectJourney, setProjectJourney] = useState(null);
  const [journeyLoading, setJourneyLoading] = useState(false);
  const [hoveredStageId, setHoveredStageId] = useState(null);
  
  const [breadcrumbs, setBreadcrumbs] = useState([
    { label: t('navigation.dashboard'), path: '/dashboard' },
    { label: 'Project Dashboard', path: null }
  ]);

  useEffect(() => {
    loadProjectData();
    loadFundingData();
  }, [companyId, projectId]);

  // Debug actualCompanyId changes
  useEffect(() => {
    console.log('actualCompanyId state changed to:', actualCompanyId);
  }, [actualCompanyId]);

  // Function to refresh project data (can be called after upload)
  const refreshProjectData = () => {
    loadProjectData();
  };

  const loadProjectData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      let decksResponse;
      let displayId;
      let projectName;
      
      if (isAdminView && projectId) {
        // GP Admin view: get decks for specific project
        decksResponse = await getProjectDecks(projectId);
        const responseData = decksResponse.data || decksResponse;
        projectName = responseData.project_name || 'Unknown Project';
        displayId = projectName;
        // Set the actual company ID for uploads functionality
        console.log('Setting actualCompanyId to:', responseData.company_id);
        setActualCompanyId(responseData.company_id);
      } else if (companyId) {
        // Regular startup view: get user's own decks
        decksResponse = await getPitchDecks();
        displayId = `Project: ${companyId}`;
        setActualCompanyId(companyId);
      } else {
        throw new Error('No valid project identifier found');
      }
      
      const decksData = decksResponse.data || decksResponse;
      
      // Handle the response structure: {decks: [...]}
      const decks = decksData.decks || decksData;
      setProjectDecks(Array.isArray(decks) ? decks : []);
      
      // Set first deck as selected if available
      if (decks && decks.length > 0) {
        setSelectedDeck(decks[0]);
      }
      
      // Update breadcrumbs
      const dashboardPath = isAdminView ? '/dashboard/gp' : '/dashboard';
      setBreadcrumbs([
        { label: t('navigation.dashboard'), path: dashboardPath },
        { label: displayId, path: null }
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
    const targetCompanyId = isAdminView ? deck.company_id : companyId;
    navigate(`/project/${targetCompanyId}/deck-viewer/${deck.id}`);
  };

  const handleViewResults = (deck) => {
    const targetCompanyId = isAdminView ? deck.company_id : companyId;
    navigate(`/project/${targetCompanyId}/results/${deck.id}`);
  };

  // Funding journey functions
  const loadFundingData = async () => {
    try {
      setJourneyLoading(true);
      
      console.log('Loading funding data for companyId:', companyId, 'projectId:', projectId, 'isAdminView:', isAdminView);
      
      let projectsData = [];
      let matchingProject = null;
      
      if (isAdminView && projectId) {
        // GP Admin view: get all projects and find by projectId
        const projectsResponse = await getAllProjects();
        projectsData = projectsResponse.data || [];
        console.log('All projects response:', projectsData);
        
        // Find the project by projectId (not companyId)
        matchingProject = projectsData.find(p => p.id === parseInt(projectId));
        console.log('Matching project found by ID:', matchingProject);
      } else if (companyId) {
        // Regular startup view: get user's own projects
        const projectsResponse = await getMyProjects();
        projectsData = projectsResponse.data || [];
        console.log('My projects response:', projectsData);
        
        // Find the project matching this company ID
        matchingProject = projectsData.find(p => p.company_id === companyId);
        console.log('Matching project found by company ID:', matchingProject);
      }
      
      setProjects(projectsData);
      
      if (matchingProject) {
        setSelectedProject(matchingProject);
        
        // Load the journey for this project
        console.log('Loading journey for project ID:', matchingProject.id);
        const journeyResponse = await getProjectJourney(matchingProject.id);
        console.log('Journey response:', journeyResponse.data);
        setProjectJourney(journeyResponse.data);
      } else {
        console.log('No matching project found. Available projects:', projectsData.map(p => ({id: p.id, company_id: p.company_id})));
      }
    } catch (err) {
      console.error('Error loading funding data:', err);
      console.error('Error details:', err.response?.data);
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

  const handleStageHover = (stage) => {
    setHoveredStageId(stage.id);
  };

  const handleStageLeave = () => {
    setHoveredStageId(null);
  };

  const getStageDescription = (stageCode) => {
    return t(`journey.descriptions.${stageCode}`, 'No description available for this stage.');
  };

  const getStageName = (stageCode) => {
    return t(`journey.stages.${stageCode}`, stageCode);
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
            {deck.filename || deck.file_name || `${t('project.labels.deckDefault')} ${deck.id}`}
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
        {t('project.tabs.overview')}
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
            {t('journey.progressOverview')}
          </Typography>
          <Card sx={{ mb: 4, bgcolor: 'primary.50', border: '1px solid', borderColor: 'primary.200' }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box>
                  <Typography variant="h6" gutterBottom>
                    {selectedProject.project_name} - {t('journey.title')}
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
                      {Math.round(projectJourney.completion_percentage)}% {t('journey.complete')}
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
                  onClick={() => setActiveTab(0)}
                  size="large"
                >
                  {t('journey.viewJourney')}
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
        {t('project.tabs.allDecks')}
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

  const UploadsContent = () => {
    console.log('UploadsContent render - isAdminView:', isAdminView, 'actualCompanyId:', actualCompanyId, 'companyId:', companyId);
    
    // Wait for actualCompanyId to be loaded in admin view
    if (isAdminView && !actualCompanyId) {
      console.log('UploadsContent - waiting for actualCompanyId...');
      return (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
          <CircularProgress />
        </Box>
      );
    }
    
    const finalCompanyId = actualCompanyId || companyId;
    console.log('UploadsContent - passing companyId to ProjectUploads:', finalCompanyId);
    
    return (
      <ProjectUploads companyId={finalCompanyId} onUploadComplete={refreshProjectData} />
    );
  };

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
          {t('journey.noJourneyData')}
        </Alert>
      );
    }

    return (
      <Box>
        <Typography variant="h5" sx={{ mb: 3 }}>
          {t('journey.title')} - {selectedProject.project_name}
        </Typography>
        
        
        {/* Overall Progress Bar */}
        <Box sx={{ mb: 4 }}>
          <Typography variant="h6" gutterBottom>
            {t('journey.overallProgress')}
          </Typography>
          <LinearProgress 
            variant="determinate" 
            value={projectJourney.completion_percentage}
            sx={{ height: 12, borderRadius: 6 }}
          />
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            {Math.round(projectJourney.completion_percentage)}% {t('journey.complete')}
          </Typography>
        </Box>

        {/* Funding Journey Stepper */}
        <Typography variant="h6" gutterBottom>
          {t('journey.fundingProcessSteps')}
        </Typography>
        <Stepper 
          orientation="vertical"
          sx={{ mt: 2 }}
        >
          {projectJourney.stages.map((stage) => (
            <Step key={stage.id} active={true}>
              <StepLabel>
                <Box 
                  sx={{ display: 'flex', alignItems: 'center', gap: 1 }}
                  onMouseEnter={() => handleStageHover(stage)}
                  onMouseLeave={handleStageLeave}
                >
                  <Typography 
                    variant="body1" 
                    fontWeight="medium"
                    sx={{ 
                      cursor: 'pointer',
                      '&:hover': { color: 'primary.main', textDecoration: 'underline' }
                    }}
                  >
                    {getStageName(stage.stage_code || stage.stage_name?.toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, ''))}
                  </Typography>
                  <Chip 
                    label={t(`journey.progress.${stage.status}`, stage.status)} 
                    color={getStatusColor(stage.status)}
                    size="small"
                  />
                </Box>
                <Box sx={{ mt: 1 }}>
                  {stage.status === 'completed' && stage.completed_at && (
                    <Typography variant="caption" color="text.secondary">
                      {t('journey.dates.completed')} {new Date(stage.completed_at).toLocaleDateString()}
                    </Typography>
                  )}
                  {stage.status === 'active' && stage.started_at && (
                    <Typography variant="caption" color="text.secondary">
                      {t('journey.dates.started')} {new Date(stage.started_at).toLocaleDateString()}
                    </Typography>
                  )}
                </Box>
              </StepLabel>
              <StepContent>
                <Box sx={{ pb: 2 }}>
                  {/* Show stage description on hover */}
                  {hoveredStageId === stage.id && (
                    <Box sx={{ mt: 2, p: 2, bgcolor: 'grey.50', borderRadius: 1, border: '1px solid', borderColor: 'grey.200' }}>
                      <Typography variant="body2" sx={{ mb: 1 }}>
                        <strong>{t('journey.stageInfo.stageOf', { order: stage.stage_order })}</strong>
                      </Typography>
                      <Typography variant="body2" paragraph>
                        {getStageDescription(stage.stage_code || stage.stage_name?.toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, ''))}
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
          {t('journey.backToDashboard')}
        </Button>
        <Typography variant="h4">
          {t('project.title')}
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
          <Tab label={t('journey.title')} />
          <Tab label={t('project.tabs.overview')} />
          <Tab label={t('project.tabs.allDecks')} />
          <Tab label={t('project.tabs.uploads')} />
        </Tabs>

        <TabPanel value={activeTab} index={0}>
          <FundingJourneyContent />
        </TabPanel>

        <TabPanel value={activeTab} index={1}>
          <OverviewContent />
        </TabPanel>

        <TabPanel value={activeTab} index={2}>
          <DecksContent />
        </TabPanel>

        <TabPanel value={activeTab} index={3}>
          <UploadsContent />
        </TabPanel>
      </Paper>
    </Box>
  );
};

export default ProjectDashboard;