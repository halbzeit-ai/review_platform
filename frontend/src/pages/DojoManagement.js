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
  InputLabel,
  Checkbox,
  FormControlLabel
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
  const { t } = useTranslation(['dojo', 'common']);
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
  const [fullExtractionDialogOpen, setFullExtractionDialogOpen] = useState(false);
  const [selectedExtractionResult, setSelectedExtractionResult] = useState(null);
  
  // Classification state
  const [classificationLoading, setClassificationLoading] = useState(false);
  const [classificationResults, setClassificationResults] = useState({});
  const [selectFromCached, setSelectFromCached] = useState(false);
  const [cachedDecksCount, setCachedDecksCount] = useState(0);
  const [loadingCachedCount, setLoadingCachedCount] = useState(false);

  useEffect(() => {
    loadDojoData();
    loadAvailableModels();
  }, []);

  // Load cached decks count when checkbox is checked
  useEffect(() => {
    if (selectFromCached) {
      loadCachedDecksCount();
    }
  }, [selectFromCached]);

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

  const loadCachedDecksCount = async () => {
    try {
      setLoadingCachedCount(true);
      const user = JSON.parse(localStorage.getItem('user'));
      const token = user?.token;

      const response = await fetch('/api/dojo/extraction-test/cached-count', {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        setCachedDecksCount(data.cached_count || 0);
      } else {
        setCachedDecksCount(0);
      }
    } catch (err) {
      console.error('Error loading cached decks count:', err);
      setCachedDecksCount(0);
    } finally {
      setLoadingCachedCount(false);
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
        body: JSON.stringify({ 
          sample_size: 10,
          cached_only: selectFromCached
        })
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
        
        // Clear the current sample since cache was cleared
        setExtractionSample([]);
        
        // Refresh cached count if using cached selection
        if (selectFromCached) {
          loadCachedDecksCount();
        }
        
        // Clear any existing errors
        setError(null);
        
        // Show success message
        console.log('Visual analysis cache cleared successfully');
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

  // Classification enrichment function
  const runClassificationEnrichment = async (experimentId) => {
    setClassificationLoading(true);
    try {
      const user = JSON.parse(localStorage.getItem('user'));
      const token = user?.token;

      const response = await fetch('/api/dojo/extraction-test/run-classification', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          experiment_id: experimentId
        })
      });

      if (!response.ok) {
        throw new Error('Failed to run classification enrichment');
      }

      const data = await response.json();
      
      // Store classification results
      setClassificationResults(prev => ({
        ...prev,
        [experimentId]: data
      }));

      // Refresh experiments list to show updated status
      await loadExperiments();
      
      // If experiment details is open for this experiment, refresh it
      if (selectedExperiment?.id === experimentId) {
        await viewExperimentDetails(selectedExperiment);
      }

    } catch (err) {
      console.error('Error running classification:', err);
      setError(err.message || 'Failed to run classification');
    } finally {
      setClassificationLoading(false);
    }
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



      {/* Main Content - Tabs */}
      <Paper sx={{ p: 3 }}>
        <Tabs value={currentTab} onChange={handleTabChange}>
          <Tab label={t('tabs.trainingFiles')} />
          <Tab label={t('tabs.extractionTestingLab')} />
        </Tabs>
        
        {/* Tab Panel 0: Files Table */}
        {currentTab === 0 && (
          <Box sx={{ mt: 3 }}>
            {/* Upload Section inside Training Files Tab */}
            <Card sx={{ mb: 3 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  {t('fileManagement.uploadTrainingData')}
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
                          {processingStatus || (uploadProgress < 100 ? t('status.uploading', { progress: uploadProgress }) : t('status.processingFiles'))}
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
                          {uploadSuccess ? t('status.success') : (uploadProgress < 100 ? t('status.uploadingShort') : t('status.processing'))}
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
                            setError(t('messages.uploadCancelled'));
                          }}
                        >
                          {t('actions.cancelUpload')}
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
                      {t('fileManagement.selectZipFile')}
                      <input
                        type="file"
                        hidden
                        accept=".zip"
                        onChange={handleFileUpload}
                      />
                    </Button>
                  </Box>
                )}
              </CardContent>
            </Card>

            <Typography variant="h6" gutterBottom>
              {t('tabs.trainingFiles')}
            </Typography>
        
            {files.length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                {t('fileManagement.noFilesUploaded')}
              </Typography>
            ) : (
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>{t('fileManagement.filename')}</TableCell>
                      <TableCell>{t('status.title')}</TableCell>
                      <TableCell>{t('fileManagement.startupName')}</TableCell>
                      <TableCell>{t('fileManagement.uploaded')}</TableCell>
                      <TableCell>{t('actions.title')}</TableCell>
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
              
              {/* Cached Selection Option */}
              <Box sx={{ mb: 2 }}>
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={selectFromCached}
                      onChange={(e) => setSelectFromCached(e.target.checked)}
                    />
                  }
                  label={
                    <Box>
                      <Typography variant="body2">
                        Select from cached decks only
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        Prioritize decks with existing visual analysis for faster demo
                      </Typography>
                    </Box>
                  }
                />
                {selectFromCached && (
                  <Box sx={{ ml: 4, mt: 1 }}>
                    {loadingCachedCount ? (
                      <Typography variant="caption" color="info.main">
                        🔄 Loading available cached decks...
                      </Typography>
                    ) : cachedDecksCount === 0 ? (
                      <Alert severity="warning" size="small" sx={{ maxWidth: 400 }}>
                        <Typography variant="caption">
                          ⚠️ No cached decks available. Run visual analysis first or uncheck this option.
                        </Typography>
                      </Alert>
                    ) : (
                      <Typography variant="caption" color="success.main">
                        ✅ {cachedDecksCount} cached decks available for quick sampling
                      </Typography>
                    )}
                  </Box>
                )}
              </Box>
              
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
                <Button 
                  variant="outlined" 
                  onClick={createExtractionSample}
                  disabled={loading}
                >
                  Generate Random Sample {selectFromCached ? '(Cached Only)' : '(Up to 10 decks)'}
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
                      <InputLabel>{t('models.visionModel')}</InputLabel>
                      <Select
                        value={selectedVisionModel}
                        onChange={(e) => setSelectedVisionModel(e.target.value)}
                        label={t('models.visionModel')}
                        disabled={modelsLoading || gpuStatus === 'error'}
                      >
                        {modelsLoading ? (
                          <MenuItem disabled>
                            <CircularProgress size={16} sx={{ mr: 1 }} />
                            {t('models.loadingModels')}
                          </MenuItem>
                        ) : availableModels.vision && availableModels.vision.length > 0 ? (
                          availableModels.vision.map((model) => (
                            <MenuItem key={model.model_name} value={model.model_name}>
                              {model.model_name}
                            </MenuItem>
                          ))
                        ) : (
                          <MenuItem disabled>
                            {t('models.noModelsAvailable')}
                          </MenuItem>
                        )}
                      </Select>
                    </FormControl>
                    
                    <TextField
                      fullWidth
                      multiline
                      rows={3}
                      label={t('prompts.visualAnalysisPrompt')}
                      value={visualAnalysisPrompt}
                      onChange={(e) => setVisualAnalysisPrompt(e.target.value)}
                      placeholder={t('prompts.loadingPrompt')}
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
                        {visualAnalysisStatus === 'running' ? t('experiments.runningAnalysis') : t('experiments.runVisualAnalysis')}
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
                            {t('models.noModelsAvailable')}
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
                      placeholder={t('prompts.loadingPrompt')}
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
                        <TableCell>Classification</TableCell>
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
                              {experiment.classification_enabled ? (
                                experiment.classification_completed_at ? (
                                  <Chip 
                                    label="Classified" 
                                    size="small" 
                                    color="success" 
                                    variant="outlined"
                                  />
                                ) : (
                                  <Chip 
                                    label="In Progress" 
                                    size="small" 
                                    color="warning" 
                                    variant="outlined"
                                  />
                                )
                              ) : (
                                <Typography variant="caption" color="text.secondary">
                                  Not classified
                                </Typography>
                              )}
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
                              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                                <Button 
                                  size="small" 
                                  variant="outlined"
                                  onClick={() => viewExperimentDetails(experiment)}
                                >
                                  View Details
                                </Button>
                                {!experiment.classification_completed_at && (
                                  <Button 
                                    size="small" 
                                    variant="contained"
                                    color="secondary"
                                    onClick={() => runClassificationEnrichment(experiment.id)}
                                    disabled={classificationLoading}
                                    sx={{ minWidth: 'auto', px: 1 }}
                                  >
                                    {classificationLoading ? '...' : 'Classify'}
                                  </Button>
                                )}
                              </Box>
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
                  {experimentDetails.classification_enabled && (
                    <Grid item xs={12}>
                      <Divider sx={{ my: 1 }} />
                      <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 'medium' }}>
                        Classification Results
                      </Typography>
                      <Grid container spacing={2}>
                        <Grid item xs={6} md={3}>
                          <Typography variant="caption" color="text.secondary">Classified</Typography>
                          <Typography variant="h6" color="success.main">
                            {experimentDetails.classification_statistics?.successful_classifications || 0}
                          </Typography>
                        </Grid>
                        <Grid item xs={6} md={3}>
                          <Typography variant="caption" color="text.secondary">Classification Rate</Typography>
                          <Typography variant="h6">
                            {Math.round((experimentDetails.classification_statistics?.success_rate || 0) * 100)}%
                          </Typography>
                        </Grid>
                        <Grid item xs={6} md={3}>
                          <Typography variant="caption" color="text.secondary">Avg. Confidence</Typography>
                          <Typography variant="h6">
                            {(experimentDetails.classification_statistics?.average_confidence || 0).toFixed(2)}
                          </Typography>
                        </Grid>
                        <Grid item xs={6} md={3}>
                          <Typography variant="caption" color="text.secondary">Top Sector</Typography>
                          <Typography variant="body2">
                            {Object.entries(experimentDetails.classification_statistics?.sector_distribution || {})
                              .sort(([,a], [,b]) => b - a)[0]?.[0] || 'None'}
                          </Typography>
                        </Grid>
                      </Grid>
                    </Grid>
                  )}
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
                    
                    // Get classification data from the experiment's classification results
                    const classificationData = experimentDetails.classification_results_json && 
                      JSON.parse(experimentDetails.classification_results_json)[result.deck_id];
                    
                    return (
                      <ListItem 
                        key={index} 
                        divider
                        sx={{ 
                          py: 2,
                          '& .MuiListItemSecondaryAction-root': {
                            right: 16,
                            top: '50%',
                            transform: 'translateY(-50%)'
                          }
                        }}
                      >
                        <ListItemText
                          sx={{ pr: 12 }}
                          primary={
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                              <Box sx={{ flex: 1, minWidth: 0 }}>
                                <Typography variant="body2" sx={{ fontWeight: 'medium', mb: 0.5 }}>
                                  {result.deck_info?.filename || result.filename || `Deck ${result.deck_id}`}
                                </Typography>
                                {result.deck_info?.company_name && (
                                  <Typography variant="caption" color="text.secondary">
                                    Company: {result.deck_info.company_name}
                                  </Typography>
                                )}
                                {classificationData && (
                                  <Box sx={{ mt: 0.5, display: 'flex', gap: 1, alignItems: 'center', flexWrap: 'wrap' }}>
                                    <Chip 
                                      label={classificationData.primary_sector || 'Unknown'}
                                      size="small"
                                      color="secondary"
                                      variant="filled"
                                      sx={{ fontSize: '0.65rem', height: '20px' }}
                                    />
                                    {classificationData.confidence_score && (
                                      <Typography variant="caption" color="text.secondary">
                                        {Math.round(classificationData.confidence_score * 100)}% confidence
                                      </Typography>
                                    )}
                                  </Box>
                                )}
                              </Box>
                              <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', flexShrink: 0 }}>
                                <Typography variant="caption" color="text.secondary">
                                  {extractionLength} chars
                                </Typography>
                                <Typography variant="caption" color="text.secondary">
                                  • {result.deck_info?.page_count || 'N/A'} pages
                                </Typography>
                              </Box>
                            </Box>
                          }
                          secondary={
                            <Box>
                              <Typography 
                                variant="body2" 
                                color="text.primary"
                                sx={{ 
                                  display: '-webkit-box',
                                  WebkitLineClamp: 3,
                                  WebkitBoxOrient: 'vertical',
                                  overflow: 'hidden',
                                  lineHeight: 1.4,
                                  mb: classificationData?.reasoning ? 1 : 0
                                }}
                              >
                                {result.offering_extraction}
                              </Typography>
                              {classificationData?.reasoning && (
                                <Typography 
                                  variant="caption" 
                                  color="text.secondary"
                                  sx={{ 
                                    display: '-webkit-box',
                                    WebkitLineClamp: 2,
                                    WebkitBoxOrient: 'vertical',
                                    overflow: 'hidden',
                                    lineHeight: 1.3,
                                    fontStyle: 'italic'
                                  }}
                                >
                                  Classification reasoning: {classificationData.reasoning}
                                </Typography>
                              )}
                            </Box>
                          }
                        />
                        <ListItemSecondaryAction>
                          <Button 
                            size="small" 
                            variant="outlined"
                            onClick={() => {
                              setSelectedExtractionResult(result);
                              setFullExtractionDialogOpen(true);
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

      {/* Full Extraction Dialog */}
      <Dialog
        open={fullExtractionDialogOpen}
        onClose={() => setFullExtractionDialogOpen(false)}
        maxWidth="md"
        fullWidth
        PaperProps={{
          sx: { maxHeight: '80vh' }
        }}
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Box>
              <Typography variant="h6">
                Full Extraction Result
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {selectedExtractionResult?.deck_info?.filename || selectedExtractionResult?.filename || `Deck ${selectedExtractionResult?.deck_id}`}
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
              <Typography variant="caption" color="text.secondary">
                {selectedExtractionResult?.offering_extraction?.length || 0} characters
              </Typography>
              <Typography variant="caption" color="text.secondary">
                • {selectedExtractionResult?.deck_info?.page_count || 'N/A'} pages
              </Typography>
            </Box>
          </Box>
        </DialogTitle>
        <DialogContent>
          <Box sx={{ mt: 1 }}>
            {/* Classification Information (if available) */}
            {(() => {
              const classificationData = experimentDetails?.classification_results_json && 
                selectedExtractionResult?.deck_id &&
                JSON.parse(experimentDetails.classification_results_json)[selectedExtractionResult.deck_id];
                
              return classificationData && (
                <Box sx={{ mb: 3, p: 2, bgcolor: 'info.light', borderRadius: 1, border: 1, borderColor: 'info.main' }}>
                  <Typography variant="h6" gutterBottom sx={{ fontWeight: 'medium', color: 'info.contrastText' }}>
                    Classification Results
                  </Typography>
                  <Grid container spacing={2}>
                    <Grid item xs={12} md={6}>
                      <Typography variant="body2" color="info.contrastText" sx={{ mb: 1 }}>
                        <strong>Primary Sector:</strong> {classificationData.primary_sector || 'Unknown'}
                      </Typography>
                      {classificationData.subcategory && (
                        <Typography variant="body2" color="info.contrastText" sx={{ mb: 1 }}>
                          <strong>Subcategory:</strong> {classificationData.subcategory}
                        </Typography>
                      )}
                      {classificationData.confidence_score && (
                        <Typography variant="body2" color="info.contrastText" sx={{ mb: 1 }}>
                          <strong>Confidence:</strong> {Math.round(classificationData.confidence_score * 100)}%
                        </Typography>
                      )}
                    </Grid>
                    <Grid item xs={12} md={6}>
                      {classificationData.secondary_sector && (
                        <Typography variant="body2" color="info.contrastText" sx={{ mb: 1 }}>
                          <strong>Secondary Sector:</strong> {classificationData.secondary_sector}
                        </Typography>
                      )}
                      {classificationData.keywords_matched && classificationData.keywords_matched.length > 0 && (
                        <Typography variant="body2" color="info.contrastText" sx={{ mb: 1 }}>
                          <strong>Keywords Matched:</strong> {classificationData.keywords_matched.join(', ')}
                        </Typography>
                      )}
                    </Grid>
                    {classificationData.reasoning && (
                      <Grid item xs={12}>
                        <Typography variant="body2" color="info.contrastText" sx={{ fontStyle: 'italic' }}>
                          <strong>Reasoning:</strong> {classificationData.reasoning}
                        </Typography>
                      </Grid>
                    )}
                  </Grid>
                </Box>
              );
            })()}
            
            {/* Extraction Results */}
            <Typography variant="h6" gutterBottom sx={{ fontWeight: 'medium' }}>
              Company Offering Extraction
            </Typography>
            <Typography 
              variant="body1" 
              color="text.primary"
              sx={{ 
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                lineHeight: 1.6,
                fontFamily: 'monospace',
                p: 2,
                bgcolor: 'grey.50',
                borderRadius: 1,
                border: 1,
                borderColor: 'grey.200'
              }}
            >
              {selectedExtractionResult?.offering_extraction || 'No extraction result available'}
            </Typography>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button 
            onClick={() => {
              if (selectedExtractionResult?.offering_extraction) {
                navigator.clipboard.writeText(selectedExtractionResult.offering_extraction);
              }
            }}
          >
            Copy Text
          </Button>
          <Button onClick={() => setFullExtractionDialogOpen(false)} variant="contained">
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default DojoManagement;