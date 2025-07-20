import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Typography,
  Paper,
  Grid,
  Card,
  CardContent,
  Button,
  Alert,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  LinearProgress,
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  ListItemSecondaryAction,
  Tabs,
  Tab,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel
} from '@mui/material';
import {
  CloudUpload,
  Delete,
  Assessment,
  Description,
  CheckCircle,
  Error,
  Pending,
  Storage,
  DataUsage,
  Refresh,
  Stop,
  Clear
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

const DojoManagement = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();

  // Helper function to format upload speed
  const formatUploadSpeed = (bytesPerSecond) => {
    if (bytesPerSecond < 1024) return `${bytesPerSecond.toFixed(0)} B/s`;
    if (bytesPerSecond < 1024 * 1024) return `${(bytesPerSecond / 1024).toFixed(1)} KB/s`;
    return `${(bytesPerSecond / (1024 * 1024)).toFixed(1)} MB/s`;
  };

  // Helper function to format file size
  const formatFileSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  // Helper function to estimate remaining time
  const formatRemainingTime = (bytesUploaded, totalBytes, uploadSpeed) => {
    if (uploadSpeed === 0 || bytesUploaded === 0 || uploadSpeed < 100) return ''; // Ignore very slow speeds (100 B/s)
    
    const remainingBytes = totalBytes - bytesUploaded;
    const remainingSeconds = remainingBytes / uploadSpeed;
    
    // Cap at reasonable maximum (24 hours)
    if (remainingSeconds > 86400) return 'More than 24h remaining';
    
    if (remainingSeconds < 60) return `${Math.round(remainingSeconds)}s remaining`;
    if (remainingSeconds < 3600) return `${Math.round(remainingSeconds / 60)}m remaining`;
    return `${Math.round(remainingSeconds / 3600)}h ${Math.round((remainingSeconds % 3600) / 60)}m remaining`;
  };
  
  const [files, setFiles] = useState([]);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [selectedFile, setSelectedFile] = useState(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [fileToDelete, setFileToDelete] = useState(null);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [processingStatus, setProcessingStatus] = useState('');
  const [uploadSpeed, setUploadSpeed] = useState(0);
  const [uploadStartTime, setUploadStartTime] = useState(null);
  const [bytesUploaded, setBytesUploaded] = useState(0);
  const [currentXhr, setCurrentXhr] = useState(null);
  
  // Extraction testing states
  const [currentTab, setCurrentTab] = useState(0);
  const [extractionSample, setExtractionSample] = useState([]);
  const [visualAnalysisStatus, setVisualAnalysisStatus] = useState('idle');
  const [selectedVisionModel, setSelectedVisionModel] = useState('');
  const [visualAnalysisPrompt, setVisualAnalysisPrompt] = useState('');
  const [selectedTextModel, setSelectedTextModel] = useState('');
  const [extractionPrompt, setExtractionPrompt] = useState('');
  const [currentAnalysisController, setCurrentAnalysisController] = useState(null);
  const [clearingCache, setClearingCache] = useState(false);
  const [analysisProgress, setAnalysisProgress] = useState({ completed: 0, total: 0 });
  const [experiments, setExperiments] = useState([]);
  const [availableModels, setAvailableModels] = useState({});
  const [modelsLoading, setModelsLoading] = useState(false);
  const [gpuStatus, setGpuStatus] = useState(null);
  const [selectedExperiment, setSelectedExperiment] = useState(null);
  const [experimentDetailsOpen, setExperimentDetailsOpen] = useState(false);
  const [experimentDetails, setExperimentDetails] = useState(null);
  const [loadingExperimentDetails, setLoadingExperimentDetails] = useState(false);
  const [comparisonMode, setComparisonMode] = useState(false);
  const [selectedExperiments, setSelectedExperiments] = useState([]);

  useEffect(() => {
    loadDojoData();
    loadAvailableModels();
  }, []);

  const loadDojoData = useCallback(async () => {
    try {
      setLoading(true);
      const user = JSON.parse(localStorage.getItem('user'));
      const token = user?.token;
      
      if (!token) {
        setError('Not authenticated');
        navigate('/login');
        return;
      }

      // Load files and stats in parallel
      const [filesResponse, statsResponse] = await Promise.all([
        fetch('/api/dojo/files', {
          headers: { 'Authorization': `Bearer ${token}` }
        }),
        fetch('/api/dojo/stats', {
          headers: { 'Authorization': `Bearer ${token}` }
        })
      ]);

      if (!filesResponse.ok || !statsResponse.ok) {
        throw new Error('Failed to load dojo data');
      }

      const filesData = await filesResponse.json();
      const statsData = await statsResponse.json();

      setFiles(filesData.files || []);
      setStats(statsData);
      setError(null);
    } catch (err) {
      console.error('Error loading dojo data:', err);
      setError(err.message || 'Failed to load dojo data');
    } finally {
      setLoading(false);
    }
  }, [navigate]);

  const cancelUpload = () => {
    if (currentXhr) {
      currentXhr.abort();
      setCurrentXhr(null);
      setUploading(false);
      setUploadProgress(0);
      setSelectedFile(null);
      setUploadSuccess(false);
      setProcessingStatus('');
      setUploadSpeed(0);
      setUploadStartTime(null);
      setBytesUploaded(0);
      setError('Upload cancelled');
    }
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    // Validate file type
    if (!file.name.toLowerCase().endsWith('.zip')) {
      setError('Please select a ZIP file');
      return;
    }

    // Validate file size (1GB limit)
    const maxSize = 1024 * 1024 * 1024; // 1GB
    if (file.size > maxSize) {
      setError('File size must be less than 1GB');
      return;
    }

    try {
      setUploading(true);
      setUploadProgress(0);
      setError(null);
      setSelectedFile(file);
      setUploadStartTime(Date.now());

      const user = JSON.parse(localStorage.getItem('user'));
      const token = user?.token;

      const formData = new FormData();
      formData.append('file', file);

      // Create XMLHttpRequest to track upload progress
      const xhr = new XMLHttpRequest();
      setCurrentXhr(xhr);
      
      // Track upload progress
      xhr.upload.addEventListener('progress', (event) => {
        if (event.lengthComputable) {
          const percentComplete = Math.round((event.loaded / event.total) * 100);
          setUploadProgress(percentComplete);
          setBytesUploaded(event.loaded);
          
          // Calculate upload speed (more responsive calculation)
          const currentTime = Date.now();
          const elapsedTime = (currentTime - uploadStartTime) / 1000; // in seconds
          if (elapsedTime > 0.5 && event.loaded > 0) { // Start calculating after 0.5 seconds
            const speed = event.loaded / elapsedTime; // bytes per second
            setUploadSpeed(speed);
          }
        }
      });

      // Handle response
      xhr.addEventListener('load', async () => {
        if (xhr.status === 200) {
          try {
            const result = JSON.parse(xhr.responseText);
            setUploadProgress(100);
            setProcessingStatus('Upload completed successfully! Ready for manual processing.');
            setUploadSuccess(true);
            
            // Show success message briefly, then reload data
            setTimeout(() => {
              loadDojoData();
              setUploading(false);
              setUploadProgress(0);
              setSelectedFile(null);
              setUploadSuccess(false);
              setProcessingStatus('');
              setUploadSpeed(0);
              setUploadStartTime(null);
              setBytesUploaded(0);
              setCurrentXhr(null);
            }, 2000);
          } catch (parseError) {
            throw new Error('Invalid response from server');
          }
        } else {
          try {
            const errorData = JSON.parse(xhr.responseText);
            throw new Error(errorData.detail || 'Upload failed');
          } catch (parseError) {
            throw new Error(`Upload failed with status: ${xhr.status}`);
          }
        }
      });

      // Handle errors
      xhr.addEventListener('error', () => {
        setError('Upload failed due to network error');
        setUploading(false);
        setUploadProgress(0);
        setSelectedFile(null);
        setUploadSuccess(false);
        setProcessingStatus('');
        setUploadSpeed(0);
        setUploadStartTime(null);
        setBytesUploaded(0);
        setCurrentXhr(null);
      });

      // Handle timeout
      xhr.addEventListener('timeout', () => {
        setError('Upload timed out. Please try again.');
        setUploading(false);
        setUploadProgress(0);
        setSelectedFile(null);
        setUploadSuccess(false);
        setProcessingStatus('');
        setUploadSpeed(0);
        setUploadStartTime(null);
        setBytesUploaded(0);
      });

      // Set dynamic timeout based on file size - more generous for large files  
      // Base timeout of 15 minutes plus 2 minutes per 100MB, capped at 1 hour
      const baseTimeout = 15 * 60 * 1000; // 15 minutes base
      const fileSizeTimeout = Math.ceil(file.size / (100 * 1024 * 1024)) * 2 * 60 * 1000; // 2 minutes per 100MB
      const totalTimeout = baseTimeout + fileSizeTimeout;
      xhr.timeout = Math.min(totalTimeout, 60 * 60 * 1000); // Cap at 1 hour

      // Send request
      xhr.open('POST', '/api/dojo/upload');
      xhr.setRequestHeader('Authorization', `Bearer ${token}`);
      xhr.send(formData);

    } catch (err) {
      console.error('Error uploading file:', err);
      setError(err.message || 'Failed to upload file');
      setUploading(false);
      setUploadProgress(0);
      setSelectedFile(null);
      setUploadSuccess(false);
      setProcessingStatus('');
      setUploadSpeed(0);
      setUploadStartTime(null);
      setBytesUploaded(0);
    }

    // Clear file input
    event.target.value = '';
  };

  // ==================== EXTRACTION TESTING FUNCTIONALITY ====================

  const loadAvailableModels = async () => {
    try {
      setModelsLoading(true);
      setGpuStatus(null);
      
      const user = JSON.parse(localStorage.getItem('user'));
      const token = user?.token;

      const response = await fetch('/api/config/models', {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        const modelsData = await response.json();
        
        // Check if GPU is available based on the response
        const hasModels = modelsData.models && modelsData.models.length > 0;
        setGpuStatus(hasModels ? 'online' : 'offline');
        
        // Transform the models data to match expected format
        // All models can be used for both vision and text tasks
        const modelOptions = modelsData.models ? modelsData.models.map(model => ({ model_name: model.name })) : [];
        const transformedModels = {
          vision: modelOptions,
          text: modelOptions
        };
        
        setAvailableModels(transformedModels);
        
        // Set default models - prefer models with certain names for vision/text
        const visionPreferred = modelOptions.find(model => 
          model.model_name.toLowerCase().includes('vision') || 
          model.model_name.toLowerCase().includes('llava') ||
          model.model_name.toLowerCase().includes('minicpm')
        );
        const textPreferred = modelOptions.find(model => 
          model.model_name.toLowerCase().includes('llama') ||
          model.model_name.toLowerCase().includes('mistral') ||
          model.model_name.toLowerCase().includes('gemma')
        );
        
        if (visionPreferred) {
          setSelectedVisionModel(visionPreferred.model_name);
        } else if (modelOptions.length > 0) {
          setSelectedVisionModel(modelOptions[0].model_name);
        }
        
        if (textPreferred) {
          setSelectedTextModel(textPreferred.model_name);
        } else if (modelOptions.length > 0) {
          setSelectedTextModel(modelOptions[0].model_name);
        }
        
        // Load actual prompts from backend
        loadPipelinePrompts(token);
      } else {
        setGpuStatus('error');
        throw new Error('Failed to fetch models');
      }
    } catch (err) {
      console.error('Error loading models:', err);
      setGpuStatus('error');
      // Set empty models on error
      setAvailableModels({ vision: [], text: [] });
    } finally {
      setModelsLoading(false);
    }
  };

  const loadPipelinePrompts = async (token) => {
    try {
      const response = await fetch('/api/pipeline/prompts', {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        const data = await response.json();
        const prompts = data.prompts;
        
        // Set the actual prompts from the database
        if (prompts.image_analysis) {
          setVisualAnalysisPrompt(prompts.image_analysis);
        }
        if (prompts.offering_extraction) {
          setExtractionPrompt(prompts.offering_extraction);
        }
        
        console.log('Loaded pipeline prompts:', prompts);
      } else {
        console.error('Failed to load pipeline prompts');
        // Fallback to empty prompts so user can enter their own
        setVisualAnalysisPrompt('');
        setExtractionPrompt('');
      }
    } catch (err) {
      console.error('Error loading pipeline prompts:', err);
      // Fallback to empty prompts so user can enter their own
      setVisualAnalysisPrompt('');
      setExtractionPrompt('');
    }
  };

  const createExtractionSample = async () => {
    try {
      const user = JSON.parse(localStorage.getItem('user'));
      const token = user?.token;

      const response = await fetch('/api/dojo/extraction-test/sample', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ sample_size: 10 })
      });

      if (response.ok) {
        const data = await response.json();
        setExtractionSample(data.sample);
        console.log('Created extraction sample:', data);
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to create extraction sample');
      }
    } catch (err) {
      console.error('Error creating extraction sample:', err);
      setError('Failed to create extraction sample');
    }
  };

  const runVisualAnalysis = async () => {
    try {
      setVisualAnalysisStatus('running');
      const user = JSON.parse(localStorage.getItem('user'));
      const token = user?.token;

      // Create AbortController for cancellation
      const controller = new AbortController();
      setCurrentAnalysisController(controller);

      const deckIds = extractionSample.map(deck => deck.id);
      
      const response = await fetch('/api/dojo/extraction-test/run-visual-analysis', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          deck_ids: deckIds,
          vision_model: selectedVisionModel,
          analysis_prompt: visualAnalysisPrompt
        }),
        signal: controller.signal
      });

      if (response.ok) {
        const data = await response.json();
        console.log('Visual analysis batch started:', data);
        
        // Initialize progress tracking
        const total = extractionSample.length;
        setAnalysisProgress({ completed: 0, total });
        
        // Start polling for progress updates
        const pollInterval = setInterval(async () => {
          const progress = await checkAnalysisProgress();
          if (progress && (progress.completed === progress.total || visualAnalysisStatus === 'cancelled')) {
            clearInterval(pollInterval);
            if (progress.completed === progress.total) {
              setVisualAnalysisStatus('completed');
            }
          }
        }, 3000); // Check every 3 seconds
        
        // Store interval ID so we can clear it if stopped
        controller.pollInterval = pollInterval;
      } else {
        setVisualAnalysisStatus('error');
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to run visual analysis');
      }
    } catch (err) {
      if (err.name === 'AbortError') {
        setVisualAnalysisStatus('cancelled');
        console.log('Visual analysis cancelled by user');
        setError('Visual analysis cancelled');
      } else {
        setVisualAnalysisStatus('error');
        console.error('Error running visual analysis:', err);
        setError('Failed to run visual analysis');
      }
    } finally {
      // Clear polling interval if it exists
      if (currentAnalysisController && currentAnalysisController.pollInterval) {
        clearInterval(currentAnalysisController.pollInterval);
      }
      setCurrentAnalysisController(null);
    }
  };

  const checkAnalysisProgress = async () => {
    try {
      const user = JSON.parse(localStorage.getItem('user'));
      const token = user?.token;

      // Re-fetch the current sample to get updated cache status
      const response = await fetch('/api/dojo/extraction-test/sample', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ 
          sample_size: extractionSample.length,
          existing_ids: extractionSample.map(deck => deck.id) // Get status for existing sample
        })
      });

      if (response.ok) {
        const data = await response.json();
        setExtractionSample(data.sample);
        
        // Count completed vs total
        const completed = data.sample.filter(deck => deck.has_visual_cache).length;
        const total = data.sample.length;
        
        setAnalysisProgress({ completed, total });
        
        return { completed, total };
      }
    } catch (err) {
      console.error('Error checking analysis progress:', err);
    }
    return null;
  };

  const stopVisualAnalysis = () => {
    if (currentAnalysisController) {
      // Clear polling interval
      if (currentAnalysisController.pollInterval) {
        clearInterval(currentAnalysisController.pollInterval);
      }
      // Abort the HTTP request
      currentAnalysisController.abort();
      setCurrentAnalysisController(null);
      setVisualAnalysisStatus('cancelled');
      console.log('Visual analysis stopped by user');
    }
  };

  const clearVisualAnalysisCache = async () => {
    try {
      setClearingCache(true);
      const user = JSON.parse(localStorage.getItem('user'));
      const token = user?.token;

      const deckIds = extractionSample.map(deck => deck.id);
      
      const response = await fetch('/api/dojo/extraction-test/clear-cache', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          deck_ids: deckIds
        })
      });

      if (response.ok) {
        const data = await response.json();
        console.log('Cache cleared:', data);
        // Refresh sample to update cache status
        createExtractionSample();
        setError(null);
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to clear cache');
      }
    } catch (err) {
      console.error('Error clearing cache:', err);
      setError('Failed to clear cache');
    } finally {
      setClearingCache(false);
    }
  };

  const runExtractionTest = async () => {
    try {
      const user = JSON.parse(localStorage.getItem('user'));
      const token = user?.token;

      const deckIds = extractionSample.map(deck => deck.id);
      const experimentName = `test_${Date.now()}`;
      
      const response = await fetch('/api/dojo/extraction-test/run-offering-extraction', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          experiment_name: experimentName,
          deck_ids: deckIds,
          text_model: selectedTextModel,
          extraction_prompt: extractionPrompt,
          use_cached_visual: true
        })
      });

      if (response.ok) {
        const data = await response.json();
        console.log('Extraction test completed:', data);
        loadExperiments();
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to run extraction test');
      }
    } catch (err) {
      console.error('Error running extraction test:', err);
      setError('Failed to run extraction test');
    }
  };

  const loadExperiments = async () => {
    try {
      const user = JSON.parse(localStorage.getItem('user'));
      const token = user?.token;

      const response = await fetch('/api/dojo/extraction-test/experiments', {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        const data = await response.json();
        setExperiments(data.experiments);
      }
    } catch (err) {
      console.error('Error loading experiments:', err);
    }
  };

  const handleTabChange = (event, newValue) => {
    setCurrentTab(newValue);
    if (newValue === 1) { // Extraction Testing Lab tab
      loadExperiments();
    }
  };

  const viewExperimentDetails = async (experiment) => {
    setSelectedExperiment(experiment);
    setExperimentDetailsOpen(true);
    setLoadingExperimentDetails(true);
    
    try {
      const user = JSON.parse(localStorage.getItem('user'));
      const token = user?.token;

      const response = await fetch(`/api/dojo/extraction-test/experiments/${experiment.id}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        const details = await response.json();
        setExperimentDetails(details);
      } else {
        console.error('Failed to load experiment details');
      }
    } catch (err) {
      console.error('Error loading experiment details:', err);
    } finally {
      setLoadingExperimentDetails(false);
    }
  };

  const toggleComparisonMode = () => {
    setComparisonMode(!comparisonMode);
    setSelectedExperiments([]);
  };

  const handleExperimentSelection = (experimentId) => {
    setSelectedExperiments(prev => {
      if (prev.includes(experimentId)) {
        return prev.filter(id => id !== experimentId);
      } else if (prev.length < 3) { // Limit to 3 experiments for comparison
        return [...prev, experimentId];
      }
      return prev;
    });
  };

  const getExperimentById = (id) => {
    return experiments.find(exp => exp.id === id);
  };

  const handleDeleteFile = async (fileId) => {
    try {
      const user = JSON.parse(localStorage.getItem('user'));
      const token = user?.token;

      const response = await fetch(`/api/dojo/files/${fileId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to delete file');
      }

      // Reload data after successful deletion
      loadDojoData();
      setDeleteDialogOpen(false);
      setFileToDelete(null);

    } catch (err) {
      console.error('Error deleting file:', err);
      setError(err.message || 'Failed to delete file');
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed':
        return <CheckCircle color="success" />;
      case 'failed':
        return <Error color="error" />;
      case 'processing':
        return <CircularProgress size={20} />;
      default:
        return <Pending color="warning" />;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'failed':
        return 'error';
      case 'processing':
        return 'info';
      default:
        return 'warning';
    }
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
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom>
          Dojo Training Data Management
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Upload and manage training datasets for AI model improvement
        </Typography>
      </Box>

      {/* Error Alert */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Stats Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <Storage sx={{ mr: 2, color: 'primary.main' }} />
                <Box>
                  <Typography variant="h4" color="primary">
                    {stats.total_files || 0}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Total Files
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <CheckCircle sx={{ mr: 2, color: 'success.main' }} />
                <Box>
                  <Typography variant="h4" color="success.main">
                    {stats.processed_files || 0}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Processed
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <Pending sx={{ mr: 2, color: 'warning.main' }} />
                <Box>
                  <Typography variant="h4" color="warning.main">
                    {stats.pending_files || 0}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Pending
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <Error sx={{ mr: 2, color: 'error.main' }} />
                <Box>
                  <Typography variant="h4" color="error.main">
                    {stats.failed_files || 0}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Failed
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Upload Section */}
      <Paper sx={{ p: 3, mb: 4 }}>
        <Typography variant="h6" gutterBottom>
          Upload Training Data
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Upload a ZIP file containing PDF pitch decks for AI training (max 1GB)
        </Typography>

        {uploading ? (
          <Box sx={{ width: '100%', mb: 2 }}>
            {/* File Info */}
            {selectedFile && (
              <Box sx={{ mb: 2, p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
                <Typography variant="body2" sx={{ fontWeight: 'medium' }}>
                  Uploading: {selectedFile.name}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Size: {formatFileSize(selectedFile.size)}
                </Typography>
              </Box>
            )}

            {/* Progress Bar */}
            <Box sx={{ width: '100%', mb: 1 }}>
              <LinearProgress 
                variant="determinate" 
                value={uploadProgress} 
                sx={{ height: 8, borderRadius: 4 }}
              />
            </Box>

            {/* Progress Info */}
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Box>
                <Typography variant="body2" color={uploadSuccess ? 'success.main' : 'text.secondary'}>
                  {processingStatus || (uploadProgress < 100 ? `Uploading... ${uploadProgress}%` : 'Processing files...')}
                </Typography>
                {uploadSpeed > 0 && uploadProgress < 100 && (
                  <Box>
                    <Typography variant="caption" color="text.secondary">
                      {formatUploadSpeed(uploadSpeed)}
                    </Typography>
                    {selectedFile && (
                      <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>
                        • {formatRemainingTime(bytesUploaded, selectedFile.size, uploadSpeed)}
                      </Typography>
                    )}
                  </Box>
                )}
              </Box>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                {uploadSuccess ? (
                  <CheckCircle color="success" sx={{ mr: 1 }} />
                ) : (
                  <CircularProgress size={16} sx={{ mr: 1 }} />
                )}
                <Typography variant="caption" color={uploadSuccess ? 'success.main' : 'text.secondary'}>
                  {uploadSuccess ? 'Success' : (uploadProgress < 100 ? 'Uploading' : 'Processing')}
                </Typography>
              </Box>
            </Box>

            {/* Cancel Button - only show if upload is in progress and not completed */}
            {!uploadSuccess && (
              <Box sx={{ mt: 2 }}>
                <Button
                  variant="outlined"
                  color="error"
                  size="small"
                  onClick={() => {
                    setUploading(false);
                    setUploadProgress(0);
                    setSelectedFile(null);
                    setUploadSuccess(false);
                    setProcessingStatus('');
                    setUploadSpeed(0);
                    setUploadStartTime(null);
                    setBytesUploaded(0);
                    setError('Upload cancelled');
                  }}
                >
                  Cancel Upload
                </Button>
              </Box>
            )}
          </Box>
        ) : (
          <Box>
            <Button
              variant="contained"
              component="label"
              startIcon={<CloudUpload />}
              disabled={uploading}
              sx={{ mb: 2 }}
            >
              Select ZIP File
              <input
                type="file"
                hidden
                accept=".zip"
                onChange={handleFileUpload}
              />
            </Button>

            {/* Upload Guidelines */}
            <Box sx={{ mt: 2, p: 2, bgcolor: 'info.light', borderRadius: 1, color: 'info.contrastText' }}>
              <Typography variant="caption" sx={{ fontWeight: 'medium' }}>
                Upload Guidelines:
              </Typography>
              <List dense sx={{ mt: 1 }}>
                <ListItem sx={{ py: 0.5 }}>
                  <ListItemText 
                    primary="• Only ZIP files containing PDF pitch decks" 
                    primaryTypographyProps={{ variant: 'caption' }}
                  />
                </ListItem>
                <ListItem sx={{ py: 0.5 }}>
                  <ListItemText 
                    primary="• Maximum file size: 1GB" 
                    primaryTypographyProps={{ variant: 'caption' }}
                  />
                </ListItem>
                <ListItem sx={{ py: 0.5 }}>
                  <ListItemText 
                    primary="• Files are stored after upload and require manual processing" 
                    primaryTypographyProps={{ variant: 'caption' }}
                  />
                </ListItem>
                <ListItem sx={{ py: 0.5 }}>
                  <ListItemText 
                    primary="• Processing can be triggered multiple times with different parameters" 
                    primaryTypographyProps={{ variant: 'caption' }}
                  />
                </ListItem>
                <ListItem sx={{ py: 0.5 }}>
                  <ListItemText 
                    primary="• Upload timeout adjusts automatically based on file size" 
                    primaryTypographyProps={{ variant: 'caption' }}
                  />
                </ListItem>
              </List>
            </Box>
          </Box>
        )}
      </Paper>

      {/* Main Content - Tabs */}
      <Paper sx={{ p: 3 }}>
        <Tabs value={currentTab} onChange={handleTabChange}>
          <Tab label="Training Files" />
          <Tab label="Extraction Testing Lab" />
        </Tabs>
        
        {/* Tab Panel 0: Files Table */}
        {currentTab === 0 && (
          <Box sx={{ mt: 3 }}>
            <Typography variant="h6" gutterBottom>
              Training Files
            </Typography>
        
            {files.length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                No training files uploaded yet
              </Typography>
            ) : (
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Filename</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell>Startup Name</TableCell>
                      <TableCell>Uploaded</TableCell>
                      <TableCell>Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {files.map((file) => (
                      <TableRow key={file.id}>
                        <TableCell>
                          <Box sx={{ display: 'flex', alignItems: 'center' }}>
                            <Description sx={{ mr: 1 }} />
                            {file.filename}
                          </Box>
                        </TableCell>
                        <TableCell>
                          <Chip
                            icon={getStatusIcon(file.processing_status)}
                            label={file.processing_status}
                            color={getStatusColor(file.processing_status)}
                            variant="outlined"
                            size="small"
                          />
                        </TableCell>
                        <TableCell>
                          {file.ai_extracted_startup_name || '-'}
                        </TableCell>
                        <TableCell>
                          {file.created_at ? new Date(file.created_at).toLocaleDateString() : '-'}
                        </TableCell>
                        <TableCell>
                          <IconButton
                            onClick={() => {
                              setFileToDelete(file);
                              setDeleteDialogOpen(true);
                            }}
                            color="error"
                            size="small"
                          >
                            <Delete />
                          </IconButton>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </Box>
        )}
        
        {/* Tab Panel 1: Extraction Testing Lab */}
        {currentTab === 1 && (
          <Box sx={{ mt: 3 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 3 }}>
              <Box>
                <Typography variant="h6" gutterBottom>
                  Extraction Testing Lab
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Test and compare company offering extraction quality using different models and prompts
                </Typography>
              </Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                {gpuStatus && (
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    {gpuStatus === 'online' && (
                      <>
                        <CheckCircle color="success" fontSize="small" />
                        <Typography variant="caption" color="success.main">GPU Online</Typography>
                      </>
                    )}
                    {gpuStatus === 'offline' && (
                      <>
                        <Error color="warning" fontSize="small" />
                        <Typography variant="caption" color="warning.main">GPU Offline</Typography>
                      </>
                    )}
                    {gpuStatus === 'error' && (
                      <>
                        <Error color="error" fontSize="small" />
                        <Typography variant="caption" color="error.main">GPU Connection Error</Typography>
                      </>
                    )}
                  </Box>
                )}
                <Button
                  variant="outlined"
                  size="small"
                  onClick={loadAvailableModels}
                  disabled={modelsLoading}
                  startIcon={modelsLoading ? <CircularProgress size={16} /> : <Refresh />}
                >
                  {modelsLoading ? 'Loading...' : 'Refresh Models'}
                </Button>
              </Box>
            </Box>
            
            {/* GPU Status Alert */}
            {gpuStatus === 'error' && (
              <Alert severity="error" sx={{ mb: 3 }}>
                Unable to connect to GPU instance. Model selection and analysis features will not be available.
                Please check if the GPU instance is running and try refreshing the models.
              </Alert>
            )}
            
            {gpuStatus === 'offline' && (
              <Alert severity="warning" sx={{ mb: 3 }}>
                GPU instance is online but no models are available. You may need to pull models first 
                in the Model Configuration page.
              </Alert>
            )}
            
            {availableModels.vision && availableModels.vision.length === 0 && !modelsLoading && (
              <Alert severity="info" sx={{ mb: 3 }}>
                No models available for extraction testing. Please ensure the GPU instance is running 
                and models are installed.
              </Alert>
            )}
            
            {/* Step 1: Sample Selection */}
            <Paper sx={{ p: 3, mb: 3, bgcolor: 'grey.50' }}>
              <Typography variant="h6" gutterBottom>
                Step 1: Create Sample
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
                <Button 
                  variant="outlined" 
                  onClick={createExtractionSample}
                  disabled={loading}
                >
                  Generate Random Sample (10 decks)
                </Button>
                <Typography variant="body2" color="text.secondary">
                  {extractionSample.length > 0 ? `Sample created: ${extractionSample.length} decks` : 'No sample created yet'}
                </Typography>
              </Box>
              
              {extractionSample.length > 0 && (
                <Box sx={{ mt: 2 }}>
                  <Typography variant="subtitle2" gutterBottom>Sample Overview:</Typography>
                  <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                    {extractionSample.map((deck, index) => (
                      <Chip 
                        key={deck.id}
                        label={`${index + 1}. ${deck.filename}`}
                        color={deck.has_visual_cache ? 'success' : 'default'}
                        variant="outlined"
                        size="small"
                      />
                    ))}
                  </Box>
                  <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                    Green chips have cached visual analysis. Others need visual analysis first.
                  </Typography>
                </Box>
              )}
            </Paper>
            
            {/* Step 2: Visual Analysis */}
            {extractionSample.length > 0 && (
              <Paper sx={{ p: 3, mb: 3, bgcolor: 'grey.50' }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                  <Typography variant="h6">
                    Step 2: Visual Analysis Manager
                  </Typography>
                  {gpuStatus && (
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      {gpuStatus === 'online' && (
                        <>
                          <CheckCircle color="success" fontSize="small" />
                          <Typography variant="caption" color="success.main">GPU Online</Typography>
                        </>
                      )}
                      {gpuStatus === 'offline' && (
                        <>
                          <Error color="warning" fontSize="small" />
                          <Typography variant="caption" color="warning.main">GPU Offline</Typography>
                        </>
                      )}
                      {gpuStatus === 'error' && (
                        <>
                          <Error color="error" fontSize="small" />
                          <Typography variant="caption" color="error.main">GPU Error</Typography>
                        </>
                      )}
                    </Box>
                  )}
                </Box>
                <Grid container spacing={3}>
                  <Grid item xs={12} md={6}>
                    <FormControl fullWidth sx={{ mb: 2 }}>
                      <InputLabel>Vision Model</InputLabel>
                      <Select
                        value={selectedVisionModel}
                        onChange={(e) => setSelectedVisionModel(e.target.value)}
                        label="Vision Model"
                        disabled={modelsLoading || gpuStatus === 'error'}
                      >
                        {modelsLoading ? (
                          <MenuItem disabled>
                            <CircularProgress size={16} sx={{ mr: 1 }} />
                            Loading models...
                          </MenuItem>
                        ) : availableModels.vision && availableModels.vision.length > 0 ? (
                          availableModels.vision.map((model) => (
                            <MenuItem key={model.model_name} value={model.model_name}>
                              {model.model_name}
                            </MenuItem>
                          ))
                        ) : (
                          <MenuItem disabled>
                            No models available - GPU may be offline
                          </MenuItem>
                        )}
                      </Select>
                    </FormControl>
                    
                    <TextField
                      fullWidth
                      multiline
                      rows={3}
                      label="Visual Analysis Prompt"
                      value={visualAnalysisPrompt}
                      onChange={(e) => setVisualAnalysisPrompt(e.target.value)}
                      placeholder="Loading actual prompt from database..."
                    />
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                      <Button 
                        variant="contained" 
                        onClick={runVisualAnalysis}
                        disabled={!selectedVisionModel || !visualAnalysisPrompt || visualAnalysisStatus === 'running'}
                        startIcon={visualAnalysisStatus === 'running' ? <CircularProgress size={16} /> : <Assessment />}
                      >
                        {visualAnalysisStatus === 'running' ? 'Running Analysis...' : 'Run Visual Analysis'}
                      </Button>

                      {/* Stop Analysis Button */}
                      {visualAnalysisStatus === 'running' && (
                        <Button 
                          variant="outlined" 
                          color="error"
                          onClick={stopVisualAnalysis}
                          startIcon={<Stop />}
                        >
                          Stop Analysis
                        </Button>
                      )}

                      {/* Clear Cache Button */}
                      <Button 
                        variant="outlined" 
                        color="warning"
                        onClick={clearVisualAnalysisCache}
                        disabled={extractionSample.length === 0 || clearingCache}
                        startIcon={clearingCache ? <CircularProgress size={16} /> : <Clear />}
                      >
                        {clearingCache ? 'Clearing Cache...' : 'Clear Visual Cache'}
                      </Button>
                      
                      {visualAnalysisStatus !== 'idle' && (
                        <Alert severity={
                          visualAnalysisStatus === 'error' ? 'error' : 
                          visualAnalysisStatus === 'completed' ? 'success' : 
                          visualAnalysisStatus === 'cancelled' ? 'warning' : 'info'
                        }>
                          {visualAnalysisStatus === 'running' && (
                            analysisProgress.total > 0 
                              ? `Processing visual analysis: ${analysisProgress.completed}/${analysisProgress.total} decks analyzed`
                              : 'Processing visual analysis for sample decks...'
                          )}
                          {visualAnalysisStatus === 'completed' && 'Visual analysis completed and cached!'}
                          {visualAnalysisStatus === 'cancelled' && 'Visual analysis cancelled by user.'}
                          {visualAnalysisStatus === 'error' && 'Visual analysis failed. Check logs for details.'}
                        </Alert>
                      )}
                    </Box>
                  </Grid>
                </Grid>
              </Paper>
            )}
            
            {/* Step 3: Extraction Testing */}
            {extractionSample.length > 0 && (
              <Paper sx={{ p: 3, mb: 3, bgcolor: 'grey.50' }}>
                <Typography variant="h6" gutterBottom>
                  Step 3: Company Offering Extraction
                </Typography>
                <Grid container spacing={3}>
                  <Grid item xs={12} md={6}>
                    <FormControl fullWidth sx={{ mb: 2 }}>
                      <InputLabel>Text Model</InputLabel>
                      <Select
                        value={selectedTextModel}
                        onChange={(e) => setSelectedTextModel(e.target.value)}
                        label="Text Model"
                        disabled={modelsLoading || gpuStatus === 'error'}
                      >
                        {modelsLoading ? (
                          <MenuItem disabled>
                            <CircularProgress size={16} sx={{ mr: 1 }} />
                            Loading models...
                          </MenuItem>
                        ) : availableModels.text && availableModels.text.length > 0 ? (
                          availableModels.text.map((model) => (
                            <MenuItem key={model.model_name} value={model.model_name}>
                              {model.model_name}
                            </MenuItem>
                          ))
                        ) : (
                          <MenuItem disabled>
                            No models available - GPU may be offline
                          </MenuItem>
                        )}
                      </Select>
                    </FormControl>
                    
                    <TextField
                      fullWidth
                      multiline
                      rows={4}
                      label="Extraction Prompt"
                      value={extractionPrompt}
                      onChange={(e) => setExtractionPrompt(e.target.value)}
                      placeholder="Loading actual prompt from database..."
                    />
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                      <Button 
                        variant="contained" 
                        color="secondary"
                        onClick={runExtractionTest}
                        disabled={!selectedTextModel || !extractionPrompt}
                        startIcon={<DataUsage />}
                      >
                        Run Extraction Test
                      </Button>
                      
                      <Alert severity="info">
                        This will test company offering extraction on your sample using the selected model and prompt. Results will be saved for comparison.
                      </Alert>
                    </Box>
                  </Grid>
                </Grid>
              </Paper>
            )}
            
            {/* Step 4: Experiments Results */}
            <Paper sx={{ p: 3, bgcolor: 'grey.50' }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6">
                  Extraction Experiments History ({experiments.length})
                </Typography>
                <Box sx={{ display: 'flex', gap: 1 }}>
                  <Button 
                    size="small" 
                    variant={comparisonMode ? 'contained' : 'outlined'}
                    onClick={toggleComparisonMode}
                    disabled={experiments.length < 2}
                  >
                    {comparisonMode ? 'Exit Comparison' : 'Compare Experiments'}
                  </Button>
                  {comparisonMode && selectedExperiments.length >= 2 && (
                    <Button 
                      size="small" 
                      variant="contained" 
                      color="secondary"
                      onClick={() => {/* TODO: Open comparison view */}}
                    >
                      Compare ({selectedExperiments.length})
                    </Button>
                  )}
                </Box>
              </Box>
              
              {experiments.length === 0 ? (
                <Typography variant="body2" color="text.secondary">
                  No extraction experiments run yet. Complete the steps above to create your first experiment.
                </Typography>
              ) : (
                <TableContainer>
                  <Table>
                    <TableHead>
                      <TableRow>
                        {comparisonMode && <TableCell padding="checkbox"></TableCell>}
                        <TableCell>Experiment Name</TableCell>
                        <TableCell>Text Model</TableCell>
                        <TableCell>Success Rate</TableCell>
                        <TableCell>Avg. Response Length</TableCell>
                        <TableCell>Created</TableCell>
                        <TableCell>Actions</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {experiments.map((experiment) => {
                        const successRate = Math.round((experiment.successful_extractions / experiment.total_decks) * 100);
                        return (
                          <TableRow 
                            key={experiment.id}
                            selected={selectedExperiments.includes(experiment.id)}
                            hover={comparisonMode}
                            onClick={comparisonMode ? () => handleExperimentSelection(experiment.id) : undefined}
                            sx={{ cursor: comparisonMode ? 'pointer' : 'default' }}
                          >
                            {comparisonMode && (
                              <TableCell padding="checkbox">
                                <input
                                  type="checkbox"
                                  checked={selectedExperiments.includes(experiment.id)}
                                  onChange={() => handleExperimentSelection(experiment.id)}
                                />
                              </TableCell>
                            )}
                            <TableCell>
                              <Box>
                                <Typography variant="body2" sx={{ fontWeight: 'medium' }}>
                                  {experiment.experiment_name}
                                </Typography>
                                <Typography variant="caption" color="text.secondary">
                                  ID: {experiment.id}
                                </Typography>
                              </Box>
                            </TableCell>
                            <TableCell>
                              <Chip label={experiment.text_model_used} size="small" />
                            </TableCell>
                            <TableCell>
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                <Typography variant="body2">
                                  {experiment.successful_extractions}/{experiment.total_decks}
                                </Typography>
                                <Chip
                                  label={`${successRate}%`}
                                  size="small"
                                  color={successRate >= 80 ? 'success' : successRate >= 60 ? 'warning' : 'error'}
                                  variant="outlined"
                                />
                              </Box>
                            </TableCell>
                            <TableCell>
                              <Typography variant="body2" color="text.secondary">
                                ~{(() => {
                                  if (!experiment.results || experiment.results.length === 0) return 0;
                                  const successfulExtractions = experiment.results.filter(
                                    result => result.offering_extraction && !result.offering_extraction.startsWith('Error:')
                                  );
                                  if (successfulExtractions.length === 0) return 0;
                                  const totalLength = successfulExtractions.reduce(
                                    (sum, result) => sum + (result.offering_extraction?.length || 0), 0
                                  );
                                  return Math.round(totalLength / successfulExtractions.length);
                                })()} chars
                              </Typography>
                            </TableCell>
                            <TableCell>
                              <Typography variant="body2">
                                {new Date(experiment.created_at).toLocaleDateString()}
                              </Typography>
                              <Typography variant="caption" color="text.secondary">
                                {new Date(experiment.created_at).toLocaleTimeString()}
                              </Typography>
                            </TableCell>
                            <TableCell>
                              <Button 
                                size="small" 
                                variant="outlined"
                                onClick={() => viewExperimentDetails(experiment)}
                              >
                                View Details
                              </Button>
                            </TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </Paper>
          </Box>
        )}
      </Paper>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteDialogOpen}
        onClose={() => setDeleteDialogOpen(false)}
      >
        <DialogTitle>Delete Training File</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete "{fileToDelete?.filename}"?
            This action cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>
            Cancel
          </Button>
          <Button
            onClick={() => handleDeleteFile(fileToDelete?.id)}
            color="error"
            variant="contained"
          >
            Delete
          </Button>
        </DialogActions>
      </Dialog>

      {/* Experiment Details Dialog */}
      <Dialog
        open={experimentDetailsOpen}
        onClose={() => setExperimentDetailsOpen(false)}
        maxWidth="lg"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Box>
              <Typography variant="h6">
                Experiment Details: {selectedExperiment?.experiment_name}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Created: {selectedExperiment?.created_at && new Date(selectedExperiment.created_at).toLocaleString()}
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Chip label={selectedExperiment?.text_model_used} size="small" />
              <Chip 
                label={`${Math.round((selectedExperiment?.successful_extractions / selectedExperiment?.total_decks) * 100)}% Success`}
                size="small" 
                color="primary"
              />
            </Box>
          </Box>
        </DialogTitle>
        <DialogContent dividers>
          {loadingExperimentDetails ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
              <CircularProgress />
              <Typography sx={{ ml: 2 }}>Loading experiment details...</Typography>
            </Box>
          ) : experimentDetails ? (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
              {/* Experiment Overview */}
              <Paper sx={{ p: 2, bgcolor: 'grey.50' }}>
                <Typography variant="subtitle1" gutterBottom sx={{ fontWeight: 'medium' }}>
                  Experiment Overview
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={6} md={3}>
                    <Typography variant="caption" color="text.secondary">Total Decks</Typography>
                    <Typography variant="h6">{experimentDetails.total_decks}</Typography>
                  </Grid>
                  <Grid item xs={6} md={3}>
                    <Typography variant="caption" color="text.secondary">Successful Extractions</Typography>
                    <Typography variant="h6" color="success.main">{experimentDetails.successful_extractions}</Typography>
                  </Grid>
                  <Grid item xs={6} md={3}>
                    <Typography variant="caption" color="text.secondary">Success Rate</Typography>
                    <Typography variant="h6">
                      {Math.round((experimentDetails.successful_extractions / experimentDetails.total_decks) * 100)}%
                    </Typography>
                  </Grid>
                  <Grid item xs={6} md={3}>
                    <Typography variant="caption" color="text.secondary">Model Used</Typography>
                    <Typography variant="body2">{experimentDetails.text_model_used}</Typography>
                  </Grid>
                </Grid>
              </Paper>

              {/* Extraction Prompt */}
              <Paper sx={{ p: 2, bgcolor: 'info.light', color: 'info.contrastText' }}>
                <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 'medium' }}>
                  Extraction Prompt Used
                </Typography>
                <Typography variant="body2" sx={{ fontFamily: 'monospace', whiteSpace: 'pre-wrap' }}>
                  {experimentDetails.extraction_prompt}
                </Typography>
              </Paper>

              {/* Individual Results */}
              <Box>
                <Typography variant="subtitle1" gutterBottom sx={{ fontWeight: 'medium' }}>
                  Individual Extraction Results ({experimentDetails.results?.length || 0} decks)
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  Showing results for each deck in the sample. Click on a result to see the full extraction.
                </Typography>
                
                <List>
                  {experimentDetails.results?.map((result, index) => {
                    const isSuccess = !result.offering_extraction.startsWith('Error:');
                    const extractionLength = result.offering_extraction?.length || 0;
                    
                    return (
                      <ListItem key={index} divider>
                        <ListItemIcon>
                          {isSuccess ? (
                            <CheckCircle color="success" />
                          ) : (
                            <Error color="error" />
                          )}
                        </ListItemIcon>
                        <ListItemText
                          primary={
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                              <Box>
                                <Typography variant="body2" sx={{ fontWeight: 'medium' }}>
                                  {result.deck_info?.filename || result.filename || `Deck ${result.deck_id}`}
                                </Typography>
                                {result.deck_info?.company_name && (
                                  <Typography variant="caption" color="text.secondary">
                                    Company: {result.deck_info.company_name}
                                  </Typography>
                                )}
                              </Box>
                              <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                                <Typography variant="caption" color="text.secondary">
                                  {extractionLength} chars
                                </Typography>
                                <Chip 
                                  label={isSuccess ? 'Success' : 'Failed'} 
                                  size="small"
                                  color={isSuccess ? 'success' : 'error'}
                                  variant="outlined"
                                />
                                {result.visual_analysis_used && (
                                  <Chip 
                                    label="Visual Used" 
                                    size="small"
                                    color="info"
                                    variant="outlined"
                                  />
                                )}
                              </Box>
                            </Box>
                          }
                          secondary={
                            <Box sx={{ mt: 1 }}>
                              <Typography variant="body2" color="text.primary">
                                {isSuccess 
                                  ? `${result.offering_extraction.substring(0, 150)}${result.offering_extraction.length > 150 ? '...' : ''}`
                                  : result.offering_extraction
                                }
                              </Typography>
                            </Box>
                          }
                        />
                        <ListItemSecondaryAction>
                          <Button 
                            size="small" 
                            variant="outlined"
                            onClick={() => {
                              // TODO: Show full extraction in a dialog
                              console.log('Full extraction:', result.offering_extraction);
                            }}
                          >
                            View Full
                          </Button>
                        </ListItemSecondaryAction>
                      </ListItem>
                    );
                  })}
                </List>
              </Box>
            </Box>
          ) : (
            <Typography>No experiment details available</Typography>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setExperimentDetailsOpen(false)}>
            Close
          </Button>
          <Button variant="contained" disabled>
            Export Results
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default DojoManagement;