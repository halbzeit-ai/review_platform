import React, { useState, useEffect } from 'react';
import { Container, Typography, Grid, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Button, CircularProgress, Box, Snackbar, Alert, Tabs, Tab, Divider, LinearProgress, Chip, Dialog, DialogContent, DialogTitle, Select, MenuItem, FormControl, InputLabel, TextField } from '@mui/material';
import { Settings, Assignment, CleaningServices, Storage, People } from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { getPitchDecks, cleanupOrphanedDecks, getPerformanceMetrics, getAllProjects, getProjectJourney, updateStageStatus } from '../services/api';

function GPDashboard() {
  const { t } = useTranslation('dashboard');
  const navigate = useNavigate();
  const [pitchDecks, setPitchDecks] = useState([]);
  const [loadingDecks, setLoadingDecks] = useState(true);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' });
  const [cleanupLoading, setCleanupLoading] = useState(false);
  const [activeTab, setActiveTab] = useState(0);
  const [performanceMetrics, setPerformanceMetrics] = useState(null);
  const [projects, setProjects] = useState([]);
  const [loadingProjects, setLoadingProjects] = useState(false);
  const [includeTestData, setIncludeTestData] = useState(false);
  const [selectedProject, setSelectedProject] = useState(null);
  const [projectJourney, setProjectJourney] = useState(null);
  const [journeyDialogOpen, setJourneyDialogOpen] = useState(false);
  const [stageUpdateDialog, setStageUpdateDialog] = useState({ open: false, stage: null, projectId: null });


  const fetchPitchDecks = async () => {
    try {
      const response = await getPitchDecks();
      setPitchDecks(response.data.decks);
    } catch (error) {
      console.error('Error fetching pitch decks:', error);
    } finally {
      setLoadingDecks(false);
    }
  };

  const fetchPerformanceMetrics = async () => {
    try {
      const response = await getPerformanceMetrics();
      setPerformanceMetrics(response.data);
    } catch (error) {
      console.error('Error fetching performance metrics:', error);
    }
  };

  const fetchProjects = async () => {
    setLoadingProjects(true);
    try {
      const response = await getAllProjects(includeTestData);
      setProjects(response.data);
    } catch (error) {
      console.error('Error fetching projects:', error);
      setSnackbar({
        open: true,
        message: 'Error fetching projects: ' + (error.response?.data?.detail || error.message),
        severity: 'error'
      });
    } finally {
      setLoadingProjects(false);
    }
  };

  const handleViewProjectJourney = async (projectId) => {
    try {
      const response = await getProjectJourney(projectId);
      setProjectJourney(response.data);
      setSelectedProject(projectId);
      setJourneyDialogOpen(true);
    } catch (error) {
      console.error('Error fetching project journey:', error);
      setSnackbar({
        open: true,
        message: 'Error fetching project journey: ' + (error.response?.data?.detail || error.message),
        severity: 'error'
      });
    }
  };

  const handleUpdateStageStatus = async (status, completionNotes = '') => {
    try {
      await updateStageStatus(stageUpdateDialog.projectId, stageUpdateDialog.stage.id, {
        status,
        completion_notes: completionNotes
      });
      
      setSnackbar({
        open: true,
        message: `Stage updated to ${status}`,
        severity: 'success'
      });
      
      // Refresh the project journey
      await handleViewProjectJourney(stageUpdateDialog.projectId);
      setStageUpdateDialog({ open: false, stage: null, projectId: null });
    } catch (error) {
      console.error('Error updating stage status:', error);
      setSnackbar({
        open: true,
        message: 'Error updating stage: ' + (error.response?.data?.detail || error.message),
        severity: 'error'
      });
    }
  };

  const handleCleanupOrphanedDecks = async () => {
    setCleanupLoading(true);
    try {
      const response = await cleanupOrphanedDecks();
      
      setSnackbar({
        open: true,
        message: response.data.message || t('gp.adminActions.cleanupSuccess'),
        severity: 'success'
      });
      
      // Refresh the decks list
      await fetchPitchDecks();
      
    } catch (error) {
      console.error('Error cleaning up orphaned decks:', error);
      
      setSnackbar({
        open: true,
        message: `${t('gp.adminActions.cleanupError')}: ${error.response?.data?.detail || error.message}`,
        severity: 'error'
      });
    } finally {
      setCleanupLoading(false);
    }
  };

  useEffect(() => {
    fetchPitchDecks();
    fetchPerformanceMetrics();
    fetchProjects();
  }, [includeTestData]);

  // Helper function to get status color
  const getStatusColor = (status) => {
    switch (status) {
      case 'completed': return 'success';
      case 'active': return 'primary';
      case 'pending': return 'default';
      case 'skipped': return 'warning';
      default: return 'default';
    }
  };

  // Tab panel helper component
  const TabPanel = ({ children, value, index }) => (
    <div role="tabpanel" hidden={value !== index}>
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );

  // Performance metrics panel component
  const PerformanceMetricsPanel = () => (
    <Box>
      <Typography variant="h6" sx={{ mb: 3 }}>
        Template Performance Metrics
      </Typography>
      
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" sx={{ mb: 2 }}>
              Template Usage
            </Typography>
            {performanceMetrics?.template_performance?.map((template, index) => (
              <Box key={index} sx={{ mb: 1 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography variant="body2">{template.template_name}</Typography>
                  <Typography variant="body2">{template.usage_count} uses</Typography>
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography variant="caption" color="text.secondary">
                    Avg Confidence: {(template.avg_confidence * 100).toFixed(1)}%
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Avg Rating: {template.avg_rating.toFixed(1)}/5
                  </Typography>
                </Box>
                <Divider sx={{ my: 1 }} />
              </Box>
            ))}
          </Paper>
        </Grid>
        
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" sx={{ mb: 2 }}>
              Classification Accuracy
            </Typography>
            <Box sx={{ textAlign: 'center' }}>
              <Typography variant="h3" color="primary">
                {performanceMetrics?.classification_accuracy?.accuracy_percentage?.toFixed(1)}%
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Overall Accuracy
              </Typography>
              <Box sx={{ mt: 2 }}>
                <Typography variant="body2">
                  {performanceMetrics?.classification_accuracy?.accurate_classifications} accurate / {' '}
                  {performanceMetrics?.classification_accuracy?.total_classifications} total
                </Typography>
              </Box>
            </Box>
          </Paper>
        </Grid>
        
        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" sx={{ mb: 2 }}>
              Sector Distribution
            </Typography>
            <Grid container spacing={2}>
              {performanceMetrics?.sector_distribution?.map((sector, index) => (
                <Grid item xs={12} sm={6} md={3} key={index}>
                  <Box sx={{ textAlign: 'center' }}>
                    <Typography variant="h5" color="primary">
                      {sector.classification_count}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {sector.sector_name}
                    </Typography>
                  </Box>
                </Grid>
              ))}
            </Grid>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );

  // Projects Management panel component
  const ProjectsManagementPanel = () => (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h6">
          Projects & Funding Stages
        </Typography>
        <FormControl size="small" sx={{ minWidth: 200 }}>
          <InputLabel>Data Filter</InputLabel>
          <Select
            value={includeTestData ? 'all' : 'production'}
            label="Data Filter"
            onChange={(e) => setIncludeTestData(e.target.value === 'all')}
          >
            <MenuItem value="production">Production Only</MenuItem>
            <MenuItem value="all">Include Test Data</MenuItem>
          </Select>
        </FormControl>
      </Box>
      
      {loadingProjects ? (
        <CircularProgress />
      ) : projects.length === 0 ? (
        <Typography color="text.secondary">No projects found</Typography>
      ) : (
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Company</TableCell>
                <TableCell>Project</TableCell>
                <TableCell>Funding Round</TableCell>
                <TableCell>Progress</TableCell>
                <TableCell>Current Stage</TableCell>
                <TableCell>Documents</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {projects.map((project) => (
                <TableRow key={project.id}>
                  <TableCell>{project.company_id}</TableCell>
                  <TableCell>{project.project_name}</TableCell>
                  <TableCell>
                    <Chip 
                      label={project.funding_round || 'N/A'} 
                      size="small" 
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <LinearProgress 
                        variant="determinate" 
                        value={project.completion_percentage || 0}
                        sx={{ width: 100, height: 8, borderRadius: 4 }}
                      />
                      <Typography variant="body2" color="text.secondary">
                        {Math.round(project.completion_percentage || 0)}%
                      </Typography>
                    </Box>
                  </TableCell>
                  <TableCell>
                    {project.current_stage_name ? (
                      <Chip 
                        label={project.current_stage_name} 
                        color="primary" 
                        size="small"
                      />
                    ) : (
                      <Typography variant="body2" color="text.secondary">Not started</Typography>
                    )}
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">
                      {project.document_count || 0} docs
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Button
                      size="small"
                      variant="outlined"
                      onClick={() => handleViewProjectJourney(project.id)}
                    >
                      View Journey
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Box>
  );

  // Stage Update Dialog Component
  const StageUpdateDialog = () => {
    const [newStatus, setNewStatus] = useState('');
    const [completionNotes, setCompletionNotes] = useState('');
    
    return (
      <Dialog 
        open={stageUpdateDialog.open} 
        onClose={() => setStageUpdateDialog({ open: false, stage: null, projectId: null })}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          Update Stage: {stageUpdateDialog.stage?.stage_name}
        </DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 3 }}>
            <FormControl fullWidth>
              <InputLabel>New Status</InputLabel>
              <Select
                value={newStatus}
                label="New Status"
                onChange={(e) => setNewStatus(e.target.value)}
              >
                <MenuItem value="pending">Pending</MenuItem>
                <MenuItem value="active">Active</MenuItem>
                <MenuItem value="completed">Completed</MenuItem>
                <MenuItem value="skipped">Skipped</MenuItem>
              </Select>
            </FormControl>
            
            <TextField
              label="Completion Notes"
              multiline
              rows={3}
              value={completionNotes}
              onChange={(e) => setCompletionNotes(e.target.value)}
              placeholder="Add notes about this stage update..."
              fullWidth
            />
            
            <Box sx={{ display: 'flex', gap: 2, justifyContent: 'flex-end' }}>
              <Button 
                onClick={() => setStageUpdateDialog({ open: false, stage: null, projectId: null })}
              >
                Cancel
              </Button>
              <Button 
                variant="contained" 
                onClick={() => handleUpdateStageStatus(newStatus, completionNotes)}
                disabled={!newStatus}
              >
                Update Stage
              </Button>
            </Box>
          </Box>
        </DialogContent>
      </Dialog>
    );
  };

  // Project Journey Dialog Component  
  const ProjectJourneyDialog = () => (
    <Dialog 
      open={journeyDialogOpen} 
      onClose={() => setJourneyDialogOpen(false)}
      maxWidth="md"
      fullWidth
    >
      <DialogTitle>
        {projectJourney ? `${projectJourney.company_id} - ${projectJourney.project_name}` : 'Project Journey'}
      </DialogTitle>
      <DialogContent>
        {projectJourney && (
          <Box sx={{ pt: 2 }}>
            <Box sx={{ mb: 3 }}>
              <Typography variant="h6" gutterBottom>Progress Overview</Typography>
              <Grid container spacing={2}>
                <Grid item xs={3}>
                  <Paper sx={{ p: 2, textAlign: 'center' }}>
                    <Typography variant="h4" color="primary">
                      {Math.round(projectJourney.completion_percentage)}%
                    </Typography>
                    <Typography variant="body2" color="text.secondary">Complete</Typography>
                  </Paper>
                </Grid>
                <Grid item xs={3}>
                  <Paper sx={{ p: 2, textAlign: 'center' }}>
                    <Typography variant="h4" color="success.main">
                      {projectJourney.completed_stages}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">Completed</Typography>
                  </Paper>
                </Grid>
                <Grid item xs={3}>
                  <Paper sx={{ p: 2, textAlign: 'center' }}>
                    <Typography variant="h4" color="primary">
                      {projectJourney.active_stages}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">Active</Typography>
                  </Paper>
                </Grid>
                <Grid item xs={3}>
                  <Paper sx={{ p: 2, textAlign: 'center' }}>
                    <Typography variant="h4" color="text.secondary">
                      {projectJourney.pending_stages}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">Pending</Typography>
                  </Paper>
                </Grid>
              </Grid>
            </Box>
            
            <Typography variant="h6" gutterBottom>Funding Journey</Typography>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Stage</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Started</TableCell>
                    <TableCell>Completed</TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {projectJourney.stages.map((stage) => (
                    <TableRow key={stage.id}>
                      <TableCell>
                        <Box>
                          <Typography variant="body2" fontWeight="medium">
                            {stage.stage_name}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            Stage {stage.stage_order}
                          </Typography>
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Chip 
                          label={stage.status} 
                          color={getStatusColor(stage.status)}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">
                          {stage.started_at ? new Date(stage.started_at).toLocaleDateString() : '-'}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">
                          {stage.completed_at ? new Date(stage.completed_at).toLocaleDateString() : '-'}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Button
                          size="small"
                          variant="outlined"
                          onClick={() => setStageUpdateDialog({ 
                            open: true, 
                            stage: stage, 
                            projectId: projectJourney.project_id 
                          })}
                        >
                          Update
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Box>
        )}
      </DialogContent>
    </Dialog>
  );

  return (
    <Container maxWidth="lg" sx={{ mt: 4 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">{t('gp.title')}</Typography>
        <Box display="flex" gap={2}>
          <Button
            variant="outlined"
            startIcon={<People />}
            onClick={() => navigate('/users')}
          >
            Manage Users
          </Button>
          <Button
            variant="outlined"
            startIcon={<Assignment />}
            onClick={() => navigate('/templates')}
          >
            {t('gp.adminActions.analysisTemplates')}
          </Button>
          <Button
            variant="outlined"
            startIcon={<Storage />}
            onClick={() => navigate('/dojo')}
          >
            {t('gp.adminActions.dojo')}
          </Button>
          <Button
            variant="outlined"
            startIcon={<Settings />}
            onClick={() => navigate('/config')}
          >
            {t('gp.adminActions.modelConfiguration')}
          </Button>
          <Button
            variant="outlined"
            startIcon={<CleaningServices />}
            onClick={handleCleanupOrphanedDecks}
            disabled={cleanupLoading}
          >
            {cleanupLoading ? t('gp.adminActions.cleanupInProgress') : t('gp.adminActions.cleanupOrphanedData')}
          </Button>
        </Box>
      </Box>
      <Paper sx={{ mt: 3 }}>
        <Tabs value={activeTab} onChange={(e, newValue) => setActiveTab(newValue)} sx={{ borderBottom: 1, borderColor: 'divider', px: 3, pt: 2 }}>
          <Tab label={t('gp.reviewsSection.title')} />
          <Tab label="Projects & Funding" />
          <Tab label="Performance Metrics" />
        </Tabs>

        <TabPanel value={activeTab} index={0}>
          <Box sx={{ px: 3, pb: 3 }}>
            {loadingDecks ? (
              <CircularProgress />
            ) : pitchDecks.length === 0 ? (
              <Typography color="text.secondary">{t('gp.reviewsSection.noReviews')}</Typography>
            ) : (
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>{t('gp.reviewsSection.columns.deck')}</TableCell>
                      <TableCell>{t('gp.reviewsSection.columns.company')}</TableCell>
                      <TableCell>{t('common:forms.email')}</TableCell>
                      <TableCell>{t('gp.reviewsSection.columns.date')}</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {pitchDecks.map((deck) => (
                      <TableRow key={deck.id}>
                        <TableCell>{deck.file_name}</TableCell>
                        <TableCell>{deck.user?.company_name || 'N/A'}</TableCell>
                        <TableCell>{deck.user?.email || 'N/A'}</TableCell>
                        <TableCell>{new Date(deck.created_at).toLocaleDateString()}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </Box>
        </TabPanel>

        <TabPanel value={activeTab} index={1}>
          <Box sx={{ px: 3, pb: 3 }}>
            <ProjectsManagementPanel />
          </Box>
        </TabPanel>

        <TabPanel value={activeTab} index={2}>
          <Box sx={{ px: 3, pb: 3 }}>
            <PerformanceMetricsPanel />
          </Box>
        </TabPanel>
      </Paper>

      {/* Dialog Components */}
      <ProjectJourneyDialog />
      <StageUpdateDialog />

      {/* Success/Error Snackbar */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert
          onClose={() => setSnackbar({ ...snackbar, open: false })}
          severity={snackbar.severity}
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Container>
  );
}

export default GPDashboard;