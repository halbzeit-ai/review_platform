import React, { useState, useEffect, useCallback, useMemo } from 'react';
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
  Info as InfoIcon,
  Psychology,
  Business,
  AttachMoney,
  DateRange,
  Category
} from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';

import { 
  getPitchDecks,
  getMyProjects,
  getAllProjects,
  getProjectJourney,
  getProjectDecks,
  getProcessingProgress,
  getExtractionResults
} from '../services/api';
import ProjectUploads from '../components/ProjectUploads';

// CRITICAL FIX: Move TabPanel OUTSIDE component to prevent recreation on every render
const TabPanel = ({ children, value, index }) => (
  <div hidden={value !== index}>
    {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
  </div>
);

const ProjectDashboard = () => {
  const { t } = useTranslation('dashboard');
  const navigate = useNavigate();
  const { companyId, projectId } = useParams();
  const [searchParams] = useSearchParams();
  
  // Determine if this is GP admin view
  const isAdminView = window.location.pathname.includes('/admin/project/');
  
  // Initialize activeTab from URL parameter or default to 0
  const [activeTab, setActiveTab] = useState(() => {
    const tabParam = searchParams.get('tab');
    return tabParam ? parseInt(tabParam, 10) : 0;
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Project data
  const [projectDecks, setProjectDecks] = useState([]);
  const [selectedDeck, setSelectedDeck] = useState(null);
  const [actualCompanyId, setActualCompanyId] = useState(null);
  const [progressData, setProgressData] = useState({});
  const [progressIntervals, setProgressIntervals] = useState({});
  const [extractionResults, setExtractionResults] = useState([]);
  const [extractionLoading, setExtractionLoading] = useState(true);
  
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
    fetchExtractionResults();
  }, [companyId, projectId]);

  // Cleanup intervals on unmount
  useEffect(() => {
    return () => {
      // Clear all progress polling intervals
      Object.values(progressIntervals).forEach(intervalId => {
        clearInterval(intervalId);
      });
    };
  }, [progressIntervals]);

  // Debug actualCompanyId changes
  useEffect(() => {
    console.log('actualCompanyId state changed to:', actualCompanyId);
  }, [actualCompanyId]);

  const loadProjectData = useCallback(async () => {
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
      
      // Start polling for processing decks
      startProgressPollingForDecks(decks);
      
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
  }, [isAdminView, projectId, companyId]); // Removed 't' dependency to prevent infinite recreations

  // Function to refresh project data (can be called after upload)
  const refreshProjectData = useCallback(() => {
    loadProjectData();
    // Automatically switch to overview tab after upload (tab index 1)
    setActiveTab(1);
  }, [loadProjectData]);

  const startProgressPollingForDecks = (decks) => {
    // Clear existing intervals
    Object.values(progressIntervals).forEach(intervalId => {
      clearInterval(intervalId);
    });
    setProgressIntervals({});
    
    // Only poll for decks that are actually processing or queued (not failed/completed)
    const processingDecks = decks.filter(deck => 
      deck.processing_status === 'processing' || 
      deck.processing_status === 'queued' ||
      (deck.processing_status === 'pending' && !deck.results_file_path)
    );
    
    console.log(`Progress polling: Found ${processingDecks.length} processing decks out of ${decks.length} total decks`);
    
    if (processingDecks.length === 0) {
      return; // No polling needed
    }
    
    // Use a single interval that batches all progress requests with intelligent throttling
    let batchIndex = 0;
    const BATCH_SIZE = 3; // Process max 3 decks at a time
    const BATCH_DELAY = 8000; // 8 seconds between batches (increased from 3s)
    const STAGGER_DELAY = 1000; // 1 second between individual requests in batch
    
    const batchedPollingInterval = setInterval(async () => {
      // Get current batch of decks to poll
      const batchStart = batchIndex * BATCH_SIZE;
      const batchEnd = Math.min(batchStart + BATCH_SIZE, processingDecks.length);
      const currentBatch = processingDecks.slice(batchStart, batchEnd);
      
      console.log(`Progress polling: Batch ${Math.floor(batchIndex * BATCH_SIZE / BATCH_SIZE) + 1}, processing ${currentBatch.length} decks (${currentBatch.map(d => d.id).join(', ')})`);
      
      // Process batch with staggered requests to avoid overwhelming server
      for (let i = 0; i < currentBatch.length; i++) {
        const deck = currentBatch[i];
        
        // Stagger requests within batch
        setTimeout(() => {
          fetchProgressForDeck(deck.id);
        }, i * STAGGER_DELAY);
      }
      
      // Move to next batch, cycling back to start
      batchIndex = (batchIndex + 1) % Math.ceil(processingDecks.length / BATCH_SIZE);
      
    }, BATCH_DELAY);
    
    // Store the single interval for cleanup
    setProgressIntervals({ batched: batchedPollingInterval });
    
    // Initial batch - fetch progress for first batch immediately
    processingDecks.slice(0, BATCH_SIZE).forEach((deck, index) => {
      setTimeout(() => {
        fetchProgressForDeck(deck.id);
      }, index * STAGGER_DELAY);
    });
  };
  
  const fetchProgressForDeck = async (deckId) => {
    try {
      const response = await getProcessingProgress(deckId);
      const data = response.data || response;
      
      // Extract progress data from queue system or legacy GPU progress
      const progressInfo = data.queue_progress || data.gpu_progress || data;
      
      setProgressData(prev => ({
        ...prev,
        [deckId]: progressInfo
      }));
      
      // Check processing status from either gpu_progress or root level
      const status = progressInfo.status || data.processing_status;
      
      // If processing is complete, mark deck for removal from polling
      if (status === 'completed' || status === 'failed') {
        console.log(`Deck ${deckId} finished processing with status: ${status}`);
        
        // Update just this deck's status without reloading everything
        if (status === 'completed') {
          // Mark this deck as completed with results and restart polling with updated list
          setProjectDecks(prev => {
            const updatedDecks = prev.map(deck => 
              deck.id === deckId 
                ? { ...deck, results_file_path: 'completed', processing_status: 'completed' }
                : deck
            );
            
            // Restart polling with updated deck list (async to avoid state conflicts)
            setTimeout(() => {
              startProgressPollingForDecks(updatedDecks);
            }, 1000);
            
            return updatedDecks;
          });
        }
      }
    } catch (error) {
      console.error('Error fetching progress for deck', deckId, error);
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
    console.log('handleViewResults called:', {
      isAdminView,
      pathname: window.location.pathname,
      deckId: deck.id,
      companyId
    });
    
    if (isAdminView) {
      // In admin view (GP impersonating startup), use startup results page
      console.log('Navigating to startup results page:', `/results/${deck.id}`);
      navigate(`/results/${deck.id}`);
    } else {
      // Regular startup view uses project results page
      console.log('Navigating to project results page:', `/project/${companyId}/results/${deck.id}`);
      navigate(`/project/${companyId}/results/${deck.id}`);
    }
  };

  // Extraction results functions
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

  // Funding journey functions
  const loadFundingData = async () => {
    try {
      setJourneyLoading(true);
      
      console.log('Loading funding data for companyId:', companyId, 'projectId:', projectId, 'isAdminView:', isAdminView);
      
      let projectsData = [];
      let matchingProject = null;
      
      if (isAdminView && projectId) {
        // GP Admin view: get all projects and find by projectId (include test data for dojo projects)
        const projectsResponse = await getAllProjects(true);  // Include test data
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
          {t('project.labels.uploaded')} {new Date(deck.created_at).toLocaleString('en-US', { 
            year: 'numeric', 
            month: 'short', 
            day: 'numeric', 
            hour: '2-digit', 
            minute: '2-digit',
            hour12: false 
          })}
        </Typography>
        
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 2 }}>
          {deck.results_file_path ? (
            <Chip 
              label={t('project.status.analyzed')} 
              color="success"
              size="small"
            />
          ) : (
            <>
              <Chip 
                label={progressData[deck.id]?.current_stage || t('project.status.processing')} 
                color="warning"
                size="small"
              />
              {progressData[deck.id]?.progress_percentage !== undefined && (
                <Chip 
                  label={`${Math.round(progressData[deck.id].progress_percentage)}%`} 
                  color="info"
                  size="small"
                  variant="outlined"
                />
              )}
            </>
          )}
          <Chip 
            label={t('project.status.pdf')} 
            variant="outlined"
            size="small"
          />
        </Box>
        
        {/* Progress bar for processing decks */}
        {!deck.results_file_path && progressData[deck.id]?.progress_percentage !== undefined && (
          <Box sx={{ mb: 2 }}>
            <LinearProgress 
              variant="determinate" 
              value={progressData[deck.id].progress_percentage} 
              sx={{ height: 6, borderRadius: 3 }}
            />
            {progressData[deck.id]?.message && (
              <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
                {progressData[deck.id].message}
              </Typography>
            )}
          </Box>
        )}
      </CardContent>
      
      <CardActions>
        <Button
          size="small"
          startIcon={<VisibilityIcon />}
          onClick={(e) => {
            e.stopPropagation();
            handleViewDeckAnalysis(deck);
          }}
          disabled={deck.processing_status === 'queued' || (deck.processing_status === 'processing' && (!progressData[deck.id] || progressData[deck.id].progress_percentage < 20))}
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

  // FIXED: Stable finalCompanyId - only changes when the actual result value changes
  const finalCompanyId = useMemo(() => {
    const result = actualCompanyId || companyId;
    console.log('finalCompanyId computed:', result, 'from actualCompanyId:', actualCompanyId, 'companyId:', companyId);
    return result;
  }, [actualCompanyId || companyId]); // Depend on the result, not the inputs

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
          <Tab label="Extraction Results" />
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
          {isAdminView && !actualCompanyId ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
              <CircularProgress />
            </Box>
          ) : (
            <ProjectUploads 
              companyId={finalCompanyId} 
              onUploadComplete={refreshProjectData} 
            />
          )}
        </TabPanel>

        <TabPanel value={activeTab} index={4}>
          <Typography variant="h6" gutterBottom>
            <Psychology sx={{ mr: 1, verticalAlign: 'middle' }} />
            Extraction Results
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
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
        </TabPanel>
      </Paper>
    </Box>
  );
};

export default ProjectDashboard;