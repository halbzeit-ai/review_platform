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
  Close as CloseIcon
} from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import { getProjectUploads, uploadPitchDeck, deleteDeck } from '../services/api';

const ProjectUploads = ({ projectId, onUploadComplete }) => {
  const { t } = useTranslation();
  const [uploads, setUploads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedUpload, setSelectedUpload] = useState(null);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [deleting, setDeleting] = useState(null);

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


  const handleViewDetails = (upload) => {
    setSelectedUpload(upload);
    setDetailsOpen(true);
  };

  const handleCloseDetails = () => {
    setDetailsOpen(false);
    setSelectedUpload(null);
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
      // TODO: Update delete endpoint to use project ID
      // await deleteDeck(projectId, upload.id);
      throw new Error('Delete functionality temporarily disabled during project ID migration');
      setUploadStatus({ 
        type: 'success', 
        message: `"${upload.filename}" deleted successfully!` 
      });
      
      // Refresh the uploads list
      loadUploads(projectId);
      
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
              {formatFileSize(upload.file_size)} • {upload.pages ? `${upload.pages} pages` : (upload.processing_status === 'completed' ? 'Analyzed' : 'Processing...')} • {new Date(upload.upload_date).toLocaleString('en-US', { 
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
                  primary="File Path"
                  secondary={selectedUpload.file_path}
                />
              </ListItem>
            </List>
          </Box>
        )}
      </DialogContent>
      
      <DialogActions>
        <Button onClick={handleCloseDetails}>
          Close
        </Button>
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