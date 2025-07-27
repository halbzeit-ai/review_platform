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
  const [expandedStageId, setExpandedStageId] = useState(null);
  
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
      
      console.log('Loading funding data for companyId:', companyId);
      
      // Load my projects
      const projectsResponse = await getMyProjects();
      const projectsData = projectsResponse.data || [];
      console.log('My projects response:', projectsData);
      setProjects(projectsData);
      
      // Find the project matching this company ID
      const matchingProject = projectsData.find(p => p.company_id === companyId);
      console.log('Matching project found:', matchingProject);
      
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

  const handleStageClick = (stage) => {
    setExpandedStageId(expandedStageId === stage.id ? null : stage.id);
  };

  const getStageDescription = (stageCode) => {
    const descriptions = {
      'deck_submission': 'You initially submit your deck and our AI will get the deal relevant data, analyse your startup according to our investment criteria. We will provide you with helpful feedback on your deck, the presentation of you company and the state of your business. You are then invited to answer questions, fill in details and also submit a new version of your deck.',
      
      'video_upload': 'As you can imagine, we are flooded with pitches and we simply cannot afford to meet every startup in person. To make the process easier for us and for you, we invite you to do a 5min video pitch recording you and possible co-founders to present your startup. A second video would then also demonstrate your product, software or any relevant information to for offering to the market. Again, we will analyse these videos using AI, but we will also watch them in person.',
      
      'gp_interview': 'Now it\'s time to get to know you in person and also you can ask your questions about the funding process, anything you want to know about HALBZEIT and the founders and hopefully, we get a personal touch here and an initial taste about you as founders feel in person. For most institutions, this is the most important step as it is very important to believe in the founders and their views on the world.',
      
      'kyc_verification': 'As a funding platform it is a legal obligation to verify that you are you and have an external proof of that. We are working with online verification services that will have a brief video interview with you asking you to show your ID and move your face to match it with the ID.',
      
      'due_diligence': 'Next, we need to look a bit deeper into your business plan, financial statements of the last couple of years, medical validity of your offering and so on. This is an important and legally obligatory step for us as funding platform as we have the obligation to deliver legit startups in whose success we as HALBZEIT can believe in.',
      
      'term_sheet': 'Once that is done, we can go on to negotiate terms of the investment. These are usually standard terms, but we may deviate when we are co-investing with other institutions. Further more, we need to discuss the current valuation of your company which has a direct effect on what share of your company our investors will get.',
      
      'publishing': 'Now we are able to "go public"! Your startup will be presented to the public and investors can view the investment opportunity. As part of this, we will publish a so-called KIIS (Key Investment Information Sheet) as this is a legal obligation again. It includes the investment terms in addition to your company\'s information.',
      
      'investor_commits': 'Investors are informed by us that there is a new investment opportunity, e.g. by our newsletter. They can also interact with you and comment on specific details of your offering, scientific background, reimbursement etc. They are asked for a financial commitment, e.g. 10.000€, we collect the commitments and you\'ll see how much is committed at any time.',
      
      'commit_complete': 'If you get enough committed capital: BINGO! Let\'s formalize the relationship, sign contracts and transfer the money.',
      
      'signing_vehicle': 'We are setting up a legal entity in which all investors are bundled, they get a share of that vehicle proportionate to the amount they are investing. This legal entity will become a shareholder in your company. In this way, you are not dealing with dozens of new investors but only one that will speak with one voice.',
      
      'signing_startup': 'We will sign the investment contract with you based on the term sheet we have negotiated earlier. We GPs do this as representing person in the role of the legal vehicle.',
      
      'funding_collection': 'The legal entity has a bank account, it will collect the money from the investors and keep it until the investment is formally registered here in Germany.',
      
      'funding_transfer': 'Once all money is there and legal obligations are met, the transfer of the money to your bank account is executed.',
      
      'round_closed': 'This is the final step: PARTY! From now on, the legal entity will receive monthly updates and reporting from you and will deliver this information to the investors. Again, this is a legal obligation.'
    };
    
    return descriptions[stageCode] || 'No description available for this stage.';
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
                  onClick={() => setActiveTab(0)}
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
              <StepLabel>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography 
                    variant="body1" 
                    fontWeight="medium"
                    sx={{ 
                      cursor: 'pointer',
                      '&:hover': { color: 'primary.main', textDecoration: 'underline' }
                    }}
                    onClick={() => handleStageClick(stage)}
                  >
                    {stage.stage_name}
                  </Typography>
                  <Chip 
                    label={stage.status} 
                    color={getStatusColor(stage.status)}
                    size="small"
                  />
                </Box>
                <Box sx={{ mt: 1 }}>
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
              </StepLabel>
              <StepContent>
                <Box sx={{ pb: 2 }}>
                  {/* Show stage description when expanded */}
                  {expandedStageId === stage.id && (
                    <Box sx={{ mt: 2, p: 2, bgcolor: 'grey.50', borderRadius: 1, border: '1px solid', borderColor: 'grey.200' }}>
                      <Typography variant="body2" sx={{ mb: 1 }}>
                        <strong>Stage {stage.stage_order} of 14</strong>
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
          <Tab label="Funding Journey" />
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