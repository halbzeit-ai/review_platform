import React, { useState, useEffect } from 'react';
import { 
  Container, 
  Paper, 
  Typography, 
  Grid, 
  Box, 
  LinearProgress, 
  Stepper, 
  Step, 
  StepLabel, 
  StepContent,
  Chip,
  CircularProgress,
  Alert,
  Card,
  CardContent,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Divider
} from '@mui/material';
import { 
  CheckCircle, 
  RadioButtonUnchecked, 
  PlayCircle, 
  Schedule,
  Description,
  VideoLibrary,
  People,
  Gavel,
  Assignment,
  Publish,
  AccountBalance,
  AttachMoney,
  TrendingUp
} from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import { useParams, useNavigate } from 'react-router-dom';
import { getMyProjects, getProjectJourney } from '../services/api';

function StartupJourney() {
  const { t } = useTranslation('dashboard');
  const { projectId } = useParams();
  const navigate = useNavigate();
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState(null);
  const [projectJourney, setProjectJourney] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchMyProjects = async () => {
    try {
      const response = await getMyProjects();
      setProjects(response.data);
      
      // If we have a projectId from URL, select that project
      if (projectId) {
        const project = response.data.find(p => p.id === parseInt(projectId));
        if (project) {
          setSelectedProject(project);
          await fetchProjectJourney(project.id);
        }
      } else if (response.data.length > 0) {
        // Otherwise, select the first project
        setSelectedProject(response.data[0]);
        await fetchProjectJourney(response.data[0].id);
      }
    } catch (error) {
      console.error('Error fetching projects:', error);
      setError('Failed to fetch projects');
    } finally {
      setLoading(false);
    }
  };

  const fetchProjectJourney = async (projectId) => {
    try {
      const response = await getProjectJourney(projectId);
      setProjectJourney(response.data);
    } catch (error) {
      console.error('Error fetching project journey:', error);
      setError('Failed to fetch project journey');
    }
  };

  const handleProjectSelect = async (project) => {
    setSelectedProject(project);
    setProjectJourney(null);
    navigate(`/funding-journey/${project.id}`);
    await fetchProjectJourney(project.id);
  };

  // Get appropriate icon for each stage
  const getStageIcon = (stageCode, status) => {
    const iconProps = { 
      color: status === 'completed' ? 'success' : status === 'active' ? 'primary' : 'disabled'
    };
    
    switch(stageCode) {
      case 'deck_submission': return <Description {...iconProps} />;
      case 'video_upload': return <VideoLibrary {...iconProps} />;
      case 'gp_interview': return <People {...iconProps} />;
      case 'kyc_verification': return <Assignment {...iconProps} />;
      case 'due_diligence': return <Gavel {...iconProps} />;
      case 'term_sheet': return <Description {...iconProps} />;
      case 'publishing': return <Publish {...iconProps} />;
      case 'investor_commits': return <TrendingUp {...iconProps} />;
      case 'commit_complete': return <CheckCircle {...iconProps} />;
      case 'signing_vehicle': return <AccountBalance {...iconProps} />;
      case 'signing_startup': return <AccountBalance {...iconProps} />;
      case 'funding_collection': return <AttachMoney {...iconProps} />;
      case 'funding_transfer': return <AttachMoney {...iconProps} />;
      case 'round_closed': return <CheckCircle {...iconProps} />;
      default: return <RadioButtonUnchecked {...iconProps} />;
    }
  };

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

  useEffect(() => {
    fetchMyProjects();
  }, [projectId]);

  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4, display: 'flex', justifyContent: 'center' }}>
        <CircularProgress />
      </Container>
    );
  }

  if (error) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4 }}>
        <Alert severity="error">{error}</Alert>
      </Container>
    );
  }

  if (projects.length === 0) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4 }}>
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <Typography variant="h6" gutterBottom>No Projects Found</Typography>
          <Typography color="text.secondary">
            You don't have any funding projects yet. Upload a pitch deck to get started.
          </Typography>
        </Paper>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ mt: 4 }}>
      <Typography variant="h4" gutterBottom>Funding Journey</Typography>
      
      {/* Project Selection */}
      {projects.length > 1 && (
        <Paper sx={{ p: 3, mb: 3 }}>
          <Typography variant="h6" gutterBottom>Select Project</Typography>
          <Grid container spacing={2}>
            {projects.map((project) => (
              <Grid item xs={12} sm={6} md={4} key={project.id}>
                <Card 
                  sx={{ 
                    cursor: 'pointer',
                    border: selectedProject?.id === project.id ? 2 : 1,
                    borderColor: selectedProject?.id === project.id ? 'primary.main' : 'divider'
                  }}
                  onClick={() => handleProjectSelect(project)}
                >
                  <CardContent>
                    <Typography variant="h6" gutterBottom>
                      {project.project_name}
                    </Typography>
                    <Typography variant="body2" color="text.secondary" gutterBottom>
                      {project.company_id}
                    </Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 2 }}>
                      <LinearProgress 
                        variant="determinate" 
                        value={project.completion_percentage || 0}
                        sx={{ flexGrow: 1, height: 8, borderRadius: 4 }}
                      />
                      <Typography variant="body2" color="text.secondary">
                        {Math.round(project.completion_percentage || 0)}%
                      </Typography>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </Paper>
      )}

      {selectedProject && projectJourney && (
        <Grid container spacing={3}>
          {/* Progress Overview */}
          <Grid item xs={12}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                {selectedProject.project_name} - Progress Overview
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={6} sm={3}>
                  <Box sx={{ textAlign: 'center' }}>
                    <Typography variant="h3" color="primary">
                      {Math.round(projectJourney.completion_percentage)}%
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Complete
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={6} sm={3}>
                  <Box sx={{ textAlign: 'center' }}>
                    <Typography variant="h3" color="success.main">
                      {projectJourney.completed_stages}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Completed
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={6} sm={3}>
                  <Box sx={{ textAlign: 'center' }}>
                    <Typography variant="h3" color="primary">
                      {projectJourney.active_stages}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Active
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={6} sm={3}>
                  <Box sx={{ textAlign: 'center' }}>
                    <Typography variant="h3" color="text.secondary">
                      {projectJourney.pending_stages}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Pending
                    </Typography>
                  </Box>
                </Grid>
              </Grid>
              
              {/* Overall Progress Bar */}
              <Box sx={{ mt: 3 }}>
                <LinearProgress 
                  variant="determinate" 
                  value={projectJourney.completion_percentage}
                  sx={{ height: 12, borderRadius: 6 }}
                />
              </Box>
            </Paper>
          </Grid>

          {/* Funding Journey Stepper */}
          <Grid item xs={12}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>Funding Process Steps</Typography>
              <Stepper 
                activeStep={getActiveStep()} 
                orientation="vertical"
                sx={{ mt: 2 }}
              >
                {projectJourney.stages.map((stage) => (
                  <Step key={stage.id}>
                    <StepLabel 
                      icon={getStageIcon(stage.stage_code, stage.status)}
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
                        {stage.stage_metadata && Object.keys(stage.stage_metadata).length > 0 && (
                          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                            {stage.stage_metadata.description || 'Stage in progress'}
                          </Typography>
                        )}
                        
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
            </Paper>
          </Grid>
        </Grid>
      )}
    </Container>
  );
}

export default StartupJourney;