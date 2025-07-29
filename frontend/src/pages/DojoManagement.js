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

  // Helper function to format processing time
  const formatProcessingTime = (milliseconds) => {
    const seconds = Math.floor(milliseconds / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    
    if (hours > 0) {
      return `${hours}h ${minutes % 60}m ${seconds % 60}s`;
    } else if (minutes > 0) {
      return `${minutes}m ${seconds % 60}s`;
    } else {
      return `${seconds}s`;
    }
  };

  // Helper function to get current processing stats
  const getProcessingStats = () => {
    if (!analysisStartTime || processingTimes.length === 0) return null;
    
    const avgTimePerDeck = processingTimes.reduce((sum, time) => sum + time, 0) / processingTimes.length;
    const totalElapsed = Date.now() - analysisStartTime;
    
    return {
      avgTimePerDeck: formatProcessingTime(avgTimePerDeck),
      totalElapsed: formatProcessingTime(totalElapsed)
    };
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
  const [addCompaniesSuccess, setAddCompaniesSuccess] = useState('');
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
  const [selectedTextModel, setSelectedTextModel] = useState('');
  const [currentAnalysisController, setCurrentAnalysisController] = useState(null);
  const [currentStep3Controller, setCurrentStep3Controller] = useState(null);
  const [currentStep4Controller, setCurrentStep4Controller] = useState(null);
  const [clearingCache, setClearingCache] = useState(false);
  const [analysisProgress, setAnalysisProgress] = useState({ completed: 0, total: 0 });
  const [analysisStartTime, setAnalysisStartTime] = useState(null);
  const [lastDeckCompletedTime, setLastDeckCompletedTime] = useState(null);
  const [processingTimes, setProcessingTimes] = useState([]);
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
  const [selectedTemplate, setSelectedTemplate] = useState('');
  const [templateProcessingStatus, setTemplateProcessingStatus] = useState('');
  const [availableTemplates, setAvailableTemplates] = useState([]);
  const [templatesLoading, setTemplatesLoading] = useState(false);
  const [lastExperimentId, setLastExperimentId] = useState(null);

  // Helper function to check if visual analysis is effectively completed
  const isVisualAnalysisCompleted = () => {
    return visualAnalysisStatus === 'completed' || 
           (selectFromCached && extractionSample.length > 0);
  };
  const [fullExtractionDialogOpen, setFullExtractionDialogOpen] = useState(false);
  const [selectedExtractionResult, setSelectedExtractionResult] = useState(null);
  
  // Classification state
  const [classificationLoading, setClassificationLoading] = useState(false);
  const [classificationResults, setClassificationResults] = useState({});
  const [selectFromCached, setSelectFromCached] = useState(false);
  const [cachedDecksCount, setCachedDecksCount] = useState(0);
  const [loadingCachedCount, setLoadingCachedCount] = useState(false);
  const [sampleSize, setSampleSize] = useState(10);
  
  // Data management states
  const [cleanupLoading, setCleanupLoading] = useState(false);
  const [cleanupDialogOpen, setCleanupDialogOpen] = useState(false);
  const [testDataStats, setTestDataStats] = useState(null);

  // Sequential pipeline execution states
  const [runStep3AfterStep2, setRunStep3AfterStep2] = useState(false);
  const [runStep4AfterStep3, setRunStep4AfterStep3] = useState(false);
  const [step3Progress, setStep3Progress] = useState({ completed: 0, total: 0, status: 'idle' });
  const [step4Progress, setStep4Progress] = useState({ completed: 0, total: 0, status: 'idle' });
  
  // Current deck being processed for each step
  const [currentStep2Deck, setCurrentStep2Deck] = useState('');
  const [currentStep3Deck, setCurrentStep3Deck] = useState('');
  const [currentStep4Deck, setCurrentStep4Deck] = useState('');

  useEffect(() => {
    loadDojoData();
    loadAvailableModels();
    loadAvailableTemplates();
  }, []);

  // General polling for current deck progress when any step is processing
  useEffect(() => {
    let pollInterval;
    
    if (step3Progress.status === 'processing' || step4Progress.status === 'processing') {
      pollInterval = setInterval(async () => {
        await fetchCurrentDeckProgress();
      }, 2000); // Poll every 2 seconds for current deck updates
    }
    
    return () => {
      if (pollInterval) {
        clearInterval(pollInterval);
      }
    };
  }, [step3Progress.status, step4Progress.status]);

  // Auto-run Step 4 (template processing) after Step 3 completes if checkbox is enabled
  useEffect(() => {
    if (step3Progress.status === 'completed' && runStep4AfterStep3 && selectedTemplate && step4Progress.status !== 'processing') {
      console.log('Auto-triggering Step 4 (template processing) after Step 3 completion');
      runTemplateProcessing();
    }
  }, [step3Progress.status, runStep4AfterStep3, selectedTemplate, step4Progress.status]);

  // Load cached decks count on component mount and when checkbox is checked
  useEffect(() => {
    loadCachedDecksCount();
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

  const loadAvailableTemplates = async () => {
    try {
      setTemplatesLoading(true);
      const user = JSON.parse(localStorage.getItem('user'));
      const token = user?.token;

      const response = await fetch('/api/healthcare-templates/templates', {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        const templates = await response.json();
        setAvailableTemplates(templates);
      } else {
        console.error('Failed to load templates');
        setAvailableTemplates([]);
      }
    } catch (err) {
      console.error('Error loading templates:', err);
      setAvailableTemplates([]);
    } finally {
      setTemplatesLoading(false);
    }
  };

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
        const count = data.cached_count || 0;
        setCachedDecksCount(count);
        
        // If no cached decks available, auto-uncheck the "cached only" option
        if (count === 0 && selectFromCached) {
          setSelectFromCached(false);
        }
      } else {
        setCachedDecksCount(0);
        // Auto-uncheck if API call failed
        if (selectFromCached) {
          setSelectFromCached(false);
        }
      }
    } catch (err) {
      console.error('Error loading cached decks count:', err);
      setCachedDecksCount(0);
      // Auto-uncheck if API call failed
      if (selectFromCached) {
        setSelectFromCached(false);
      }
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
          sample_size: sampleSize === 'all' ? 999999 : sampleSize,
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
    console.log('🚀 Starting runVisualAnalysis');
    try {
      console.log('📝 Setting visual analysis status to running');
      setVisualAnalysisStatus('running');
      // Reset timing states for fresh analysis
      setAnalysisStartTime(null);
      setLastDeckCompletedTime(null);
      setProcessingTimes([]);
      const user = JSON.parse(localStorage.getItem('user'));
      const token = user?.token;

      // Create AbortController for cancellation
      const controller = new AbortController();
      setCurrentAnalysisController(controller);

      const deckIds = extractionSample.map(deck => deck.id);
      console.log('📊 Extracted deck IDs:', deckIds);
      console.log('🎯 Selected vision model:', selectedVisionModel);
      
      console.log('🌐 Making API request to run-visual-analysis');
      const response = await fetch('/api/dojo/extraction-test/run-visual-analysis', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          deck_ids: deckIds,
          vision_model: selectedVisionModel,
          analysis_prompt: "Analyze this pitch deck. Describe the company's business model, target market, value proposition, financial projections, team background, and key metrics. Focus on extracting structured information that can be used for investment analysis."
        }),
        signal: controller.signal
      });

      console.log('📡 API response status:', response.status);
      if (response.ok) {
        const data = await response.json();
        console.log('✅ Visual analysis batch started:', data);
        
        // Initialize progress tracking
        const total = extractionSample.length;
        const startTime = Date.now();
        console.log('📈 Initializing progress tracking - total:', total);
        setAnalysisProgress({ completed: 0, total });
        setAnalysisStartTime(startTime);
        setLastDeckCompletedTime(null);
        setProcessingTimes([]);
        
        console.log('⏰ Starting polling interval');
        // Start polling for progress updates
        const pollInterval = setInterval(async () => {
          console.log('🔄 Polling for progress updates...');
          const progressData = await fetchCurrentDeckProgress();
          console.log('📊 Progress data received:', progressData);
          
          // During active processing, use backend progress tracker for status transitions
          if (progressData && progressData.step2) {
            const step2Status = progressData.step2.status;
            console.log('🔍 Step2 status:', step2Status);
            
            if (step2Status === 'completed') {
              console.log('✅ Step2 completed - clearing interval');
              clearInterval(pollInterval);
              setVisualAnalysisStatus('completed');
              setCurrentAnalysisController(null);
              // Do a final cache check to get accurate numbers
              await checkAnalysisProgress();
            } else if (step2Status === 'error') {
              console.log('❌ Step2 error - clearing interval');
              clearInterval(pollInterval);
              setVisualAnalysisStatus('error');
              setCurrentAnalysisController(null);
            }
          } else {
            console.log('🔄 Using fallback cache checking');
            // Fallback to cache checking if backend progress is not available
            const progress = await checkAnalysisProgress();
            console.log('📊 Cache progress:', progress);
            if (progress && progress.completed === progress.total) {
              console.log('✅ Cache checking shows completion - clearing interval');
              clearInterval(pollInterval);
              setVisualAnalysisStatus('completed');
              setCurrentAnalysisController(null);
            }
          }
        }, 2000); // Check every 2 seconds for more responsive updates
        
        // Store interval ID so we can clear it if stopped
        controller.pollInterval = pollInterval;
      } else {
        console.log('❌ API request failed with status:', response.status);
        setVisualAnalysisStatus('error');
        let errorMessage = 'Failed to run visual analysis';
        try {
          const errorData = await response.json();
          console.log('📄 Error data:', errorData);
          errorMessage = errorData.detail || errorMessage;
        } catch (parseError) {
          console.error('❌ Error parsing error response:', parseError);
        }
        setError(errorMessage);
      }
    } catch (err) {
      console.log('🚨 Exception caught in runVisualAnalysis:', err);
      if (err.name === 'AbortError') {
        console.log('🛑 Analysis was aborted');
        setVisualAnalysisStatus('cancelled');
        console.log('Visual analysis cancelled by user');
        setError('Visual analysis cancelled');
      } else {
        console.log('❌ Unexpected error:', err);
        setVisualAnalysisStatus('error');
        console.error('Error running visual analysis:', err);
        setError('Failed to run visual analysis');
      }
    } finally {
      console.log('🧹 Running cleanup in finally block');
      // Clear polling interval if it exists - use current state
      if (currentAnalysisController && currentAnalysisController.pollInterval) {
        console.log('⏰ Clearing polling interval');
        clearInterval(currentAnalysisController.pollInterval);
      }
      setCurrentAnalysisController(null);
      console.log('✅ Cleanup completed');
    }
  };

  // Batch visual analysis function
  const runVisualAnalysisBatch = async () => {
    await runVisualAnalysis();
  };

  // Clear analysis cache function
  const clearAnalysisCache = async () => {
    setClearingCache(true);
    try {
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
        // Clear the current sample since cache was cleared
        setExtractionSample([]);
        setError(null);
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

  // Stop current analysis function
  const stopCurrentAnalysis = () => {
    if (currentAnalysisController) {
      currentAnalysisController.abort();
      if (currentAnalysisController.pollInterval) {
        clearInterval(currentAnalysisController.pollInterval);
      }
      setCurrentAnalysisController(null);
      setVisualAnalysisStatus('cancelled');
    }
  };

  // Stop Step 3 extraction pipeline
  const stopStep3Pipeline = () => {
    if (currentStep3Controller) {
      currentStep3Controller.abort();
      setCurrentStep3Controller(null);
      setStep3Progress(prev => ({ ...prev, status: 'cancelled' }));
      setCurrentStep3Deck('Extraction pipeline cancelled');
    }
  };

  // Stop Step 4 template processing
  const stopStep4Processing = () => {
    if (currentStep4Controller) {
      currentStep4Controller.abort();
      setCurrentStep4Controller(null);
      setStep4Progress(prev => ({ ...prev, status: 'cancelled' }));
      setCurrentStep4Deck('Template processing cancelled');
    }
  };

  const fetchCurrentDeckProgress = async () => {
    try {
      const user = JSON.parse(localStorage.getItem('user'));
      const token = user?.token;

      const response = await fetch('/api/dojo/extraction-test/progress', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        const progressData = await response.json();
        
        // Update current deck being processed for each step
        setCurrentStep2Deck(progressData.step2?.current_deck || '');
        setCurrentStep3Deck(progressData.step3?.current_deck || '');
        setCurrentStep4Deck(progressData.step4?.current_deck || '');
        
        // Update step progress statuses and counts
        setStep3Progress(prev => ({ 
          ...prev, 
          completed: progressData.step3?.progress || 0,
          total: progressData.step3?.total || 0,
          status: progressData.step3?.status || 'idle' 
        }));
        setStep4Progress(prev => ({ 
          ...prev, 
          completed: progressData.step4?.progress || 0,
          total: progressData.step4?.total || 0,
          status: progressData.step4?.status || 'idle' 
        }));
        
        // Update visual analysis progress for step 2
        setAnalysisProgress(prev => ({
          ...prev,
          completed: progressData.step2?.progress || 0,
          total: progressData.step2?.total || 0
        }));
        setVisualAnalysisStatus(progressData.step2?.status || 'idle');
        
        return progressData;
      } else {
        console.error('Failed to fetch current deck progress');
        return null;
      }
    } catch (error) {
      console.error('Error fetching current deck progress:', error);
      return null;
    }
  };

  const checkAnalysisProgress = async () => {
    console.log('🔍 Checking analysis progress...');
    try {
      const user = JSON.parse(localStorage.getItem('user'));
      const token = user?.token;

      // Re-fetch the current sample to get updated cache status
      console.log('🌐 Fetching sample for progress check');
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
        console.log('📊 Sample data received:', data);
        
        // Count completed vs total
        const completed = data.sample.filter(deck => deck.has_visual_cache).length;
        const total = data.sample.length;
        console.log(`📈 Progress: ${completed}/${total} completed`);
        
        // Only update sample if there are actual changes to avoid unnecessary re-renders
        const currentCompleted = extractionSample.filter(deck => deck.has_visual_cache).length;
        console.log(`🔄 Current completed: ${currentCompleted}, New completed: ${completed}`);
        if (completed !== currentCompleted) {
          console.log('✨ Updating extraction sample');
          setExtractionSample(data.sample);
        }
        
        // Calculate timing if a new deck was completed
        const currentTime = Date.now();
        let newProcessingTimes = processingTimes;
        
        if (completed > analysisProgress.completed && analysisStartTime) {
          // A new deck was completed - calculate processing time for this deck
          let deckProcessingTime;
          
          if (processingTimes.length === 0) {
            // First deck completed - time from analysis start
            deckProcessingTime = currentTime - analysisStartTime;
          } else {
            // Subsequent decks - time since last completion
            deckProcessingTime = lastDeckCompletedTime ? currentTime - lastDeckCompletedTime : currentTime - analysisStartTime;
          }
          
          newProcessingTimes = [...processingTimes, deckProcessingTime];
          setProcessingTimes(newProcessingTimes);
          setLastDeckCompletedTime(currentTime);
        }
        
        setAnalysisProgress({ completed, total });
        
        const result = { completed, total, processingTimes: newProcessingTimes };
        console.log('📤 Returning progress result:', result);
        return result;
      }
    } catch (err) {
      console.error('❌ Error checking analysis progress:', err);
    }
    console.log('❌ Returning null from checkAnalysisProgress');
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
      
      // Initialize step 3 progress
      setStep3Progress({ completed: 0, total: deckIds.length, status: 'processing' });
      setCurrentStep3Deck('Starting offering extraction...');
      setError(null);
      
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
          use_cached_visual: true
        })
      });

      if (response.ok) {
        const data = await response.json();
        console.log('Extraction test completed:', data);
        setStep3Progress(prev => ({ ...prev, status: 'completed', completed: deckIds.length }));
        setCurrentStep3Deck('Offering extraction completed');
        loadExperiments();
      } else {
        const errorData = await response.json();
        setStep3Progress(prev => ({ ...prev, status: 'error', completed: 0 }));
        setCurrentStep3Deck('Extraction failed');
        setError(errorData.detail || 'Failed to run extraction test');
      }
    } catch (err) {
      console.error('Error running extraction test:', err);
      setStep3Progress(prev => ({ ...prev, status: 'error', completed: 0 }));
      setCurrentStep3Deck('Processing error occurred');
      setError('Failed to run extraction test');
    }
  };

  const runCompleteExtractionPipeline = async () => {
    try {
      const user = JSON.parse(localStorage.getItem('user'));
      const token = user?.token;

      const deckIds = extractionSample.map(deck => deck.id);
      const experimentName = `pipeline_${Date.now()}`;
      
      // Create AbortController for Step 3
      const controller = new AbortController();
      setCurrentStep3Controller(controller);
      
      // Initialize step 3 progress
      setStep3Progress({ completed: 0, total: deckIds.length, status: 'processing' });
      setCurrentStep3Deck('Starting complete extraction pipeline...');
      setError(null);
      
      // Step 3: Run offering extraction
      const offeringResponse = await fetch('/api/dojo/extraction-test/run-offering-extraction', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          experiment_name: experimentName,
          deck_ids: deckIds,
          text_model: selectedTextModel,
          use_cached_visual: true
        }),
        signal: controller.signal
      });

      if (!offeringResponse.ok) {
        const errorData = await offeringResponse.json();
        throw new Error(errorData.detail || 'Failed to run offering extraction');
      }

      const offeringData = await offeringResponse.json();
      const experimentId = offeringData.experiment_id;
      console.log('Step 3 completed: Offering extraction', offeringData);
      
      // Update step 3 as completed, initialize step 4
      setStep3Progress({ completed: deckIds.length, total: deckIds.length, status: 'completed' });
      setCurrentStep3Deck('Offering extraction completed');
      setStep4Progress({ completed: 0, total: deckIds.length, status: 'processing' });
      setCurrentStep4Deck('Starting classification...');

      // Step 4: Run classification on the experiment
      const classificationResponse = await fetch('/api/dojo/extraction-test/run-classification', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          experiment_id: experimentId
        }),
        signal: controller.signal
      });

      if (!classificationResponse.ok) {
        const errorData = await classificationResponse.json();
        console.warn('Step 4 failed: Classification', errorData);
        // Continue even if classification fails
      } else {
        const classificationData = await classificationResponse.json();
        console.log('Step 4 completed: Classification', classificationData);
      }

      // Step 5: Run company name extraction
      const companyNameResponse = await fetch('/api/dojo/extraction-test/run-company-name-extraction', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          experiment_id: experimentId
        }),
        signal: controller.signal
      });

      if (!companyNameResponse.ok) {
        const errorData = await companyNameResponse.json();
        console.warn('Step 5 failed: Company name extraction', errorData);
        // Continue even if company name extraction fails
      } else {
        const companyNameData = await companyNameResponse.json();
        console.log('Step 5 completed: Company name extraction', companyNameData);
      }

      // Step 6: Run funding amount extraction
      const fundingAmountResponse = await fetch('/api/dojo/extraction-test/run-funding-amount-extraction', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          experiment_id: experimentId
        }),
        signal: controller.signal
      });

      if (!fundingAmountResponse.ok) {
        const errorData = await fundingAmountResponse.json();
        console.warn('Step 6 failed: Funding amount extraction', errorData);
        // Continue even if funding amount extraction fails
      } else {
        const fundingAmountData = await fundingAmountResponse.json();
        console.log('Step 6 completed: Funding amount extraction', fundingAmountData);
      }

      // Step 7: Run deck date extraction
      const deckDateResponse = await fetch('/api/dojo/extraction-test/run-deck-date-extraction', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          experiment_id: experimentId
        }),
        signal: controller.signal
      });

      if (!deckDateResponse.ok) {
        const errorData = await deckDateResponse.json();
        console.warn('Step 7 failed: Deck date extraction', errorData);
        // Continue even if deck date extraction fails
      } else {
        const deckDateData = await deckDateResponse.json();
        console.log('Step 7 completed: Deck date extraction', deckDateData);
      }

      // Refresh experiments list
      await loadExperiments();
      
      console.log('Complete extraction pipeline finished successfully');
      
      // Clear the controller on successful completion
      setCurrentStep3Controller(null);
      
    } catch (err) {
      // Clear the controller on error or cancellation
      setCurrentStep3Controller(null);
      
      if (err.name === 'AbortError') {
        console.log('Step 3 extraction pipeline was cancelled');
        setStep3Progress(prev => ({ ...prev, status: 'cancelled' }));
        setCurrentStep3Deck('Extraction pipeline cancelled');
        return;
      }
      
      console.error('Error running complete extraction pipeline:', err);
      setStep3Progress(prev => ({ ...prev, status: 'error' }));
      setCurrentStep3Deck('Extraction pipeline error');
      setError(err.message || 'Failed to run complete extraction pipeline');
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
        // Set the last experiment ID for template processing
        if (data.experiments && data.experiments.length > 0) {
          setLastExperimentId(data.experiments[0].id);
        }
      }
    } catch (err) {
      console.error('Error loading experiments:', err);
    }
  };

  const handleTabChange = (event, newValue) => {
    setCurrentTab(newValue);
    if (newValue === 1) { // Extraction Experiments History tab
      loadExperiments();
    } else if (newValue === 3) { // Data Management tab
      loadTestDataStats();
    }
  };

  const loadExperimentDetails = async (experimentId) => {
    setLoadingExperimentDetails(true);
    
    try {
      const user = JSON.parse(localStorage.getItem('user'));
      const token = user?.token;

      const response = await fetch(`/api/dojo/extraction-test/experiments/${experimentId}`, {
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

  const viewExperimentDetails = async (experiment) => {
    setSelectedExperiment(experiment);
    setExperimentDetailsOpen(true);
    await loadExperimentDetails(experiment.id);
  };

  const getSampleFromExperiment = async (experiment) => {
    try {
      const user = JSON.parse(localStorage.getItem('user'));
      const token = user?.token;

      // Get the experiment details to extract the deck IDs
      const response = await fetch(`/api/dojo/extraction-test/experiments/${experiment.id}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (!response.ok) {
        throw new Error('Failed to fetch experiment details');
      }

      const experimentDetails = await response.json();
      console.log('Full experiment details:', experimentDetails); // Debug log
      console.log('All experiment detail keys:', Object.keys(experimentDetails)); // Debug log
      
      let deckIds = experimentDetails.pitch_deck_ids || [];
      console.log('Extracted deck IDs from pitch_deck_ids:', deckIds); // Debug log

      if (deckIds.length === 0) {
        console.log('No deck IDs found in pitch_deck_ids. Trying alternative field names...'); // Debug log
        
        // Try all possible field names that might contain deck IDs
        const possibleFields = [
          'deck_ids',
          'pitch_decks', 
          'deck_list',
          'sample_deck_ids',
          'experiment_deck_ids'
        ];
        
        for (const field of possibleFields) {
          if (experimentDetails[field]) {
            console.log(`Found deck IDs in field '${field}':`, experimentDetails[field]);
            deckIds = Array.isArray(experimentDetails[field]) ? experimentDetails[field] : [experimentDetails[field]];
            break;
          }
        }
        
        // Try extracting from results array
        if (deckIds.length === 0 && experimentDetails.results && Array.isArray(experimentDetails.results)) {
          console.log('Trying to extract deck IDs from results array...');
          deckIds = experimentDetails.results.map(r => r.deck_id).filter(id => id != null);
          console.log('Deck IDs from results:', deckIds);
        }
        
        if (deckIds.length === 0) {
          console.log('Still no deck IDs found. Full experiment details:', experimentDetails);
          setError('No decks found in this experiment - check console for details');
          return;
        }
      }

      // Fetch the file details for these deck IDs to recreate the sample
      const filesResponse = await fetch('/api/dojo/files', {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (!filesResponse.ok) {
        throw new Error('Failed to fetch files');
      }

      const allFiles = await filesResponse.json();
      
      // Handle case where API returns object with files property or direct array
      const filesArray = Array.isArray(allFiles) ? allFiles : (allFiles.files || allFiles.data || []);
      
      // Filter files to match the experiment's deck IDs
      const experimentSample = filesArray.filter(file => deckIds.includes(file.id));

      // Set this as the current extraction sample
      setExtractionSample(experimentSample);
      
      // Switch to the Extraction Testing Lab tab if not already there
      setCurrentTab(0);
      
      console.log(`Sample recreated from experiment ${experiment.experiment_name}:`, experimentSample);
      
      // Show success message
      setError(null);
      
    } catch (err) {
      console.error('Error getting sample from experiment:', err);
      setError(err.message || 'Failed to get sample from experiment');
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

  // Run template-based processing for experiment results
  const runTemplateProcessing = async () => {
    if ((!lastExperimentId && !isVisualAnalysisCompleted()) || !selectedTemplate) {
      setError('Please select a template and ensure visual analysis is completed');
      return;
    }

    try {
      // Create AbortController for Step 4
      const controller = new AbortController();
      setCurrentStep4Controller(controller);
      
      setTemplateProcessingStatus('processing');
      setError(null);

      const user = JSON.parse(localStorage.getItem('user'));
      const token = user?.token;

      // Use the existing experiment ID or create a new one
      let experimentId = lastExperimentId;
      
      if (!experimentId && extractionSample.length > 0) {
        // If no experiment ID but we have a sample, we need to create a new experiment first
        const deckIds = extractionSample.map(item => item.id);
        const experimentName = `template_processing_${Date.now()}`;
        
        // Create experiment by running offering extraction first (required for experiment creation)
        const offeringResponse = await fetch('/api/dojo/extraction-test/run-offering-extraction', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            experiment_name: experimentName,
            deck_ids: deckIds,
            text_model: selectedTextModel || 'gemma3:27b',
            use_cached_visual: true
          }),
          signal: controller.signal
        });

        if (!offeringResponse.ok) {
          const errorData = await offeringResponse.json();
          throw new Error(errorData.detail || 'Failed to create experiment for template processing');
        }

        const offeringData = await offeringResponse.json();
        experimentId = offeringData.experiment_id;
        console.log('Created experiment for template processing:', experimentId);
      }

      if (!experimentId) {
        throw new Error('No experiment available for template processing');
      }

      // Run batch template processing on the entire experiment
      const response = await fetch('/api/dojo/extraction-test/run-template-processing', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          experiment_id: experimentId,
          template_id: selectedTemplate ? parseInt(selectedTemplate, 10) : null,
          generate_thumbnails: true
        }),
        signal: controller.signal
      });

      if (!response.ok) {
        const errorData = await response.json();
        setStep4Progress(prev => ({ ...prev, status: 'error', completed: 0 }));
        setCurrentStep4Deck('Template processing failed');
        throw new Error(errorData.detail || 'Failed to run template processing');
      }

      const result = await response.json();
      console.log('Template processing completed:', result);
      
      // Update step 4 as completed
      const deckCount = extractionSample.length;
      setStep4Progress(prev => ({ ...prev, status: 'completed', completed: deckCount }));
      setCurrentStep4Deck('Template processing completed');
      
      setTemplateProcessingStatus('completed');
      
      // Refresh experiments to show updated results
      await loadExperiments();

      // Clear the controller on successful completion
      setCurrentStep4Controller(null);

    } catch (err) {
      // Clear the controller on error or cancellation
      setCurrentStep4Controller(null);
      
      if (err.name === 'AbortError') {
        console.log('Step 4 template processing was cancelled');
        setStep4Progress(prev => ({ ...prev, status: 'cancelled' }));
        setCurrentStep4Deck('Template processing cancelled');
        setTemplateProcessingStatus('cancelled');
        return;
      }
      
      console.error('Error running template processing:', err);
      setStep4Progress(prev => ({ ...prev, status: 'error', completed: 0 }));
      setCurrentStep4Deck('Processing error occurred');
      setError(err.message || 'Failed to run template processing');
      setTemplateProcessingStatus('error');
    }
  };

  // Check if experiment has required extractions for adding companies
  const canAddDojoCompanies = (experimentDetails) => {
    if (!experimentDetails || !experimentDetails.results) return false;
    
    // Check if experiment has classification, company offering, and company name extractions
    const hasClassification = experimentDetails.classification_enabled && 
                             experimentDetails.classification_results_json;
    
    // Check if results contain company offering extraction
    const hasOfferingExtraction = experimentDetails.results.some(result => 
      result.offering_extraction && 
      !result.offering_extraction.startsWith('Error:') && 
      result.offering_extraction.length > 10
    );
    
    // Check if results contain company name (from deck_info or AI extraction)
    const hasCompanyName = experimentDetails.results.some(result => 
      (result.deck_info?.company_name) || 
      (result.ai_extracted_startup_name)
    );
    
    return hasClassification && hasOfferingExtraction && hasCompanyName;
  };

  // Run missing extractions for experiment
  const runClassificationEnrichment = async (experimentId) => {
    try {
      const user = JSON.parse(localStorage.getItem('user'));
      const token = user?.token;
      
      const response = await fetch('/api/dojo/extraction-test/run-classification', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ experiment_id: experimentId })
      });
      
      if (response.ok) {
        setError(null);
        // Reload experiment details to show classification data
        await loadExperimentDetails(experimentId);
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to run classification');
      }
    } catch (err) {
      console.error('Error running classification:', err);
      setError('Failed to run classification');
    }
  };
  
  const runFundingAmountExtraction = async (experimentId) => {
    try {
      const user = JSON.parse(localStorage.getItem('user'));
      const token = user?.token;
      
      const response = await fetch('/api/dojo/extraction-test/run-funding-amount-extraction', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ experiment_id: experimentId })
      });
      
      if (response.ok) {
        setError(null);
        // Reload experiment details to show funding data
        await loadExperimentDetails(experimentId);
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to run funding extraction');
      }
    } catch (err) {
      console.error('Error running funding extraction:', err);
      setError('Failed to run funding extraction');
    }
  };
  
  const runCompanyNameExtraction = async (experimentId) => {
    try {
      const user = JSON.parse(localStorage.getItem('user'));
      const token = user?.token;
      
      const response = await fetch('/api/dojo/extraction-test/run-company-name-extraction', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ experiment_id: experimentId })
      });
      
      if (response.ok) {
        setError(null);
        // Reload experiment details to show company name data
        await loadExperimentDetails(experimentId);
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to run company name extraction');
      }
    } catch (err) {
      console.error('Error running company name extraction:', err);
      setError('Failed to run company name extraction');
    }
  };

  // Add companies from experiment to projects database
  const addDojoCompanies = async () => {
    if (!experimentDetails) return;
    
    try {
      const user = JSON.parse(localStorage.getItem('user'));
      const token = user?.token;
      
      const response = await fetch('/api/dojo-experiments/add-companies', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          experiment_id: selectedExperiment.id
        })
      });

      if (response.ok) {
        const result = await response.json();
        console.log('Companies added successfully:', result);
        setAddCompaniesSuccess(`Successfully added ${result.companies_added} companies and created ${result.projects_created} projects!`);
        setError(null);
        setExperimentDetailsOpen(false);
        // Clear success message after 5 seconds
        setTimeout(() => setAddCompaniesSuccess(''), 5000);
      } else {
        const errorData = await response.json();
        console.error('Failed to add companies:', errorData);
        setError(errorData.detail || 'Failed to add companies to projects database');
      }
    } catch (err) {
      console.error('Error adding companies:', err);
      setError('Failed to add companies to projects database');
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

  // Load test data statistics for data management tab
  const loadTestDataStats = async () => {
    try {
      const user = JSON.parse(localStorage.getItem('user'));
      const token = user?.token;

      const response = await fetch('/api/dojo-experiments/stats', {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        const stats = await response.json();
        setTestDataStats(stats);
      }
    } catch (err) {
      console.error('Error loading test data stats:', err);
    }
  };

  // Clean up dojo projects while preserving experimental data
  const cleanupDojoProjects = async () => {
    try {
      setCleanupLoading(true);
      const user = JSON.parse(localStorage.getItem('user'));
      const token = user?.token;

      const response = await fetch('/api/dojo-experiments/cleanup-dojo-projects', {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        const result = await response.json();
        setAddCompaniesSuccess(`Successfully cleaned up ${result.projects_deleted} dojo projects and ${result.documents_deleted} documents. All experimental data preserved.`);
        setError(null);
        // Refresh stats
        await loadTestDataStats();
        // Clear success message after 8 seconds
        setTimeout(() => setAddCompaniesSuccess(''), 8000);
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to cleanup dojo projects');
      }
    } catch (err) {
      console.error('Error cleaning up dojo projects:', err);
      setError('Failed to cleanup dojo projects');
    } finally {
      setCleanupLoading(false);
      setCleanupDialogOpen(false);
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

      {/* Success Alert */}
      {addCompaniesSuccess && (
        <Alert severity="success" sx={{ mb: 3 }} onClose={() => setAddCompaniesSuccess('')}>
          {addCompaniesSuccess}
        </Alert>
      )}



      {/* Main Content - Tabs */}
      <Paper sx={{ p: 3 }}>
        <Tabs value={currentTab} onChange={handleTabChange}>
          <Tab label={t('tabs.extractionTestingLab')} />
          <Tab label="Extraction Experiments History" />
          <Tab label={t('tabs.trainingFiles')} />
          <Tab label="Data Management" />
        </Tabs>
        
        {/* Tab Panel 0: Extraction Testing Lab */}
        {currentTab === 0 && (
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
            
            {/* Step 1: Sample Selection */}
            <Paper sx={{ p: 3, mb: 3, bgcolor: 'grey.50' }}>
              <Typography variant="h6" gutterBottom>
                Step 1: Create Sample
              </Typography>
              
              {/* Sample Size Selection */}
              <Box sx={{ mb: 2 }}>
                <FormControl sx={{ minWidth: 200, mb: 2 }}>
                  <InputLabel>Sample Size</InputLabel>
                  <Select
                    value={sampleSize}
                    label="Sample Size"
                    onChange={(e) => setSampleSize(e.target.value)}
                  >
                    <MenuItem value={10}>10 decks</MenuItem>
                    <MenuItem value={50}>50 decks</MenuItem>
                    <MenuItem value={100}>100 decks</MenuItem>
                    <MenuItem value="all">All available decks</MenuItem>
                  </Select>
                </FormControl>
              </Box>

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
                
                {/* Always show cached decks count */}
                <Box sx={{ mt: 2, mb: 2 }}>
                  {loadingCachedCount ? (
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <CircularProgress size={14} />
                      <Typography variant="body2" color="text.secondary">
                        Checking cached decks...
                      </Typography>
                    </Box>
                  ) : (
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Typography variant="body2" color="text.secondary">
                        📊 {cachedDecksCount} decks have cached visual analysis
                      </Typography>
                      <Button
                        variant="outlined"
                        size="small"
                        onClick={clearAnalysisCache}
                        disabled={clearingCache}
                        startIcon={clearingCache ? <CircularProgress size={16} /> : <Clear />}
                        color="error"
                      >
                        {clearingCache ? 'Clearing...' : 'Clear Cache'}
                      </Button>
                    </Box>
                  )}
                </Box>
                
                {selectFromCached && (
                  <Box sx={{ ml: 4, mt: 1 }}>
                    <Typography variant="caption" color="text.secondary">
                      ✓ Sample will prioritize cached decks for faster processing
                    </Typography>
                  </Box>
                )}
              </Box>

              <Box sx={{ display: 'flex', gap: 2 }}>
                <Button
                  variant="contained"
                  onClick={createExtractionSample}
                  disabled={files.length === 0}
                >
                  Create Sample ({sampleSize === 'all' ? files.length : Math.min(sampleSize, files.length)} decks)
                </Button>
                
                {extractionSample.length > 0 && (
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                    Sample created: {extractionSample.length} decks selected
                  </Typography>
                )}
              </Box>
            </Paper>

            {/* Step 2: Visual Analysis */}
            <Paper sx={{ p: 3, mb: 3, bgcolor: 'grey.50' }}>
              <Typography variant="h6" gutterBottom>
                Step 2: Visual Analysis Manager
              </Typography>
              
              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <FormControl fullWidth sx={{ mb: 2 }}>
                    <InputLabel>Vision Model</InputLabel>
                    <Select
                      value={selectedVisionModel}
                      onChange={(e) => setSelectedVisionModel(e.target.value)}
                      label="Vision Model"
                      disabled={extractionSample.length === 0 || modelsLoading || gpuStatus === 'error'}
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
                          {t('models.noModelsAvailable')}
                        </MenuItem>
                      )}
                    </Select>
                  </FormControl>
                  
                </Grid>
                <Grid item xs={12} md={6}>
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                    <Button 
                      variant="contained"
                      onClick={runVisualAnalysisBatch}
                      disabled={extractionSample.length === 0 || !selectedVisionModel || visualAnalysisStatus === 'running'}
                      startIcon={visualAnalysisStatus === 'running' ? <CircularProgress size={16} /> : <Assessment />}
                    >
                      {visualAnalysisStatus === 'running' ? 'Analyzing...' : 'Run Visual Analysis'}
                    </Button>
                    
                    <Box sx={{ display: 'flex', gap: 1 }}>
                      <Button 
                        variant="outlined" 
                        color="error"
                        size="small"
                        onClick={stopCurrentAnalysis}
                        disabled={visualAnalysisStatus !== 'running'}
                        startIcon={<Stop />}
                      >
                        Stop
                      </Button>
                    </Box>
                    
                  </Box>
                </Grid>
              </Grid>
            </Paper>
            
            {/* Step 3: Run Obligatory Extractions */}
            <Paper sx={{ p: 3, mb: 3, bgcolor: 'grey.50' }}>
              <Typography variant="h6" gutterBottom>
                Step 3: Run Obligatory Extractions
              </Typography>
              
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                Run the complete extraction pipeline including company offering extraction, classification, company name extraction, funding amount extraction, and deck date extraction.
              </Typography>
              
              <Grid container spacing={2}>
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
                  
                </Grid>
                <Grid item xs={12} md={6}>
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                    <Button 
                      variant="contained" 
                      color="secondary"
                      onClick={runCompleteExtractionPipeline}
                      disabled={!isVisualAnalysisCompleted() || !selectedTextModel || step3Progress.status === 'processing'}
                      startIcon={step3Progress.status === 'processing' ? <CircularProgress size={16} /> : <DataUsage />}
                    >
                      {step3Progress.status === 'processing' ? 'Processing...' : 'Run Complete Extraction Pipeline'}
                    </Button>

                    {step3Progress.status === 'processing' && (
                      <Button 
                        variant="outlined" 
                        color="error"
                        size="small"
                        onClick={stopStep3Pipeline}
                        startIcon={<Stop />}
                      >
                        Stop
                      </Button>
                    )}

                    {/* Run after step 2 checkbox for Step 3 */}
                    <FormControlLabel
                      control={
                        <Checkbox
                          checked={runStep3AfterStep2}
                          onChange={(e) => setRunStep3AfterStep2(e.target.checked)}
                          disabled={!selectedTextModel}
                        />
                      }
                      label="Run after Step 2 is completed"
                    />
                    
                  </Box>
                </Grid>
              </Grid>
            </Paper>
            
            {/* Step 4: Template-Based Processing (greyed out until step 3 is complete) */}
            <Paper sx={{ p: 3, mb: 3, bgcolor: 'grey.50', opacity: 1 }}> {/* Always enabled for full pipeline configuration */}
              <Typography variant="h6" gutterBottom>
                Step 4: Template-Based Processing
              </Typography>
              
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                Process selected decks through the full template-based analysis pipeline to generate complete results files and extract slide images for thumbnails.
              </Typography>
              
              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <FormControl fullWidth sx={{ mb: 2 }}>
                    <InputLabel>Healthcare Template</InputLabel>
                    <Select
                      value={selectedTemplate || ''}
                      onChange={(e) => setSelectedTemplate(e.target.value)}
                      label="Healthcare Template"
                      disabled={false} // Temporarily enabled for full pipeline configuration
                    >
                      {templatesLoading ? (
                        <MenuItem disabled>
                          <CircularProgress size={16} sx={{ mr: 1 }} />
                          Loading templates...
                        </MenuItem>
                      ) : availableTemplates.length > 0 ? (
                        availableTemplates.map((template) => (
                          <MenuItem key={template.id} value={template.id}>
                            {template.name} {template.sector_name && `(${template.sector_name})`}
                          </MenuItem>
                        ))
                      ) : (
                        <MenuItem disabled>No templates available</MenuItem>
                      )}
                    </Select>
                  </FormControl>
                </Grid>
                <Grid item xs={12} md={6}>
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                    <Button
                      variant="contained"
                      onClick={runTemplateProcessing}
                      disabled={!selectedTemplate || step4Progress.status === 'processing'} // Use backend progress status
                      startIcon={step4Progress.status === 'processing' ? <CircularProgress size={16} /> : <Assessment />}
                      fullWidth
                      sx={{ height: 56 }}
                    >
                      {step4Progress.status === 'processing' ? 'Processing...' : 'Run Template Processing'}
                    </Button>

                    {step4Progress.status === 'processing' && (
                      <Button 
                        variant="outlined" 
                        color="error"
                        size="small"
                        onClick={stopStep4Processing}
                        startIcon={<Stop />}
                        fullWidth
                      >
                        Stop
                      </Button>
                    )}

                    {/* Run after step 3 checkbox for Step 4 */}
                    <FormControlLabel
                      control={
                        <Checkbox
                          checked={runStep4AfterStep3}
                          onChange={(e) => setRunStep4AfterStep3(e.target.checked)}
                          disabled={!selectedTemplate} // Enabled when template is selected
                        />
                      }
                      label="Run after Step 3 is completed"
                    />
                  </Box>
                </Grid>
              </Grid>
            </Paper>
          </Box>
        )}

        {/* Tab Panel 1: Extraction Experiments History */}
        {currentTab === 1 && (
          <Box sx={{ mt: 3 }}>
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
                  No extraction experiments run yet. Complete the steps in the Extraction Testing Lab to create your first experiment.
                </Typography>
              ) : (
                <TableContainer>
                  <Table>
                    <TableHead>
                      <TableRow>
                        {comparisonMode && <TableCell padding="checkbox"></TableCell>}
                        <TableCell>Experiment Name</TableCell>
                        <TableCell>Text Model</TableCell>
                        <TableCell>Obligatory Extractions</TableCell>
                        <TableCell>Templates Processed</TableCell>
                        <TableCell>Created</TableCell>
                        <TableCell>Actions</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {experiments.map((experiment) => (
                        <TableRow key={experiment.id}>
                          {comparisonMode && (
                            <TableCell padding="checkbox">
                              <Checkbox
                                checked={selectedExperiments.includes(experiment.id)}
                                onChange={(e) => {
                                  if (e.target.checked) {
                                    setSelectedExperiments([...selectedExperiments, experiment.id]);
                                  } else {
                                    setSelectedExperiments(selectedExperiments.filter(id => id !== experiment.id));
                                  }
                                }}
                              />
                            </TableCell>
                          )}
                          <TableCell>
                            <Typography variant="body2" fontWeight="medium">
                              {experiment.experiment_name}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Chip label={experiment.text_model_used} size="small" variant="outlined" />
                          </TableCell>
                          <TableCell>
                            <Chip 
                              label={(() => {
                                // Check completion timestamps and results data
                                const resultsData = experiment.results_json ? JSON.parse(experiment.results_json) : {};
                                const hasOfferingExtraction = !!(resultsData.successful_extractions > 0);
                                const hasCompanyNameExtraction = !!(experiment.company_name_completed_at);
                                const hasFundingAmountExtraction = !!(experiment.funding_amount_completed_at);
                                
                                
                                return (hasOfferingExtraction && hasCompanyNameExtraction && hasFundingAmountExtraction) ? 'Yes' : 'No';
                              })()}
                              color={(() => {
                                const resultsData = experiment.results_json ? JSON.parse(experiment.results_json) : {};
                                const hasOfferingExtraction = !!(resultsData.successful_extractions > 0);
                                const hasCompanyNameExtraction = !!(experiment.company_name_completed_at);
                                const hasFundingAmountExtraction = !!(experiment.funding_amount_completed_at);
                                
                                return (hasOfferingExtraction && hasCompanyNameExtraction && hasFundingAmountExtraction) ? 'success' : 'default';
                              })()}
                              size="small"
                              variant="outlined"
                            />
                          </TableCell>
                          <TableCell>
                            <Chip 
                              label={experiment.classification_enabled && experiment.classification_completed_at ? 'Yes' : 'No'}
                              color={experiment.classification_enabled && experiment.classification_completed_at ? 'success' : 'default'}
                              size="small"
                              variant="outlined"
                            />
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2">
                              {new Date(experiment.created_at).toLocaleDateString()}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Box sx={{ display: 'flex', gap: 1 }}>
                              <Button
                                size="small"
                                variant="outlined"
                                onClick={() => viewExperimentDetails(experiment)}
                              >
                                View Details
                              </Button>
                              <Button
                                size="small"
                                variant="contained"
                                color="primary"
                                onClick={() => getSampleFromExperiment(experiment)}
                              >
                                Get Sample
                              </Button>
                            </Box>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </Paper>
          </Box>
        )}

        {/* Tab Panel 2: Training Files */}
        {currentTab === 2 && (
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
        
        {/* Tab Panel 3: Data Management */}
        {currentTab === 3 && (
          <Box sx={{ mt: 3 }}>
            <Typography variant="h6" gutterBottom>
              Data Management
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              Manage test data and dojo projects. Clean up operations preserve all experimental data.
            </Typography>
            
            {/* Test Data Statistics */}
            {testDataStats && (
              <Paper sx={{ p: 3, mb: 3 }}>
                <Typography variant="h6" gutterBottom>
                  Current Test Data Statistics
                </Typography>
                <Grid container spacing={3}>
                  <Grid item xs={12} sm={6} md={3}>
                    <Card>
                      <CardContent sx={{ textAlign: 'center' }}>
                        <Typography variant="h4" color="primary">
                          {testDataStats.total_test_projects}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Total Test Projects
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                  <Grid item xs={12} sm={6} md={3}>
                    <Card>
                      <CardContent sx={{ textAlign: 'center' }}>
                        <Typography variant="h4" color="info.main">
                          {testDataStats.dojo_projects}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Dojo Projects
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                  <Grid item xs={12} sm={6} md={3}>
                    <Card>
                      <CardContent sx={{ textAlign: 'center' }}>
                        <Typography variant="h4" color="secondary.main">
                          {testDataStats.total_test_companies}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Test Companies
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                  <Grid item xs={12} sm={6} md={3}>
                    <Card>
                      <CardContent sx={{ textAlign: 'center' }}>
                        <Typography variant="h4" color="success.main">
                          {testDataStats.total_test_documents}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Test Documents
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                </Grid>
              </Paper>
            )}
            
            {/* Cleanup Operations */}
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Cleanup Operations
              </Typography>
              
              <Alert severity="info" sx={{ mb: 3 }}>
                <Typography variant="body2">
                  <strong>Safety Notice:</strong> These cleanup operations only remove projects and project documents created from experiments. 
                  All experimental data (experiments, PDFs, results files) are preserved and you can regenerate projects 
                  by running "Add Dojo Companies" again on any experiment.
                </Typography>
              </Alert>
              
              <Box sx={{ display: 'flex', gap: 2, flexDirection: 'column' }}>
                <Box>
                  <Typography variant="subtitle1" gutterBottom>
                    Clean Up Dojo Projects
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    Remove all dojo-created projects and their associated documents from the projects database. 
                    This will clean up the Gallery view while preserving all experimental data for future re-creation.
                  </Typography>
                  <Button
                    variant="contained"
                    color="warning"
                    onClick={() => setCleanupDialogOpen(true)}
                    disabled={cleanupLoading}
                    startIcon={cleanupLoading ? <CircularProgress size={16} /> : <Clear />}
                  >
                    {cleanupLoading ? 'Cleaning...' : 'Clean Up Dojo Projects'}
                  </Button>
                </Box>
              </Box>
            </Paper>
          </Box>
        )}
      </Paper>
      
      {/* Cleanup Confirmation Dialog */}
      <Dialog
        open={cleanupDialogOpen}
        onClose={() => !cleanupLoading && setCleanupDialogOpen(false)}
      >
        <DialogTitle>Clean Up Dojo Projects</DialogTitle>
        <DialogContent>
          <Typography sx={{ mb: 2 }}>
            Are you sure you want to clean up all dojo projects? This will:
          </Typography>
          <Box component="ul" sx={{ pl: 2 }}>
            <Typography component="li" variant="body2">
              Remove all projects created from dojo experiments ({testDataStats?.dojo_projects || 0} projects)
            </Typography>
            <Typography component="li" variant="body2">
              Remove associated project documents
            </Typography>
            <Typography component="li" variant="body2" color="success.main">
              <strong>Preserve</strong> all experimental data (experiments, PDFs, results files)
            </Typography>
            <Typography component="li" variant="body2" color="success.main">
              <strong>Allow</strong> re-creation of projects from existing experiments
            </Typography>
          </Box>
          <Alert severity="warning" sx={{ mt: 2 }}>
            This action cannot be undone, but projects can be recreated from experiments.
          </Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCleanupDialogOpen(false)} disabled={cleanupLoading}>
            Cancel
          </Button>
          <Button
            onClick={cleanupDojoProjects}
            color="warning"
            variant="contained"
            disabled={cleanupLoading}
            startIcon={cleanupLoading ? <CircularProgress size={16} /> : null}
          >
            {cleanupLoading ? 'Cleaning...' : 'Clean Up Projects'}
          </Button>
        </DialogActions>
      </Dialog>
      
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
                                {(() => {
                                  // Get funding amount for this deck
                                  const fundingAmountResult = experimentDetails.funding_amount_results?.find(
                                    fa => fa.deck_id === result.deck_id
                                  );
                                  return fundingAmountResult?.funding_amount && (
                                    <Typography variant="caption" color="text.secondary">
                                      Funding: {fundingAmountResult.funding_amount}
                                    </Typography>
                                  );
                                })()}
                                {(() => {
                                  // Get deck date for this deck
                                  const deckDateResult = experimentDetails.deck_date_results?.find(
                                    dd => dd.deck_id === result.deck_id
                                  );
                                  return deckDateResult?.deck_date && deckDateResult.deck_date !== 'Date not specified' && (
                                    <Typography variant="caption" color="text.secondary">
                                      Deck Date: {deckDateResult.deck_date}
                                    </Typography>
                                  );
                                })()}
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
        <DialogActions sx={{ flexDirection: 'column', gap: 2, alignItems: 'stretch' }}>
          {/* Missing extractions panel */}
          {experimentDetails && (
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', width: '100%' }}>
              {!experimentDetails.classification_enabled && (
                <Button
                  size="small"
                  variant="outlined"
                  color="primary"
                  onClick={() => runClassificationEnrichment(experimentDetails.id)}
                  sx={{ minWidth: 120 }}
                >
                  Run Classification
                </Button>
              )}
              {!experimentDetails.funding_amount_completed_at && (
                <Button
                  size="small"
                  variant="outlined"
                  color="primary"
                  onClick={() => runFundingAmountExtraction(experimentDetails.id)}
                  sx={{ minWidth: 120 }}
                >
                  Run Funding Extraction
                </Button>
              )}
              {!experimentDetails.company_name_completed_at && (
                <Button
                  size="small"
                  variant="outlined"
                  color="primary"
                  onClick={() => runCompanyNameExtraction(experimentDetails.id)}
                  sx={{ minWidth: 120 }}
                >
                  Run Company Names
                </Button>
              )}
            </Box>
          )}
          
          {/* Main action buttons */}
          <Box sx={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
            <Button onClick={() => setExperimentDetailsOpen(false)}>
              Close
            </Button>
            <Button 
              variant="contained" 
              disabled={!canAddDojoCompanies(experimentDetails)}
              onClick={addDojoCompanies}
            >
              Add Dojo Companies
            </Button>
          </Box>
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