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
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  FormControlLabel,
  Switch,
  FormHelperText
} from '@mui/material';
import {
  Edit as EditIcon,
  FileCopy as CopyIcon,
  Add as AddIcon,
  Assessment as AssessmentIcon,
  Visibility as VisibilityIcon,
  Storefront as StorefrontIcon,
  Category as CategoryIcon,
  PlayArrow as PlayArrowIcon,
  Delete as DeleteIcon
} from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import PromptEditor from '../components/PromptEditor';

import { 
  getHealthcareSectors, 
  getSectorTemplates, 
  getTemplateDetails,
  customizeTemplate,
  updateTemplate,
  getMyCustomizations,
  getPipelinePrompts,
  getPipelinePromptByStage,
  updatePipelinePrompt,
  resetPipelinePrompt,
  deleteTemplate,
  deleteCustomization
} from '../services/api';

const TemplateManagement = () => {
  const { t } = useTranslation('templates');
  const navigate = useNavigate();
  
  const [activeTab, setActiveTab] = useState(0);
  const [templates, setTemplates] = useState([]);
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [templateDetails, setTemplateDetails] = useState(null);
  const [sectors, setSectors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Classification settings state
  const [useClassification, setUseClassification] = useState(true);  // Default to single template mode
  const [selectedTemplateId, setSelectedTemplateId] = useState('');
  
  
  
  
  // Dialog states
  const [templateDialogOpen, setTemplateDialogOpen] = useState(false);
  const [customizeDialogOpen, setCustomizeDialogOpen] = useState(false);
  const [customizationName, setCustomizationName] = useState('');
  const [isEditMode, setIsEditMode] = useState(false); // Track if we're editing vs duplicating
  
  // Pipeline configuration state
  const [pipelinePrompts, setPipelinePrompts] = useState({});
  
  // Delete confirmation dialog state
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [templateToDelete, setTemplateToDelete] = useState(null);
  const [selectedPromptStage, setSelectedPromptStage] = useState('image_analysis');
  const [promptTexts, setPromptTexts] = useState({
    image_analysis: '',
    offering_extraction: '',
    startup_name_extraction: ''
  });
  
  const breadcrumbs = [
    { label: t('navigation.dashboard'), path: '/dashboard' },
    { label: t('configuration.title'), path: '/configuration' },
    { label: t('templates.title'), path: '/templates' }
  ];

  const loadInitialData = useCallback(async () => {
    try {
      setLoading(true);
      const [sectorsResponse, pipelineResponse, customizationsResponse] = await Promise.all([
        getHealthcareSectors(),
        getPipelinePrompts(),
        getMyCustomizations()
      ]);
      
      // Extract data from API responses
      const sectorsData = sectorsResponse.data || sectorsResponse;
      const pipelineData = pipelineResponse.data || pipelineResponse;
      const customizationsData = customizationsResponse.data || customizationsResponse;
      
      // Store sectors for classification tab
      setSectors(sectorsData);
      
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
      
      // Add customizations to the template list
      if (Array.isArray(customizationsData)) {
        const customizationTemplates = customizationsData.map(customization => ({
          id: `custom_${customization.id}`, // Prefix with custom_ to distinguish from base templates
          name: customization.customization_name,
          description: `Custom template based on ${customization.template_name}`,
          template_version: '1.0',
          specialized_analysis: [],
          is_active: true,
          is_default: false,
          usage_count: 0,
          sector_name: customization.sector_name,
          sector_id: null,
          base_template_id: customization.base_template_id,
          customization_id: customization.id,
          is_customization: true
        }));
        allTemplates.push(...customizationTemplates);
      }
      
      setTemplates(allTemplates);
      setPipelinePrompts(pipelineData.prompts || {});
      
      // Set default selected template to "Standard Seven-Chapter Review"
      const standardTemplate = allTemplates.find(t => t.name === 'Standard Seven-Chapter Review');
      if (standardTemplate) {
        setSelectedTemplateId(standardTemplate.id);
      } else if (allTemplates.length > 0) {
        setSelectedTemplateId(allTemplates[0].id);
      }
      
      // Set initial prompt texts for all stages
      const prompts = pipelineData.prompts || {};
      setPromptTexts({
        image_analysis: prompts.image_analysis || '',
        offering_extraction: prompts.offering_extraction || '',
        startup_name_extraction: prompts.startup_name_extraction || ''
      });
      
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

  useEffect(() => {
    loadInitialData();
  }, [loadInitialData]);

  const handleEditTemplate = async (template) => {
    try {
      setIsEditMode(true); // Set edit mode
      
      if (template.is_customization) {
        // For customizations, we need to reconstruct the template structure
        // Since customizations store data differently, we'll create a basic structure
        const customTemplate = {
          ...template,
          chapters: [
            {
              id: Date.now(),
              name: 'Custom Chapter',
              questions: [
                {
                  id: Date.now() + 1,
                  question_text: 'Custom question',
                  scoring_criteria: 'Custom scoring criteria'
                }
              ]
            }
          ]
        };
        setSelectedTemplate(customTemplate);
        setTemplateDetails({
          template: customTemplate,
          chapters: customTemplate.chapters
        });
      } else {
        // For regular templates, load details normally
        const detailsResponse = await getTemplateDetails(template.id);
        const details = detailsResponse.data || detailsResponse;
        setSelectedTemplate({...template, chapters: details.chapters || []});
        setTemplateDetails(details);
      }
      setTemplateDialogOpen(true);
    } catch (err) {
      console.error('Error loading template for editing:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to load template for editing');
    }
  };

  const handleDuplicateTemplate = async (template) => {
    try {
      setIsEditMode(false); // Set duplicate mode
      
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

  const handleDeleteTemplate = (template) => {
    setTemplateToDelete(template);
    setDeleteDialogOpen(true);
  };

  const confirmDeleteTemplate = async () => {
    if (!templateToDelete) return;
    
    try {
      // Debug: Log the template object to see its structure
      console.log('🔍 Template to delete:', templateToDelete);
      console.log('🔍 is_customization:', templateToDelete.is_customization);
      console.log('🔍 customization_id:', templateToDelete.customization_id);
      console.log('🔍 id:', templateToDelete.id);
      
      // Check if it's a customization or regular template
      if (templateToDelete.is_customization) {
        console.log('🔥 Deleting customization with ID:', templateToDelete.customization_id);
        // Delete customization using the customization_id
        await deleteCustomization(templateToDelete.customization_id);
      } else {
        console.log('🔥 Deleting regular template with ID:', templateToDelete.id);
        // Delete regular template using the template id
        await deleteTemplate(templateToDelete.id);
      }
      
      // Close dialog and clear state
      setDeleteDialogOpen(false);
      setTemplateToDelete(null);
      
      // Refresh templates list to reflect the deletion
      await loadInitialData();
      
      // Clear any existing errors
      setError(null);
    } catch (err) {
      console.error('Error deleting template:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to delete template');
      setDeleteDialogOpen(false);
      setTemplateToDelete(null);
    }
  };

  const cancelDeleteTemplate = () => {
    setDeleteDialogOpen(false);
    setTemplateToDelete(null);
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

  // Pipeline prompt management functions
  const handlePromptStageChange = async (stageName) => {
    try {
      setSelectedPromptStage(stageName);
      const response = await getPipelinePromptByStage(stageName);
      const promptData = response.data || response;
      const newPromptText = promptData.prompt_text || '';
      setPromptTexts(prev => ({
        ...prev,
        [stageName]: newPromptText
      }));
    } catch (err) {
      console.error('Error loading prompt:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to load prompt');
    }
  };

  const handleSavePrompt = async () => {
    try {
      const currentPromptText = promptTexts[selectedPromptStage];
      await updatePipelinePrompt(selectedPromptStage, currentPromptText);
      
      // Update local state
      setPipelinePrompts(prev => ({
        ...prev,
        [selectedPromptStage]: currentPromptText
      }));
      
      setError(null);
    } catch (err) {
      console.error('Error saving prompt:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to save prompt');
    }
  };

  const handleResetPrompt = async () => {
    try {
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
      setError(err.response?.data?.detail || err.message || 'Failed to reset prompt');
    }
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
        
        if (isEditMode) {
          // Edit mode: Update existing template
          const templateId = selectedTemplate?.id;
          if (!templateId) {
            throw new Error('Template ID is required for editing');
          }
          
          const updateData = {
            name: editedTemplate.name,
            description: editedTemplate.template?.description || ''
          };
          
          console.log('Updating template:', templateId, updateData);
          const response = await updateTemplate(templateId, updateData);
          console.log('Template updated successfully:', response.data);
          
        } else {
          // Duplicate mode: Create new template customization
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
          console.log('Template customization saved successfully:', response.data);
        }
        
        // Close dialog and refresh data
        setTemplateDialogOpen(false);
        setIsEditMode(false); // Reset edit mode
        
        // Clear any previous errors and show success
        setError(null);
        
        // Refresh sectors data to show the changes
        await loadInitialData();
        
        // Show success message
        console.log('✅ Template operation completed successfully');
        
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
        onClose={() => {
          setTemplateDialogOpen(false);
          setIsEditMode(false);
        }}
        maxWidth="lg"
        fullWidth
        PaperProps={{ sx: { maxHeight: '90vh' } }}
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography variant="h6">
              {isEditMode ? 'Edit Template' : 'Duplicate Template'}: {selectedTemplate?.name}
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
          <Button onClick={() => {
            setTemplateDialogOpen(false);
            setIsEditMode(false);
          }}>
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

  const ClassificationPanel = () => (
    <Box>
      <Typography variant="h6" sx={{ mb: 3 }}>
        Classification Settings
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 4 }}>
        Choose how to analyze pitch decks: use a single template or classify into healthcare sectors first.
      </Typography>

      <Grid container spacing={4}>
        {/* Classification Mode Selection */}
        <Grid item xs={12}>
          <Card sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <CategoryIcon sx={{ mr: 1 }} />
              <Typography variant="h6">
                Classification Mode
              </Typography>
            </Box>
            
            <FormControlLabel
              control={
                <Switch
                  checked={useClassification}
                  onChange={(e) => setUseClassification(e.target.checked)}
                  color="primary"
                />
              }
              label={
                <Box>
                  <Typography variant="body1">
                    {useClassification ? 'Use Single Template' : 'Use Healthcare Sector Classification'}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {useClassification 
                      ? 'Apply the selected template to all pitch decks'
                      : 'Automatically classify startups into healthcare sectors and use sector-specific templates'
                    }
                  </Typography>
                </Box>
              }
            />
          </Card>
        </Grid>

        {/* Single Template Selection (when classification is ON) */}
        {useClassification && (
          <Grid item xs={12} md={6}>
            <Card sx={{ p: 3 }}>
              <Typography variant="h6" sx={{ mb: 2 }}>
                Template Selection
              </Typography>
              <FormControl fullWidth>
                <InputLabel>Select Template</InputLabel>
                <Select
                  value={selectedTemplateId}
                  onChange={(e) => setSelectedTemplateId(e.target.value)}
                  label="Select Template"
                >
                  {templates.map((template) => (
                    <MenuItem key={template.id} value={template.id}>
                      <Box sx={{ display: 'flex', alignItems: 'center', width: '100%' }}>
                        <Typography>{template.name}</Typography>
                        {template.is_default && (
                          <Chip label="Default" size="small" color="primary" sx={{ ml: 1 }} />
                        )}
                      </Box>
                    </MenuItem>
                  ))}
                </Select>
                <FormHelperText>
                  This template will be applied to all pitch deck analyses
                </FormHelperText>
              </FormControl>

              {selectedTemplateId && (
                <Box sx={{ mt: 2 }}>
                  {(() => {
                    const selectedTemplate = templates.find(t => t.id === selectedTemplateId);
                    return selectedTemplate ? (
                      <Alert severity="info">
                        <Typography variant="body2">
                          <strong>Selected:</strong> {selectedTemplate.name}
                          <br />
                          <strong>Sector:</strong> {selectedTemplate.sector_name}
                          <br />
                          <strong>Description:</strong> {selectedTemplate.description}
                        </Typography>
                      </Alert>
                    ) : null;
                  })()}
                </Box>
              )}
            </Card>
          </Grid>
        )}

        {/* Classification Overview (when classification is OFF) */}
        {!useClassification && (
          <Grid item xs={12}>
            <Card sx={{ p: 3 }}>
              <Typography variant="h6" sx={{ mb: 2 }}>
                Healthcare Sector Classification
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                When classification is enabled, pitch decks will be automatically categorized into the following healthcare sectors:
              </Typography>
              
              {/* Simple list instead of cards */}
              <List>
                {sectors.map((sector) => {
                  const sectorTemplate = templates.find(t => t.sector_id === sector.id && !t.is_customization);
                  return (
                    <ListItem key={sector.id} sx={{ py: 1 }}>
                      <ListItemIcon>
                        <AssessmentIcon color="primary" />
                      </ListItemIcon>
                      <ListItemText
                        primary={sector.display_name}
                        secondary={
                          <Box>
                            <Typography variant="body2" color="text.secondary">
                              {sector.description}
                            </Typography>
                            {sectorTemplate && (
                              <Typography variant="caption" color="primary">
                                Template: {sectorTemplate.name}
                              </Typography>
                            )}
                          </Box>
                        }
                      />
                    </ListItem>
                  );
                })}
              </List>

              <Alert severity="info" sx={{ mt: 2 }}>
                <Typography variant="body2">
                  <strong>How it works:</strong> The system will analyze the company offering text from each pitch deck, 
                  classify it into the most appropriate healthcare sector, and then apply the corresponding sector-specific 
                  analysis template automatically.
                </Typography>
              </Alert>
            </Card>
          </Grid>
        )}

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
          <Tab label="Deck Review Templates" />
          <Tab label="Classifications" />
          <Tab label={t('tabs.obligatoryExtractions')} />
        </Tabs>

        <TabPanel value={activeTab} index={0}>
          <Grid container spacing={3}>
            {templates.map((template) => (
              <Grid item xs={12} md={6} lg={4} key={template.id}>
                <Card>
                  <CardContent>
                    <Box sx={{ mb: 2 }}>
                      <Typography variant="h6">
                        {template.name}
                      </Typography>
                    </Box>
                    
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                      {template.description}
                    </Typography>
                    
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                      Sector: {template.sector_name}
                    </Typography>
                  </CardContent>
                  
                  <CardActions sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Box sx={{ display: 'flex', gap: 1 }}>
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
                    </Box>
                    <Button 
                      size="small" 
                      startIcon={<DeleteIcon />}
                      onClick={() => handleDeleteTemplate(template)}
                      color="error"
                    >
                      Delete
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
          <ClassificationPanel />
        </TabPanel>

        <TabPanel value={activeTab} index={2}>
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

      {/* Delete Confirmation Dialog */}
      <Dialog 
        open={deleteDialogOpen} 
        onClose={cancelDeleteTemplate}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          Delete Template
        </DialogTitle>
        <DialogContent>
          <Typography variant="body1">
            Are you sure you want to delete the template "{templateToDelete?.name}"?
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            This action cannot be undone. The template will be permanently removed from the system.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={cancelDeleteTemplate}>
            Cancel
          </Button>
          <Button 
            variant="contained" 
            color="error" 
            onClick={confirmDeleteTemplate}
          >
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default TemplateManagement;