import React, { useState, useEffect, useCallback } from 'react';
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
  Divider,
  Badge
} from '@mui/material';
import {
  Edit as EditIcon,
  FileCopy as CopyIcon,
  Add as AddIcon,
  Assessment as AssessmentIcon,
} from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

import { 
  getHealthcareSectors, 
  getSectorTemplates, 
  getTemplateDetails,
  getPerformanceMetrics,
  customizeTemplate
} from '../services/api';

const TemplateManagement = () => {
  const { t } = useTranslation('templates');
  const navigate = useNavigate();
  
  const [activeTab, setActiveTab] = useState(0);
  const [templates, setTemplates] = useState([]);
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [templateDetails, setTemplateDetails] = useState(null);
  const [performanceMetrics, setPerformanceMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  
  
  
  // Dialog states
  const [templateDialogOpen, setTemplateDialogOpen] = useState(false);
  const [customizeDialogOpen, setCustomizeDialogOpen] = useState(false);
  const [customizationName, setCustomizationName] = useState('');
  
  const breadcrumbs = [
    { label: t('navigation.dashboard'), path: '/dashboard' },
    { label: t('configuration.title'), path: '/configuration' },
    { label: t('templates.title'), path: '/templates' }
  ];


  useEffect(() => {
    loadInitialData();
  }, [loadInitialData]);




  const loadInitialData = useCallback(async () => {
    try {
      setLoading(true);
      const [sectorsResponse, metricsResponse] = await Promise.all([
        getHealthcareSectors(),
        getPerformanceMetrics()
      ]);
      
      // Extract data from API responses
      const sectorsData = sectorsResponse.data || sectorsResponse;
      const metricsData = metricsResponse.data || metricsResponse;
      
      // Load all templates from all sectors
      const allTemplates = [];
      if (Array.isArray(sectorsData)) {
        for (const sector of sectorsData) {
          try {
            const templatesResponse = await getSectorTemplates(sector.id);
            const templatesData = templatesResponse.data || templatesResponse;
            if (Array.isArray(templatesData)) {
              // Add sector info to each template for context
              const templatesWithSector = templatesData.map(template => ({
                ...template,
                sector_name: sector.display_name,
                sector_id: sector.id
              }));
              allTemplates.push(...templatesWithSector);
            }
          } catch (err) {
            console.error(`Error loading templates for sector ${sector.id}:`, err);
          }
        }
      }
      
      setTemplates(allTemplates);
      setPerformanceMetrics(metricsData);
      
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




  const handleEditTemplate = async (template) => {
    try {
      // Load template details and open customize dialog
      const detailsResponse = await getTemplateDetails(template.id);
      const details = detailsResponse.data || detailsResponse;
      setSelectedTemplate({...template, chapters: details.chapters || []});
      setCustomizeDialogOpen(true);
    } catch (err) {
      console.error('Error loading template for editing:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to load template for editing');
    }
  };

  const handleDuplicateTemplate = async (template) => {
    try {
      // Load template details and open customize dialog with duplicate name
      const detailsResponse = await getTemplateDetails(template.id);
      const details = detailsResponse.data || detailsResponse;
      setSelectedTemplate({...template, chapters: details.chapters || []});
      setCustomizationName(`Copy of ${template.name}`);
      setCustomizeDialogOpen(true);
    } catch (err) {
      console.error('Error duplicating template:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to duplicate template');
    }
  };


  const handleCreateNewTemplate = () => {
    // Create a new empty template structure
    const newTemplate = {
      id: null, // No base template
      name: 'New Healthcare Template',
      chapters: [
        {
          id: Date.now(),
          name: 'New Chapter',
          questions: [
            {
              id: Date.now() + 1,
              question_text: '',
              scoring_criteria: ''
            }
          ]
        }
      ]
    };
    
    // Set the template and open customize dialog to get name first
    setSelectedTemplate(newTemplate);
    setCustomizeDialogOpen(true);
  };

  const handleSaveCustomization = () => {
    if (!customizationName.trim()) {
      setError('Please enter a customization name');
      return;
    }

    // Create a template based on the selected template with the custom name
    const customTemplate = {
      id: selectedTemplate?.id || null,
      name: customizationName,
      chapters: selectedTemplate?.chapters || [
        {
          id: Date.now(),
          name: 'New Chapter',
          questions: [
            {
              id: Date.now() + 1,
              question_text: '',
              scoring_criteria: ''
            }
          ]
        }
      ]
    };

    // Set up the template for editing
    setSelectedTemplate(customTemplate);
    setTemplateDetails({
      template: customTemplate,
      chapters: customTemplate.chapters
    });
    
    // Close customize dialog and open template editor
    setCustomizeDialogOpen(false);
    setCustomizationName('');
    setTemplateDialogOpen(true);
  };


  const TabPanel = ({ children, value, index }) => (
    <div hidden={value !== index}>
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );



  const TemplateDetailsDialog = () => {
    const [editedTemplate, setEditedTemplate] = useState(null);
    const [saving, setSaving] = useState(false);

    // Initialize edited template when dialog opens
    useEffect(() => {
      if (templateDialogOpen && templateDetails && selectedTemplate) {
        setEditedTemplate({
          name: selectedTemplate.name, // Use name from selectedTemplate
          template: templateDetails.template,
          chapters: templateDetails.chapters || []
        });
      }
    }, [templateDialogOpen, templateDetails]);

    const addChapter = () => {
      if (!editedTemplate) return;
      
      const newChapter = {
        id: Date.now(), // Temporary ID
        name: 'New Chapter',
        questions: [{
          id: Date.now() + 1,
          question_text: '',
          scoring_criteria: ''
        }]
      };
      
      setEditedTemplate({
        ...editedTemplate,
        chapters: [...editedTemplate.chapters, newChapter]
      });
    };

    const updateChapter = (chapterIndex, field, value) => {
      const updatedChapters = [...editedTemplate.chapters];
      updatedChapters[chapterIndex] = {
        ...updatedChapters[chapterIndex],
        [field]: value
      };
      setEditedTemplate({
        ...editedTemplate,
        chapters: updatedChapters
      });
    };

    const addQuestion = (chapterIndex) => {
      const newQuestion = {
        id: Date.now(),
        question_text: '',
        scoring_criteria: ''
      };
      
      const updatedChapters = [...editedTemplate.chapters];
      updatedChapters[chapterIndex].questions.push(newQuestion);
      
      setEditedTemplate({
        ...editedTemplate,
        chapters: updatedChapters
      });
    };

    const updateQuestion = (chapterIndex, questionIndex, field, value) => {
      const updatedChapters = [...editedTemplate.chapters];
      updatedChapters[chapterIndex].questions[questionIndex] = {
        ...updatedChapters[chapterIndex].questions[questionIndex],
        [field]: value
      };
      
      setEditedTemplate({
        ...editedTemplate,
        chapters: updatedChapters
      });
    };

    const saveTemplate = async () => {
      try {
        setSaving(true);
        
        if (!editedTemplate?.name) {
          throw new Error('Template name is required');
        }
        
        // For new templates, we need to use a base template ID
        // If no base template, we'll use the first available template as base
        let baseTemplateId = selectedTemplate?.id;
        if (!baseTemplateId && templates.length > 0) {
          // Use the first available template as base
          const firstTemplate = templates[0];
          baseTemplateId = firstTemplate.id;
        } else if (!baseTemplateId) {
          // If no templates exist, we need to get one from the first sector
          const sectorsResponse = await getHealthcareSectors();
          const sectorsData = sectorsResponse.data || sectorsResponse;
          if (Array.isArray(sectorsData) && sectorsData.length > 0) {
            const firstSector = sectorsData[0];
            const templatesResponse = await getSectorTemplates(firstSector.id);
            const templatesData = templatesResponse.data || templatesResponse;
            const sectorTemplates = Array.isArray(templatesData) ? templatesData : [];
            const defaultTemplate = sectorTemplates.find(t => t.is_default) || sectorTemplates[0];
            if (defaultTemplate) {
              baseTemplateId = defaultTemplate.id;
            } else {
              throw new Error('No base template available to create new template from');
            }
          }
        }
        
        if (!baseTemplateId) {
          throw new Error('Base template is required');
        }
        
        // Prepare customization data for API
        const customizationData = {
          base_template_id: baseTemplateId,
          customization_name: editedTemplate.name,
          customized_chapters: {},
          customized_questions: {},
          customized_weights: {}
        };
        
        // Process chapters and questions into the format expected by the API
        editedTemplate.chapters.forEach((chapter, chapterIndex) => {
          customizationData.customized_chapters[chapter.id || chapterIndex] = {
            name: chapter.name,
            order_index: chapterIndex
          };
          
          chapter.questions.forEach((question, questionIndex) => {
            const questionKey = `${chapter.id || chapterIndex}_${question.id || questionIndex}`;
            customizationData.customized_questions[questionKey] = {
              question_text: question.question_text,
              scoring_criteria: question.scoring_criteria,
              order_index: questionIndex
            };
          });
        });
        
        // Call API to save template customization
        console.log('Saving template customization:', customizationData);
        const response = await customizeTemplate(customizationData);
        
        console.log('Template saved successfully:', response.data);
        
        // Close dialog and refresh data
        setTemplateDialogOpen(false);
        
        // Clear any previous errors and show success
        setError(null);
        
        // Refresh sectors data to show the newly saved template
        await loadInitialData();
        
        // Show success message
        console.log('✅ Template saved and sectors refreshed successfully');
        
      } catch (error) {
        console.error('Error saving template:', error);
        setError('Failed to save template: ' + (error.response?.data?.detail || error.message));
      } finally {
        setSaving(false);
      }
    };

    return (
      <Dialog 
        open={templateDialogOpen} 
        onClose={() => setTemplateDialogOpen(false)}
        maxWidth="lg"
        fullWidth
        PaperProps={{ sx: { maxHeight: '90vh' } }}
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography variant="h6">
              Edit Template: {selectedTemplate?.name}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {templateDetails?.template?.sector_display_name}
            </Typography>
          </Box>
        </DialogTitle>
        
        <DialogContent sx={{ pb: 1 }}>
          {editedTemplate && (
            <Box>
              {/* Template Name Section */}
              <TextField
                label="Template Name"
                value={editedTemplate.name || ''}
                onChange={(e) => setEditedTemplate({
                  ...editedTemplate,
                  name: e.target.value
                })}
                fullWidth
                size="small"
                sx={{ mb: 3 }}
              />


              {/* Chapters Section */}
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6">
                  Analysis Chapters ({editedTemplate.chapters.length})
                </Typography>
                <Button 
                  startIcon={<AddIcon />} 
                  onClick={addChapter}
                  size="small"
                  variant="outlined"
                >
                  Add Chapter
                </Button>
              </Box>
              
              {editedTemplate.chapters.map((chapter, chapterIndex) => (
                <Paper key={chapter.id} sx={{ p: 2, mb: 2, border: 1, borderColor: 'grey.300' }}>
                  <TextField
                    label="Chapter Name"
                    value={chapter.name}
                    onChange={(e) => updateChapter(chapterIndex, 'name', e.target.value)}
                    size="small"
                    fullWidth
                    sx={{ mb: 2 }}
                  />

                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                    <Typography variant="subtitle2">
                      Questions ({chapter.questions.length})
                    </Typography>
                    <Button 
                      startIcon={<AddIcon />} 
                      onClick={() => addQuestion(chapterIndex)}
                      size="small"
                      variant="text"
                    >
                      Add Question
                    </Button>
                  </Box>

                  {chapter.questions.map((question, questionIndex) => (
                    <Paper key={question.id} sx={{ p: 2, mb: 1, bgcolor: 'grey.50' }}>
                      <Grid container spacing={2}>
                        <Grid item xs={12}>
                          <TextField
                            label="Question"
                            value={question.question_text}
                            onChange={(e) => updateQuestion(chapterIndex, questionIndex, 'question_text', e.target.value)}
                            fullWidth
                            size="small"
                            placeholder="Enter the analysis question..."
                          />
                        </Grid>
                        <Grid item xs={12}>
                          <TextField
                            label="Scoring Criteria"
                            value={question.scoring_criteria}
                            onChange={(e) => updateQuestion(chapterIndex, questionIndex, 'scoring_criteria', e.target.value)}
                            fullWidth
                            multiline
                            rows={2}
                            size="small"
                            placeholder="How should this question be scored? (e.g., 1-5 scale based on...)"
                          />
                        </Grid>
                      </Grid>
                    </Paper>
                  ))}
                </Paper>
              ))}

              {editedTemplate.chapters.length === 0 && (
                <Alert severity="info" sx={{ mb: 2 }}>
                  No chapters yet. Click "Add Chapter" to create your first analysis chapter.
                </Alert>
              )}
            </Box>
          )}
        </DialogContent>
        
        <DialogActions sx={{ p: 2 }}>
          <Button onClick={() => setTemplateDialogOpen(false)}>
            Cancel
          </Button>
          <Button 
            variant="contained" 
            onClick={saveTemplate}
            disabled={saving}
            startIcon={saving ? <CircularProgress size={16} /> : null}
          >
            {saving ? 'Saving...' : 'Save Template'}
          </Button>
        </DialogActions>
      </Dialog>
    );
  };

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
          onClick={handleCreateNewTemplate}
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
          <Tab label="Healthcare Templates" />
          <Tab label={t('tabs.performanceMetrics')} />
          <Tab label={t('tabs.obligatoryExtractions')} />
        </Tabs>

        <TabPanel value={activeTab} index={0}>
          <Grid container spacing={3}>
            {templates.map((template) => (
              <Grid item xs={12} md={6} lg={4} key={template.id}>
                <Card>
                  <CardContent>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                      <Typography variant="h6">
                        {template.name}
                      </Typography>
                      <Box sx={{ display: 'flex', gap: 1 }}>
                        {template.is_default && (
                          <Chip label="Default" size="small" color="primary" />
                        )}
                        <Badge badgeContent={template.usage_count} color="secondary">
                          <AssessmentIcon />
                        </Badge>
                      </Box>
                    </Box>
                    
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                      {template.description}
                    </Typography>
                    
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                      Sector: {template.sector_name}
                    </Typography>
                    
                    <Typography variant="caption" color="text.secondary">
                      Version {template.template_version} • Used {template.usage_count} times
                    </Typography>
                  </CardContent>
                  
                  <CardActions>
                    <Button 
                      size="small" 
                      startIcon={<EditIcon />}
                      onClick={() => handleEditTemplate(template)}
                    >
                      Edit
                    </Button>
                    <Button 
                      size="small" 
                      startIcon={<CopyIcon />}
                      onClick={() => handleDuplicateTemplate(template)}
                    >
                      Duplicate
                    </Button>
                  </CardActions>
                </Card>
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
                onClick={handleCreateNewTemplate}
              >
                <Box sx={{ textAlign: 'center', p: 3 }}>
                  <AddIcon sx={{ fontSize: 48, color: 'primary.main', mb: 1 }} />
                  <Typography variant="h6" color="primary.main">
                    Add New Template
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Create a new healthcare template
                  </Typography>
                </Box>
              </Card>
            </Grid>
          </Grid>
        </TabPanel>


        <TabPanel value={activeTab} index={1}>
          <PerformanceMetricsPanel />
        </TabPanel>

        <TabPanel value={activeTab} index={2}>
          <Box>
            <Typography variant="h6">Pipeline Configuration</Typography>
            <Typography variant="body2" color="text.secondary">
              Pipeline configuration is managed separately.
            </Typography>
          </Box>
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
          {selectedTemplate?.id ? `${t('labels.customizeTemplateTitle')}: ${selectedTemplate?.name}` : 'Create New Template'}
        </DialogTitle>
        <DialogContent>
          <Typography variant="body2" sx={{ mb: 2 }}>
            {selectedTemplate?.id 
              ? 'Create a customized version of this template with your own questions and analysis focus.'
              : 'Create a new healthcare analysis template with your own chapters and questions.'
            }
          </Typography>
          <TextField
            fullWidth
            label={selectedTemplate?.id ? t('labels.customizationName') : 'Template Name'}
            placeholder={selectedTemplate?.id ? t('labels.placeholderCustomTemplate') : 'My Healthcare Template'}
            value={customizationName}
            onChange={(e) => setCustomizationName(e.target.value)}
            sx={{ mb: 2 }}
          />
          <Typography variant="body2" color="text.secondary">
            Advanced customization options will be available in the detailed editor.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => {
            setCustomizeDialogOpen(false);
            setCustomizationName('');
          }}>
            {t('buttons.cancel')}
          </Button>
          <Button variant="contained" onClick={handleSaveCustomization}>
            {selectedTemplate?.id ? t('buttons.saveCustomization') : 'Create Template'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default TemplateManagement;