import React, { useState, useEffect, useCallback, useRef } from 'react';
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
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Breadcrumbs,
  Link,
  Alert,
  CircularProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  ListItemSecondaryAction,
  Divider,
  Badge
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  Edit as EditIcon,
  FileCopy as CopyIcon,
  Add as AddIcon,
  Assessment as AssessmentIcon,
  Science as ScienceIcon,
  LocalHospital as LocalHospitalIcon,
  Psychology as PsychologyIcon,
  Computer as ComputerIcon,
  Analytics as AnalyticsIcon,
  FitnessCenter as FitnessIcon,
  Storefront as StorefrontIcon,
  Settings as SettingsIcon,
  Visibility as VisibilityIcon
} from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import PromptEditor from '../components/PromptEditor';

import { 
  getHealthcareSectors, 
  getSectorTemplates, 
  getTemplateDetails,
  getPerformanceMetrics,
  customizeTemplate,
  getMyCustomizations,
  getPipelinePrompts,
  getPipelinePromptByStage,
  updatePipelinePrompt,
  resetPipelinePrompt,
  getPipelineStages
} from '../services/api';

const TemplateManagement = () => {
  const { t } = useTranslation('templates');
  const navigate = useNavigate();
  
  const [activeTab, setActiveTab] = useState(0);
  const [sectors, setSectors] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [selectedSector, setSelectedSector] = useState(null);
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [templateDetails, setTemplateDetails] = useState(null);
  const [performanceMetrics, setPerformanceMetrics] = useState(null);
  const [customizations, setCustomizations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Pipeline configuration state
  const [pipelinePrompts, setPipelinePrompts] = useState({});
  const [selectedPromptStage, setSelectedPromptStage] = useState('image_analysis');
  const [promptTexts, setPromptTexts] = useState({
    image_analysis: '',
    offering_extraction: '',
    startup_name_extraction: ''
  });
  const [promptLoading, setPromptLoading] = useState(false);
  const [promptError, setPromptError] = useState(null);
  
  
  
  // Dialog states
  const [templateDialogOpen, setTemplateDialogOpen] = useState(false);
  const [customizeDialogOpen, setCustomizeDialogOpen] = useState(false);
  
  const [breadcrumbs, setBreadcrumbs] = useState([
    { label: t('navigation.dashboard'), path: '/dashboard' },
    { label: t('configuration.title'), path: '/configuration' },
    { label: t('templates.title'), path: '/templates' }
  ]);

  // Sector icons mapping
  const sectorIcons = {
    'digital_therapeutics': <PsychologyIcon />,
    'healthcare_infrastructure': <ComputerIcon />,
    'telemedicine': <LocalHospitalIcon />,
    'diagnostics_devices': <ScienceIcon />,
    'biotech_pharma': <ScienceIcon />,
    'health_data_ai': <AnalyticsIcon />,
    'consumer_health': <FitnessIcon />,
    'healthcare_marketplaces': <StorefrontIcon />
  };

  useEffect(() => {
    loadInitialData();
  }, []);




  const loadInitialData = useCallback(async () => {
    try {
      setLoading(true);
      const [sectorsResponse, metricsResponse, customizationsResponse, pipelineResponse] = await Promise.all([
        getHealthcareSectors(),
        getPerformanceMetrics(),
        getMyCustomizations(),
        getPipelinePrompts()
      ]);
      
      // Extract data from API responses
      const sectorsData = sectorsResponse.data || sectorsResponse;
      const metricsData = metricsResponse.data || metricsResponse;
      const customizationsData = customizationsResponse.data || customizationsResponse;
      const pipelineData = pipelineResponse.data || pipelineResponse;
      
      
      setSectors(Array.isArray(sectorsData) ? sectorsData : []);
      setPerformanceMetrics(metricsData);
      setCustomizations(Array.isArray(customizationsData) ? customizationsData : []);
      setPipelinePrompts(pipelineData.prompts || {});
      
      // Set initial prompt texts for all stages
      const prompts = pipelineData.prompts || {};
      setPromptTexts({
        image_analysis: prompts.image_analysis || '',
        offering_extraction: prompts.offering_extraction || '',
        startup_name_extraction: prompts.startup_name_extraction || ''
      });
      
      // Load templates for first sector by default
      if (sectorsData && sectorsData.length > 0) {
        await loadSectorTemplates(sectorsData[0]);
      }
    } catch (err) {
      console.error('Error loading initial data:', err);
      if (err.response?.status === 401 || err.response?.status === 403) {
        // Authentication error - redirect to login
        localStorage.removeItem('user');
        navigate('/login');
      } else {
        setError(err.response?.data?.detail || err.message || 'Failed to load data');
      }
    } finally {
      setLoading(false);
    }
  }, [navigate]);

  const loadSectorTemplates = async (sector) => {
    try {
      setSelectedSector(sector);
      const templatesResponse = await getSectorTemplates(sector.id);
      const templatesData = templatesResponse.data || templatesResponse;
      setTemplates(Array.isArray(templatesData) ? templatesData : []);
      
      // Update breadcrumbs
      setBreadcrumbs([
        { label: t('navigation.dashboard'), path: '/dashboard' },
        { label: t('configuration.title'), path: '/configuration' },
        { label: t('templates.title'), path: '/templates' },
        { label: sector.display_name, path: null }
      ]);
    } catch (err) {
      console.error('Error loading sector templates:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to load templates');
      setTemplates([]);
    }
  };

  const loadTemplateDetails = async (template) => {
    try {
      setSelectedTemplate(template);
      const detailsResponse = await getTemplateDetails(template.id);
      const details = detailsResponse.data || detailsResponse;
      setTemplateDetails(details);
      setTemplateDialogOpen(true);
    } catch (err) {
      console.error('Error loading template details:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to load template details');
    }
  };

  const handleEditSectorTemplate = async (sector) => {
    try {
      // Load templates for this sector
      await loadSectorTemplates(sector);
      
      // Get the default template for this sector
      const templatesResponse = await getSectorTemplates(sector.id);
      const templatesData = templatesResponse.data || templatesResponse;
      const templates = Array.isArray(templatesData) ? templatesData : [];
      
      // Find the default template or get the first one
      const defaultTemplate = templates.find(t => t.is_default) || templates[0];
      
      if (defaultTemplate) {
        // Load and show template details for editing
        await loadTemplateDetails(defaultTemplate);
      } else {
        setError('No template found for this sector');
      }
    } catch (err) {
      console.error('Error editing sector template:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to load sector template for editing');
    }
  };

  const handleCustomizeTemplate = async (templateId, customizationData) => {
    try {
      await customizeTemplate({
        base_template_id: templateId,
        customization_name: customizationData.name,
        customized_chapters: customizationData.chapters,
        customized_questions: customizationData.questions,
        customized_weights: customizationData.weights
      });
      
      // Reload customizations
      const customizationsData = await getMyCustomizations();
      setCustomizations(customizationsData);
      setCustomizeDialogOpen(false);
    } catch (err) {
      setError(err.message);
    }
  };

  // Pipeline prompt management functions
  const handlePromptStageChange = async (stageName) => {
    try {
      setSelectedPromptStage(stageName);
      setPromptLoading(true);
      setPromptError(null);
      
      const response = await getPipelinePromptByStage(stageName);
      const promptData = response.data || response;
      const newPromptText = promptData.prompt_text || '';
      setPromptTexts(prev => ({
        ...prev,
        [stageName]: newPromptText
      }));
      
    } catch (err) {
      console.error('Error loading prompt:', err);
      setPromptError(err.response?.data?.detail || err.message || 'Failed to load prompt');
    } finally {
      setPromptLoading(false);
    }
  };

  const handleSavePrompt = async () => {
    try {
      setPromptLoading(true);
      setPromptError(null);
      
      const currentPromptText = promptTexts[selectedPromptStage];
      await updatePipelinePrompt(selectedPromptStage, currentPromptText);
      
      // Update local state
      setPipelinePrompts(prev => ({
        ...prev,
        [selectedPromptStage]: currentPromptText
      }));
      
      setError(null);
      // Show success message briefly
      setTimeout(() => setPromptError(null), 3000);
      
    } catch (err) {
      console.error('Error saving prompt:', err);
      setPromptError(err.response?.data?.detail || err.message || 'Failed to save prompt');
    } finally {
      setPromptLoading(false);
    }
  };

  const handleResetPrompt = async () => {
    try {
      setPromptLoading(true);
      setPromptError(null);
      
      const response = await resetPipelinePrompt(selectedPromptStage);
      const resetData = response.data || response;
      
      // Update local state with reset prompt
      const newPromptText = resetData.default_prompt || '';
      setPromptTexts(prev => ({
        ...prev,
        [selectedPromptStage]: newPromptText
      }));
      setPipelinePrompts(prev => ({
        ...prev,
        [selectedPromptStage]: newPromptText
      }));
      
      setError(null);
      
    } catch (err) {
      console.error('Error resetting prompt:', err);
      setPromptError(err.response?.data?.detail || err.message || 'Failed to reset prompt');
    } finally {
      setPromptLoading(false);
    }
  };

  const TabPanel = ({ children, value, index }) => (
    <div hidden={value !== index}>
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );

  const SectorCard = ({ sector, onSelect, onEdit }) => (
    <Card 
      sx={{ 
        transition: 'all 0.2s',
        '&:hover': { 
          transform: 'translateY(-2px)',
          boxShadow: 3 
        },
        border: selectedSector?.id === sector.id ? 2 : 1,
        borderColor: selectedSector?.id === sector.id ? 'primary.main' : 'grey.300'
      }}
    >
      <CardContent sx={{ cursor: 'pointer' }} onClick={() => onSelect(sector)}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          {sectorIcons[sector.name] || <SettingsIcon />}
          <Typography variant="h6" sx={{ ml: 1 }}>
            {sector.display_name}
          </Typography>
        </Box>
        
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {sector.description}
        </Typography>
        
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="caption" color="text.secondary">
            {sector.subcategories.length} subcategories
          </Typography>
          <Chip 
            label={`${(sector.confidence_threshold * 100).toFixed(0)}% threshold`}
            size="small"
            color="info"
          />
        </Box>
      </CardContent>
      
      <CardActions>
        <Button 
          size="small" 
          startIcon={<EditIcon />}
          onClick={(e) => {
            e.stopPropagation();
            onEdit(sector);
          }}
        >
          Edit Template
        </Button>
      </CardActions>
    </Card>
  );

  const TemplateCard = ({ template, onEdit, onCustomize, onPreview }) => (
    <Card sx={{ height: '100%' }}>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
          <Typography variant="h6">
            {template.name}
          </Typography>
          <Box sx={{ display: 'flex', gap: 1 }}>
            {template.is_default && (
              <Chip label={t('labels.default')} size="small" color="primary" />
            )}
            <Badge badgeContent={template.usage_count} color="secondary">
              <AssessmentIcon />
            </Badge>
          </Box>
        </Box>
        
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {template.description}
        </Typography>
        
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mb: 2 }}>
          {template.specialized_analysis.map((analysis, index) => (
            <Chip 
              key={index} 
              label={analysis.replace('_', ' ')} 
              size="small" 
              variant="outlined"
              color="secondary"
            />
          ))}
        </Box>
        
        <Typography variant="caption" color="text.secondary">
          Version {template.template_version} • Used {template.usage_count} times
        </Typography>
      </CardContent>
      
      <CardActions>
        <Button 
          size="small" 
          startIcon={<VisibilityIcon />}
          onClick={() => onPreview(template)}
        >
          Preview
        </Button>
        <Button 
          size="small" 
          startIcon={<EditIcon />}
          onClick={() => onEdit(template)}
        >
          Edit
        </Button>
        <Button 
          size="small" 
          startIcon={<CopyIcon />}
          onClick={() => onCustomize(template)}
        >
          {t('buttons.customize')}
        </Button>
      </CardActions>
    </Card>
  );

  const TemplateDetailsDialog = () => (
    <Dialog 
      open={templateDialogOpen} 
      onClose={() => setTemplateDialogOpen(false)}
      maxWidth="md"
      fullWidth
    >
      <DialogTitle>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h6">
            {selectedTemplate?.name}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {templateDetails?.template?.sector_display_name}
          </Typography>
        </Box>
      </DialogTitle>
      
      <DialogContent>
        {templateDetails && templateDetails.template && (
          <Box>
            <Typography variant="body2" sx={{ mb: 3 }}>
              {templateDetails.template.description || 'No description available'}
            </Typography>
            
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 3 }}>
              {(templateDetails.template.specialized_analysis || []).map((analysis, index) => (
                <Chip 
                  key={index} 
                  label={analysis.replace('_', ' ')} 
                  size="small" 
                  color="secondary"
                />
              ))}
            </Box>

            {/* Keywords Section */}
            {selectedSector && selectedSector.keywords && (
              <Box sx={{ mb: 3 }}>
                <Typography variant="h6" sx={{ mb: 1 }}>
                  Sector Keywords ({selectedSector.keywords.length})
                </Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                  {selectedSector.keywords.map((keyword, index) => (
                    <Chip 
                      key={index} 
                      label={keyword}
                      size="small" 
                      variant="outlined"
                      color="primary"
                    />
                  ))}
                </Box>
                <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                  These keywords help identify companies in this sector during classification
                </Typography>
              </Box>
            )}

            {/* Subcategories Section */}
            {selectedSector && selectedSector.subcategories && (
              <Box sx={{ mb: 3 }}>
                <Typography variant="h6" sx={{ mb: 1 }}>
                  Subcategories ({selectedSector.subcategories.length})
                </Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                  {selectedSector.subcategories.map((subcategory, index) => (
                    <Chip 
                      key={index} 
                      label={subcategory}
                      size="small" 
                      variant="outlined"
                      color="info"
                    />
                  ))}
                </Box>
              </Box>
            )}
            
            <Typography variant="h6" sx={{ mb: 2 }}>
              Analysis Chapters ({templateDetails.chapters ? templateDetails.chapters.length : 0})
            </Typography>
            
            {(!templateDetails.chapters || templateDetails.chapters.length === 0) ? (
              <Alert severity="info" sx={{ mb: 2 }}>
                No chapters configured for this template. This template needs to be set up with analysis chapters and questions.
              </Alert>
            ) : (
              (templateDetails.chapters || []).map((chapter, index) => (
              <Accordion key={chapter.id} sx={{ mb: 1 }}>
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                  <Box sx={{ display: 'flex', alignItems: 'center', width: '100%' }}>
                    <Typography variant="subtitle1" sx={{ flexGrow: 1 }}>
                      {chapter.name}
                    </Typography>
                    <Chip 
                      label={`Weight: ${chapter.weight}`}
                      size="small"
                      variant="outlined"
                      sx={{ mr: 1 }}
                    />
                    <Chip 
                      label={`${chapter.questions.length} questions`}
                      size="small"
                      color="info"
                    />
                  </Box>
                </AccordionSummary>
                
                <AccordionDetails>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    {chapter.description}
                  </Typography>
                  
                  <List dense>
                    {chapter.questions.map((question, qIndex) => (
                      <ListItem key={question.id} sx={{ pl: 0 }}>
                        <ListItemText
                          primary={question.question_text}
                          secondary={
                            <Box>
                              <Typography variant="caption" color="text.secondary">
                                {question.scoring_criteria}
                              </Typography>
                              <br />
                              <Typography variant="caption" color="primary">
                                {t('labels.healthcareFocus')}: {question.healthcare_focus}
                              </Typography>
                            </Box>
                          }
                        />
                        <ListItemSecondaryAction>
                          <Chip 
                            label={`Weight: ${question.weight}`}
                            size="small"
                            variant="outlined"
                          />
                        </ListItemSecondaryAction>
                      </ListItem>
                    ))}
                  </List>
                </AccordionDetails>
              </Accordion>
            )))}
          </Box>
        )}
      </DialogContent>
      
      <DialogActions>
        <Button onClick={() => setTemplateDialogOpen(false)}>
          Close
        </Button>
        <Button 
          variant="contained" 
          onClick={() => {
            setTemplateDialogOpen(false);
            setCustomizeDialogOpen(true);
          }}
        >
          Customize Template
        </Button>
      </DialogActions>
    </Dialog>
  );

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

  const PipelineSettingsContent = () => {
    const extractionTypes = [
      {
        key: 'image_analysis',
        name: t('labels.imageAnalysisPrompt'),
        description: t('pipeline.imageAnalysisDescription'),
        icon: <VisibilityIcon />
      },
      {
        key: 'offering_extraction',
        name: t('labels.companyOfferingPrompt'),
        description: t('pipeline.companyOfferingDescription'),
        icon: <StorefrontIcon />
      },
      {
        key: 'startup_name_extraction',
        name: 'Startup Name Extraction',
        description: 'Extract the startup name from pitch deck content',
        icon: <StorefrontIcon />
      }
    ];

    return (
      <Box>
        <Typography variant="h5" sx={{ mb: 3 }}>
          {t('pipeline.title')}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 4 }}>
          {t('pipeline.description')}
        </Typography>

        <Grid container spacing={3}>
          {/* Extraction Type Selector */}
          <Grid item xs={12} md={3}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" sx={{ mb: 2 }}>
                Extraction Types
              </Typography>
              <List>
                {extractionTypes.map((type) => (
                  <ListItem
                    key={type.key}
                    button
                    selected={selectedPromptStage === type.key}
                    onClick={() => setSelectedPromptStage(type.key)}
                    sx={{
                      borderRadius: 1,
                      mb: 1,
                      '&.Mui-selected': {
                        backgroundColor: 'primary.50',
                        borderLeft: 3,
                        borderLeftColor: 'primary.main'
                      }
                    }}
                  >
                    <ListItemIcon sx={{ minWidth: 40 }}>
                      {type.icon}
                    </ListItemIcon>
                    <ListItemText
                      primary={type.name}
                      secondary={type.key === 'image_analysis' ? 'Vision AI' : 'Text Processing'}
                    />
                  </ListItem>
                ))}
              </List>
            </Paper>
          </Grid>

          {/* Prompt Editor */}
          <Grid item xs={12} md={9}>
            <Paper sx={{ p: 3 }}>
              {(() => {
                const currentType = extractionTypes.find(t => t.key === selectedPromptStage);
                return (
                  <>
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                      {currentType?.icon}
                      <Typography variant="h6" sx={{ ml: 1 }}>
                        {currentType?.name}
                      </Typography>
                    </Box>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                      {currentType?.description}
                    </Typography>

                    <PromptEditor
                      initialPrompt={promptTexts[selectedPromptStage]}
                      stageName={selectedPromptStage}
                      onSave={(newText) => {
                        setPromptTexts(prev => ({
                          ...prev,
                          [selectedPromptStage]: newText
                        }));
                        setPipelinePrompts(prev => ({
                          ...prev,
                          [selectedPromptStage]: newText
                        }));
                      }}
                    />

                    <Alert severity="info" sx={{ mt: 2 }}>
                      Changes to prompts will affect all new PDF processing. 
                      Existing analyses will not be reprocessed.
                    </Alert>
                  </>
                );
              })()}
            </Paper>
          </Grid>
        </Grid>
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

      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">
          {t('title')}
        </Typography>
        <Button 
          variant="contained" 
          startIcon={<AddIcon />}
          onClick={() => setCustomizeDialogOpen(true)}
        >
          {t('buttons.createCustomTemplate')}
        </Button>
      </Box>

      {/* Error Alert */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Main Content */}
      <Paper sx={{ width: '100%' }}>
        <Tabs value={activeTab} onChange={(e, newValue) => setActiveTab(newValue)}>
          <Tab label={t('tabs.healthcareSectors')} />
          <Tab label={t('tabs.templateLibrary')} />
          <Tab label={t('tabs.myCustomizations')} />
          <Tab label={t('tabs.performanceMetrics')} />
          <Tab label={t('tabs.obligatoryExtractions')} />
        </Tabs>

        <TabPanel value={activeTab} index={0}>
          <Grid container spacing={3}>
            {sectors.map((sector) => (
              <Grid item xs={12} md={6} lg={4} key={sector.id}>
                <SectorCard 
                  sector={sector} 
                  onSelect={loadSectorTemplates}
                  onEdit={handleEditSectorTemplate}
                />
              </Grid>
            ))}
            <Grid item xs={12} md={6} lg={4}>
              <Card 
                sx={{ 
                  height: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  '&:hover': { 
                    transform: 'translateY(-2px)',
                    boxShadow: 3,
                    bgcolor: 'action.hover'
                  },
                  border: 2,
                  borderStyle: 'dashed',
                  borderColor: 'primary.main',
                  minHeight: 200
                }}
                onClick={() => setCustomizeDialogOpen(true)}
              >
                <Box sx={{ textAlign: 'center', p: 3 }}>
                  <AddIcon sx={{ fontSize: 48, color: 'primary.main', mb: 1 }} />
                  <Typography variant="h6" color="primary.main">
                    Add New Template
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Create a custom healthcare template
                  </Typography>
                </Box>
              </Card>
            </Grid>
          </Grid>
        </TabPanel>

        <TabPanel value={activeTab} index={1}>
          {selectedSector && (
            <Box>
              <Typography variant="h6" sx={{ mb: 2 }}>
                {selectedSector.display_name} Templates
              </Typography>
              <Grid container spacing={3}>
                {templates.map((template) => (
                  <Grid item xs={12} md={6} lg={4} key={template.id}>
                    <TemplateCard 
                      template={template}
                      onEdit={loadTemplateDetails}
                      onCustomize={(template) => {
                        setSelectedTemplate(template);
                        setCustomizeDialogOpen(true);
                      }}
                      onPreview={loadTemplateDetails}
                    />
                  </Grid>
                ))}
              </Grid>
            </Box>
          )}
        </TabPanel>

        <TabPanel value={activeTab} index={2}>
          <Box>
            <Typography variant="h6" sx={{ mb: 2 }}>
              My Template Customizations
            </Typography>
            {customizations.length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                No customizations yet. Create your first custom template!
              </Typography>
            ) : (
              <Grid container spacing={3}>
                {customizations.map((customization) => (
                  <Grid item xs={12} md={6} lg={4} key={customization.id}>
                    <Card>
                      <CardContent>
                        <Typography variant="h6">
                          {customization.customization_name}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Based on: {customization.template_name}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Sector: {customization.sector_name}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          Created: {new Date(customization.created_at).toLocaleDateString()}
                        </Typography>
                      </CardContent>
                      <CardActions>
                        <Button size="small" startIcon={<EditIcon />}>
                          Edit
                        </Button>
                        <Button size="small" startIcon={<CopyIcon />}>
                          Duplicate
                        </Button>
                      </CardActions>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            )}
          </Box>
        </TabPanel>

        <TabPanel value={activeTab} index={3}>
          <PerformanceMetricsPanel />
        </TabPanel>

        <TabPanel value={activeTab} index={4}>
          <PipelineSettingsContent />
        </TabPanel>
      </Paper>

      {/* Dialogs */}
      <TemplateDetailsDialog />
      
      {/* Template Customization Dialog */}
      <Dialog 
        open={customizeDialogOpen} 
        onClose={() => setCustomizeDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          {t('labels.customizeTemplateTitle')}: {selectedTemplate?.name}
        </DialogTitle>
        <DialogContent>
          <Typography variant="body2" sx={{ mb: 2 }}>
            Create a customized version of this template with your own questions, weights, and analysis focus.
          </Typography>
          <TextField
            fullWidth
            label={t('labels.customizationName')}
            placeholder={t('labels.placeholderCustomTemplate')}
            sx={{ mb: 2 }}
          />
          <Typography variant="body2" color="text.secondary">
            Advanced customization options will be available in the detailed editor.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCustomizeDialogOpen(false)}>
            {t('buttons.cancel')}
          </Button>
          <Button variant="contained">
            {t('buttons.saveCustomization')}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default TemplateManagement;