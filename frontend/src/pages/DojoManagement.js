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
  ListItemSecondaryAction
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
  DataUsage
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
    if (uploadSpeed === 0 || bytesUploaded === 0 || uploadSpeed < 1000) return ''; // Ignore very slow speeds
    
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

  useEffect(() => {
    loadDojoData();
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
          
          // Calculate upload speed (only after meaningful elapsed time to avoid inflated speeds)
          const currentTime = Date.now();
          const elapsedTime = (currentTime - uploadStartTime) / 1000; // in seconds
          if (elapsedTime > 2 && event.loaded > 0) { // Wait at least 2 seconds for stable measurement
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

      // Set dynamic timeout based on file size
      // Calculate timeout: minimum 10 minutes, plus 1 minute per 50MB
      const baseTimeout = 10 * 60 * 1000; // 10 minutes base
      const fileSizeTimeout = Math.ceil(file.size / (50 * 1024 * 1024)) * 60 * 1000; // 1 minute per 50MB
      xhr.timeout = Math.max(baseTimeout, fileSizeTimeout);

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

      {/* Files Table */}
      <Paper sx={{ p: 3 }}>
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
    </Box>
  );
};

export default DojoManagement;