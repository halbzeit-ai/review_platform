import React, { useState, useEffect } from 'react';
import { Container, Typography, Grid, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Button, CircularProgress, Box, Snackbar, Alert, Tabs, Tab, Divider, LinearProgress, Chip, Dialog, DialogContent, DialogTitle, Select, MenuItem, FormControl, InputLabel, TextField, Card, CardContent, CardMedia, List, ListItem, ListItemText } from '@mui/material';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import { Settings, Assignment, Storage, People } from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { getPerformanceMetrics, getAllProjects, getProjectJourney, updateStageStatus } from '../services/api';

function GPDashboard() {
  const { t } = useTranslation('dashboard');
  const navigate = useNavigate();
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' });
  const [activeTab, setActiveTab] = useState(0);
  const [performanceMetrics, setPerformanceMetrics] = useState(null);
  const [projects, setProjects] = useState([]);
  const [loadingProjects, setLoadingProjects] = useState(false);
  const [includeTestData, setIncludeTestData] = useState(() => {
    // Persist the setting in localStorage
    const saved = localStorage.getItem('gp_dashboard_include_test_data');
    return saved ? JSON.parse(saved) : false;
  });

  // Update localStorage when includeTestData changes
  useEffect(() => {
    localStorage.setItem('gp_dashboard_include_test_data', JSON.stringify(includeTestData));
  }, [includeTestData]);
  const [classificationData, setClassificationData] = useState([]);
  const [selectedProject, setSelectedProject] = useState(null);
  const [projectJourney, setProjectJourney] = useState(null);
  const [journeyDialogOpen, setJourneyDialogOpen] = useState(false);
  const [stageUpdateDialog, setStageUpdateDialog] = useState({ open: false, stage: null, projectId: null });



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

  const handleOpenProject = (projectId) => {
    // Navigate to startup view of the project for GP
    navigate(`/admin/project/${projectId}/startup-view`);
  };

  useEffect(() => {
    fetchPerformanceMetrics();
    fetchProjects();
  }, [includeTestData]);

  // Process projects data to create classification distribution for pie chart
  useEffect(() => {
    if (projects.length > 0) {
      const classificationCounts = {};
      
      projects.forEach(project => {
        try {
          // Handle both cases: metadata as object (from API) or JSON string (legacy)
          const metadata = typeof project.project_metadata === 'object' 
                            ? project.project_metadata 
                            : JSON.parse(project.project_metadata || '{}');
          const classification = metadata.classification?.primary_sector || 'N/A';
          classificationCounts[classification] = (classificationCounts[classification] || 0) + 1;
        } catch (e) {
          classificationCounts['N/A'] = (classificationCounts['N/A'] || 0) + 1;
        }
      });

      // Convert to array format for pie chart
      const chartData = Object.entries(classificationCounts).map(([name, value]) => ({
        name,
        value,
        percentage: ((value / projects.length) * 100).toFixed(1)
      }));

      setClassificationData(chartData);
    } else {
      setClassificationData([]);
    }
  }, [projects]);

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

  // Performance metrics panel component with pie chart
  const PerformanceMetricsPanel = () => {
    // Define colors for the pie chart
    const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8', '#82CA9D', '#FFC658', '#FF7C7C'];
    
    const renderCustomizedLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent }) => {
      if (percent < 0.05) return null; // Don't show label for slices < 5%
      const RADIAN = Math.PI / 180;
      const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
      const x = cx + radius * Math.cos(-midAngle * RADIAN);
      const y = cy + radius * Math.sin(-midAngle * RADIAN);

      return (
        <text 
          x={x} 
          y={y} 
          fill="white" 
          textAnchor={x > cx ? 'start' : 'end'} 
          dominantBaseline="central"
          fontSize="12"
          fontWeight="bold"
        >
          {`${(percent * 100).toFixed(0)}%`}
        </text>
      );
    };

    return (
      <Box>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Typography variant="h6">
            Classification Distribution
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
        
        {classificationData.length === 0 ? (
          <Paper sx={{ p: 4, textAlign: 'center' }}>
            <Typography color="text.secondary">
              No classification data available
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              {projects.length === 0 ? 'No projects found' : 'Projects do not have classification data'}
            </Typography>
          </Paper>
        ) : (
          <Paper sx={{ p: 3 }}>
            <Grid container spacing={3}>
              <Grid item xs={12} md={8}>
                <Box sx={{ height: 400, display: 'flex', justifyContent: 'center' }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={classificationData}
                        cx="50%"
                        cy="50%"
                        labelLine={false}
                        label={renderCustomizedLabel}
                        outerRadius={140}
                        fill="#8884d8"
                        dataKey="value"
                      >
                        {classificationData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip formatter={(value, name) => [`${value} projects`, name]} />
                    </PieChart>
                  </ResponsiveContainer>
                </Box>
              </Grid>
              
              <Grid item xs={12} md={4}>
                <Typography variant="h6" sx={{ mb: 2 }}>
                  Summary
                </Typography>
                <List dense>
                  {classificationData.map((item, index) => (
                    <ListItem key={index}>
                      <Box
                        sx={{
                          width: 16,
                          height: 16,
                          backgroundColor: COLORS[index % COLORS.length],
                          borderRadius: '50%',
                          mr: 2
                        }}
                      />
                      <ListItemText
                        primary={item.name}
                        secondary={`${item.value} projects (${item.percentage}%)`}
                      />
                    </ListItem>
                  ))}
                </List>
                
                <Divider sx={{ my: 2 }} />
                
                <Box>
                  <Typography variant="body2" color="text.secondary">
                    Total Projects: <strong>{projects.length}</strong>
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Data Source: <strong>{includeTestData ? 'Production + Test' : 'Production Only'}</strong>
                  </Typography>
                </Box>
              </Grid>
            </Grid>
          </Paper>
        )}
      </Box>
    );
  };

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

  // Gallery Panel Component
  const GalleryPanel = () => {
    // Parse project metadata to get classification info
    const getClassificationInfo = (project) => {
      try {
        // Handle both cases: metadata as object (from API) or JSON string (legacy)
        const metadata = typeof project.project_metadata === 'object' 
                          ? project.project_metadata 
                          : JSON.parse(project.project_metadata || '{}');
        return metadata.classification?.primary_sector || 'N/A';
      } catch (e) {
        return 'N/A';
      }
    };

    // Get first document with pitch deck for thumbnail
    const getDeckThumbnail = (project) => {
      const pitchDeck = project.documents?.find(doc => doc.document_type === 'pitch_deck');
      if (pitchDeck) {
        // Use the actual deck document path to generate thumbnail
        return `/api/documents/${pitchDeck.id}/thumbnail/slide/1`;
      }
      // Return empty placeholder if no deck document exists
      return null;
    };

    return (
      <Box>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Typography variant="h6">
            Project Gallery
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
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress />
          </Box>
        ) : projects.length === 0 ? (
          <Typography color="text.secondary" sx={{ textAlign: 'center', py: 4 }}>
            No projects found
          </Typography>
        ) : (
          <Grid container spacing={3}>
            {projects.map((project) => (
              <Grid item xs={12} sm={6} md={4} lg={3} key={project.id}>
                <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                  {/* Deck Thumbnail */}
                  {getDeckThumbnail(project) ? (
                    <CardMedia
                      component="img"
                      height="160"
                      image={getDeckThumbnail(project)}
                      alt={`${project.company_id} pitch deck`}
                      sx={{ 
                        objectFit: 'cover',
                        backgroundColor: 'grey.200'
                      }}
                      onError={(e) => {
                        // Fallback to placeholder if thumbnail fails
                        e.target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzIwIiBoZWlnaHQ9IjE2MCIgdmlld0JveD0iMCAwIDMyMCAxNjAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSIzMjAiIGhlaWdodD0iMTYwIiBmaWxsPSIjRjVGNUY1Ii8+CjxwYXRoIGQ9Ik0gMTYwIDgwIEwgMTQwIDcwIEwgMTQwIDkwIFoiIGZpbGw9IiM5RTlFOUUiLz4KPHN2Zz4K';
                      }}
                    />
                  ) : (
                    <Box
                      sx={{
                        height: 160,
                        backgroundColor: 'grey.100',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexDirection: 'column'
                      }}
                    >
                      <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center' }}>
                        No Deck Available
                      </Typography>
                      <Typography variant="caption" color="text.secondary" sx={{ textAlign: 'center', mt: 1 }}>
                        Run template processing to generate thumbnails
                      </Typography>
                    </Box>
                  )}
                  
                  <CardContent sx={{ flexGrow: 1, p: 2 }}>
                    {/* Company Name and Classification Row */}
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                      <Typography variant="h6" component="h3" sx={{ fontSize: '1rem', fontWeight: 600 }}>
                        {project.company_id}
                      </Typography>
                      <Chip 
                        label={getClassificationInfo(project)} 
                        size="small" 
                        variant="outlined"
                        sx={{ fontSize: '0.75rem' }}
                      />
                    </Box>
                    
                    {/* Company Offering */}
                    <Typography 
                      variant="body2" 
                      color="text.secondary" 
                      sx={{ 
                        mb: 2, 
                        display: '-webkit-box',
                        WebkitLineClamp: 3,
                        WebkitBoxOrient: 'vertical',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        minHeight: '3.6em' // Reserve space for 3 lines
                      }}
                    >
                      {project.company_offering || 'No offering description available'}
                    </Typography>
                    
                    {/* Funding Sought */}
                    <Box sx={{ mt: 'auto' }}>
                      <Typography variant="body2" color="primary" sx={{ fontWeight: 500 }}>
                        Funding: {project.funding_sought || 'N/A'}
                      </Typography>
                    </Box>
                    
                    {/* Action Buttons */}
                    <Box sx={{ mt: 2, pt: 2, borderTop: 1, borderColor: 'divider' }}>
                      <Button
                        variant="contained"
                        size="small"
                        fullWidth
                        onClick={() => handleOpenProject(project.id)}
                        sx={{ textTransform: 'none' }}
                      >
                        Open Project
                      </Button>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        )}
      </Box>
    );
  };

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
        </Box>
      </Box>
      <Paper sx={{ mt: 3 }}>
        <Tabs value={activeTab} onChange={(e, newValue) => setActiveTab(newValue)} sx={{ borderBottom: 1, borderColor: 'divider', px: 3, pt: 2 }}>
          <Tab label="Performance Metrics" />
          <Tab label="Projects & Funding" />
          <Tab label="Gallery" />
        </Tabs>

        <TabPanel value={activeTab} index={0}>
          <Box sx={{ px: 3, pb: 3 }}>
            <PerformanceMetricsPanel />
          </Box>
        </TabPanel>

        <TabPanel value={activeTab} index={1}>
          <Box sx={{ px: 3, pb: 3 }}>
            <ProjectsManagementPanel />
          </Box>
        </TabPanel>

        <TabPanel value={activeTab} index={2}>
          <Box sx={{ px: 3, pb: 3 }}>
            <GalleryPanel />
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