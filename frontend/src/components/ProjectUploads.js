import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Box,
  Typography,
  Paper,
  Button,
  Alert,
  CircularProgress,
  Chip,
  Divider,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemSecondaryAction
} from '@mui/material';
import {
  Upload as UploadIcon,
  Delete as DeleteIcon,
  PictureAsPdf as PdfIcon,
  Visibility as VisibilityIcon,
  Info as InfoIcon,
  Close as CloseIcon,
  Error as ErrorIcon,
  Refresh as RefreshIcon,
  Warning as WarningIcon
} from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import { 
  getProjectUploads, 
  uploadPitchDeck, 
  deleteDeck, 
  getDocumentFailureDetails, 
  retryFailedDocument 
} from '../services/api';

const ProjectUploads = ({ projectId, onUploadComplete, onDeleteComplete }) => {
  const { t } = useTranslation();
  const [uploads, setUploads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedUpload, setSelectedUpload] = useState(null);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [deleting, setDeleting] = useState(null);
  const [failureDetails, setFailureDetails] = useState(null);
  const [retrying, setRetrying] = useState(null);

  // Track previous projectId to prevent unnecessary reloads
  const prevProjectIdRef = useRef();
  
  const loadUploads = useCallback(async (currentProjectId) => {
    if (!currentProjectId) return;
    
    try {
      console.log('ProjectUploads - loadUploads called with projectId:', currentProjectId);
      setLoading(true);
      setError(null);
      
      console.log('ProjectUploads - about to call getProjectUploads API...');
      const response = await getProjectUploads(currentProjectId);
      console.log('ProjectUploads - API response:', response);
      const uploadsData = response.data || response;
      console.log('ProjectUploads - processed uploadsData:', uploadsData);
      
      setUploads(uploadsData.uploads || []);
    } catch (err) {
      console.error('Error loading uploads:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to load uploads');
    } finally {
      setLoading(false);
    }
  }, []); // Empty dependency array to prevent recreating the function
  
  useEffect(() => {
    console.log('ProjectUploads - projectId prop:', projectId, 'prev:', prevProjectIdRef.current);
    // Only load if projectId actually changed
    if (projectId && projectId !== prevProjectIdRef.current) {
      console.log('ProjectUploads - projectId actually changed, calling loadUploads');
      prevProjectIdRef.current = projectId;
      loadUploads(projectId); // Pass projectId as parameter instead of using closure
    } else if (!projectId) {
      console.log('ProjectUploads - no projectId provided, not loading uploads');
    } else {
      console.log('ProjectUploads - projectId unchanged, skipping reload');
    }
  }, [projectId, loadUploads]);


  const handleViewDetails = async (upload) => {
    setSelectedUpload(upload);
    setFailureDetails(null);
    
    // Get failure details for any document that might have failed tasks
    // This includes 'failed', 'error', and 'extraction_complete' (partial failures)
    if (upload.processing_status === 'failed' || upload.processing_status === 'error' || upload.processing_status === 'extraction_complete') {
      try {
        const response = await getDocumentFailureDetails(upload.id);
        setFailureDetails(response.data);
      } catch (error) {
        console.error('Error loading failure details:', error);
      }
    }
    
    setDetailsOpen(true);
  };

  const handleRetryUpload = async (uploadId) => {
    setRetrying(uploadId);
    try {
      await retryFailedDocument(uploadId);
      setUploadStatus({
        type: 'success',
        message: 'Document queued for retry processing'
      });
      // Reload uploads to show updated status
      loadUploads(projectId);
      setDetailsOpen(false);
    } catch (error) {
      setUploadStatus({
        type: 'error',
        message: error.response?.data?.detail || 'Failed to retry document'
      });
    } finally {
      setRetrying(null);
    }
  };

  const handleCloseDetails = () => {
    setDetailsOpen(false);
    setSelectedUpload(null);
    setFailureDetails(null);
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    // Check file size (50MB limit)
    const maxSize = 50 * 1024 * 1024; // 50MB in bytes
    if (file.size > maxSize) {
      setUploadStatus({ 
        type: 'error', 
        message: `File too large. Maximum size is 50MB. Your file is ${(file.size / (1024 * 1024)).toFixed(1)}MB.` 
      });
      event.target.value = '';
      return;
    }

    // Check file type
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setUploadStatus({ 
        type: 'error', 
        message: 'Only PDF files are allowed.' 
      });
      event.target.value = '';
      return;
    }

    setUploading(true);
    setUploadStatus(null);

    try {
      const response = await uploadPitchDeck(file);
      setUploadStatus({ 
        type: 'success', 
        message: 'File uploaded successfully!' 
      });
      
      // Refresh the uploads list
      loadUploads(projectId);
      
      // Call callback if provided
      if (onUploadComplete) {
        onUploadComplete(response.data);
      }
      
    } catch (error) {
      let errorMessage = 'Upload failed. Please try again.';
      
      // Handle specific error cases
      if (error.response?.status === 413) {
        errorMessage = 'File too large. Maximum size is 50MB.';
      } else if (error.response?.status === 400) {
        errorMessage = error.response.data?.detail || 'Invalid file type.';
      } else if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      }
      
      setUploadStatus({ 
        type: 'error', 
        message: errorMessage
      });
    } finally {
      setUploading(false);
      // Reset file input
      event.target.value = '';
    }
  };

  const handleDeleteUpload = async (upload) => {
    if (!window.confirm(`Are you sure you want to delete "${upload.filename}"? This action cannot be undone.`)) {
      return;
    }

    setDeleting(upload.id);
    setUploadStatus(null);

    try {
      // Delete the deck using the backend API
      await deleteDeck(projectId, upload.id);
      setUploadStatus({ 
        type: 'success', 
        message: `"${upload.filename}" deleted successfully!` 
      });
      
      // Refresh the uploads list
      loadUploads(projectId);
      
      // Trigger parent component refresh to update deck cards in all tabs
      if (onDeleteComplete) {
        onDeleteComplete();
      }
      
    } catch (error) {
      let errorMessage = 'Delete failed. Please try again.';
      
      if (error.response?.status === 403) {
        errorMessage = 'You don\'t have permission to delete this file.';
      } else if (error.response?.status === 404) {
        errorMessage = 'File not found or already deleted.';
      } else if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      }
      
      setUploadStatus({ 
        type: 'error', 
        message: errorMessage
      });
    } finally {
      setDeleting(null);
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getStatusDisplay = (upload) => {
    switch (upload.processing_status) {
      case 'completed':
        return upload.pages ? `${upload.pages} pages` : 'Analyzed';
      case 'processing':
      case 'queued':
        return 'Processing...';
      case 'failed':
      case 'error':
        return 'Failed - Click for details';
      default:
        return upload.processing_status || 'Unknown status';
    }
  };

  const getFileIcon = (fileType) => {
    switch (fileType.toLowerCase()) {
      case 'pdf':
        return <PdfIcon color="error" />;
      default:
        return <UploadIcon color="action" />;
    }
  };

  const UploadRow = ({ upload }) => (
    <Paper 
      sx={{ 
        p: 2, 
        mb: 1,
        cursor: 'pointer',
        '&:hover': { 
          backgroundColor: 'action.hover'
        }
      }}
      onClick={() => handleViewDetails(upload)}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', flex: 1 }}>
          {getFileIcon(upload.file_type)}
          <Box sx={{ ml: 2, flex: 1 }}>
            <Typography variant="body1" sx={{ fontWeight: 'medium' }}>
              {upload.filename}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {formatFileSize(upload.file_size)} • {getStatusDisplay(upload)} • {new Date(upload.upload_date).toLocaleString('en-US', { 
                year: 'numeric', 
                month: 'short', 
                day: 'numeric', 
                hour: '2-digit', 
                minute: '2-digit',
                hour12: false 
              })}
            </Typography>
          </Box>
        </Box>
        
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {upload.processing_status === 'processing' && (
            <CircularProgress size={20} sx={{ mr: 1 }} />
          )}
          {(upload.processing_status === 'failed' || upload.processing_status === 'error') && (
            <ErrorIcon color="error" sx={{ mr: 1 }} />
          )}
          <IconButton
            size="small"
            onClick={(e) => {
              e.stopPropagation();
              handleViewDetails(upload);
            }}
          >
            <InfoIcon />
          </IconButton>
          <IconButton
            size="small"
            onClick={(e) => {
              e.stopPropagation();
              handleDeleteUpload(upload);
            }}
            disabled={deleting === upload.id}
            color="error"
          >
            {deleting === upload.id ? <CircularProgress size={20} /> : <DeleteIcon />}
          </IconButton>
        </Box>
      </Box>
    </Paper>
  );

  const DetailsDialog = () => (
    <Dialog open={detailsOpen} onClose={handleCloseDetails} maxWidth="md" fullWidth>
      <DialogTitle>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Typography variant="h6">
            File Details
          </Typography>
          <IconButton onClick={handleCloseDetails}>
            <CloseIcon />
          </IconButton>
        </Box>
      </DialogTitle>
      
      <DialogContent>
        {selectedUpload && (
          <Box>
            <List>
              <ListItem>
                <ListItemIcon>
                  {getFileIcon(selectedUpload.file_type)}
                </ListItemIcon>
                <ListItemText
                  primary="Filename"
                  secondary={selectedUpload.filename}
                />
              </ListItem>
              
              <ListItem>
                <ListItemIcon>
                  <InfoIcon />
                </ListItemIcon>
                <ListItemText
                  primary="File Size"
                  secondary={formatFileSize(selectedUpload.file_size)}
                />
              </ListItem>
              
              <ListItem>
                <ListItemIcon>
                  <UploadIcon />
                </ListItemIcon>
                <ListItemText
                  primary="Upload Date"
                  secondary={new Date(selectedUpload.upload_date).toLocaleString('en-US', { 
                    year: 'numeric', 
                    month: 'short', 
                    day: 'numeric', 
                    hour: '2-digit', 
                    minute: '2-digit',
                    second: '2-digit',
                    hour12: false 
                  })}
                />
              </ListItem>
              
              <ListItem>
                <ListItemIcon>
                  <PdfIcon />
                </ListItemIcon>
                <ListItemText
                  primary="File Type"
                  secondary={selectedUpload.file_type.toUpperCase()}
                />
              </ListItem>
              
              <ListItem>
                <ListItemIcon>
                  <InfoIcon />
                </ListItemIcon>
                <ListItemText
                  primary="Processing Status"
                  secondary={
                    <Chip 
                      label={getStatusDisplay(selectedUpload)} 
                      color={
                        selectedUpload.processing_status === 'completed' ? 'success' :
                        selectedUpload.processing_status === 'processing' ? 'info' :
                        (selectedUpload.processing_status === 'failed' || selectedUpload.processing_status === 'error') ? 'error' :
                        'default'
                      }
                      size="small"
                    />
                  }
                />
              </ListItem>
              
              <ListItem>
                <ListItemIcon>
                  <InfoIcon />
                </ListItemIcon>
                <ListItemText
                  primary="File Path"
                  secondary={selectedUpload.file_path}
                />
              </ListItem>
            </List>

            {/* Failure Details Section */}
            {failureDetails && (
              <>
                <Divider sx={{ my: 2 }} />
                <Typography variant="h6" color="error" sx={{ mb: 2, display: 'flex', alignItems: 'center' }}>
                  <ErrorIcon sx={{ mr: 1 }} />
                  Processing Failure Details
                </Typography>
                
                <Alert severity="error" sx={{ mb: 2 }}>
                  <Typography variant="body2" sx={{ fontWeight: 'medium' }}>
                    {failureDetails.failure_summary || 'Processing failed'}
                  </Typography>
                </Alert>

                {failureDetails.failed_tasks && failureDetails.failed_tasks.length > 0 && (
                  <>
                    <Typography variant="subtitle2" sx={{ mb: 1 }}>
                      Failed Processing Steps:
                    </Typography>
                    <List dense>
                      {failureDetails.failed_tasks.map((task, index) => (
                        <ListItem key={index} sx={{ pl: 0 }}>
                          <ListItemIcon>
                            <WarningIcon color="warning" />
                          </ListItemIcon>
                          <ListItemText
                            primary={`Step: ${task.task_type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}`}
                            secondary={
                              <Box>
                                <Typography variant="body2" color="error">
                                  Error: {task.error_message}
                                </Typography>
                                {task.failed_at && (
                                  <Typography variant="caption" color="text.secondary">
                                    Failed at: {new Date(task.failed_at).toLocaleString()}
                                  </Typography>
                                )}
                              </Box>
                            }
                          />
                        </ListItem>
                      ))}
                    </List>
                  </>
                )}
              </>
            )}
          </Box>
        )}
      </DialogContent>
      
      <DialogActions>
        <Button onClick={handleCloseDetails}>
          Close
        </Button>
        
        {/* Retry Button for Failed Documents */}
        {failureDetails && failureDetails.can_retry && (
          <Button 
            variant="contained" 
            color="warning"
            startIcon={retrying === selectedUpload?.id ? <CircularProgress size={20} /> : <RefreshIcon />}
            onClick={() => handleRetryUpload(selectedUpload.id)}
            disabled={retrying === selectedUpload?.id}
            sx={{ mr: 1 }}
          >
            {retrying === selectedUpload?.id ? 'Retrying...' : 'Retry Processing'}
          </Button>
        )}
        
        <Button 
          variant="contained" 
          color="error"
          startIcon={deleting === selectedUpload?.id ? <CircularProgress size={20} /> : <DeleteIcon />}
          onClick={() => {
            handleDeleteUpload(selectedUpload);
            handleCloseDetails();
          }}
          disabled={deleting === selectedUpload?.id}
        >
          {deleting === selectedUpload?.id ? 'Deleting...' : 'Delete'}
        </Button>
      </DialogActions>
    </Dialog>
  );

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 3 }}>
        {error}
      </Alert>
    );
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h5">
          File Uploads
        </Typography>
        <Box>
          <input
            accept="application/pdf"
            style={{ display: 'none' }}
            id="upload-pitch-deck"
            type="file"
            onChange={handleFileUpload}
            disabled={uploading}
          />
          <label htmlFor="upload-pitch-deck">
            <Button 
              variant="outlined" 
              component="span"
              startIcon={uploading ? <CircularProgress size={20} /> : <UploadIcon />}
              disabled={uploading}
            >
              {uploading ? 'Uploading...' : 'Upload New File'}
            </Button>
          </label>
        </Box>
      </Box>
      
      {/* Upload Status */}
      {uploadStatus && (
        <Alert severity={uploadStatus.type} sx={{ mb: 3 }}>
          {uploadStatus.message}
        </Alert>
      )}
      
      {/* Upload Instructions */}
      <Alert severity="info" sx={{ mb: 3 }}>
        <Typography variant="body2">
          <strong>Upload Instructions:</strong> Only PDF files are allowed. Maximum file size: 50MB.
        </Typography>
      </Alert>
      
      <Box>
        {uploads.map((upload, index) => (
          <UploadRow key={index} upload={upload} />
        ))}
      </Box>
      
      {uploads.length === 0 && !loading && (
        <Paper sx={{ p: 4, textAlign: 'center', mt: 3 }}>
          <UploadIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
          <Typography variant="h6" color="text.secondary" gutterBottom>
            No files uploaded
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Upload your first pitch deck to get started with the analysis.
          </Typography>
          <input
            accept="application/pdf"
            style={{ display: 'none' }}
            id="upload-pitch-deck-empty"
            type="file"
            onChange={handleFileUpload}
            disabled={uploading}
          />
          <label htmlFor="upload-pitch-deck-empty">
            <Button 
              variant="contained" 
              component="span"
              startIcon={uploading ? <CircularProgress size={20} /> : <UploadIcon />}
              disabled={uploading}
            >
              {uploading ? 'Uploading...' : 'Upload Pitch Deck'}
            </Button>
          </label>
        </Paper>
      )}
      
      <DetailsDialog />
    </Box>
  );
};

export default ProjectUploads;