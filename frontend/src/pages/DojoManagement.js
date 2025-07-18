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
  
  const [files, setFiles] = useState([]);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [selectedFile, setSelectedFile] = useState(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [fileToDelete, setFileToDelete] = useState(null);

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

      const user = JSON.parse(localStorage.getItem('user'));
      const token = user?.token;

      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('/api/dojo/upload', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Upload failed');
      }

      const result = await response.json();
      setUploadProgress(100);

      // Reload data after successful upload
      setTimeout(() => {
        loadDojoData();
        setUploading(false);
        setUploadProgress(0);
      }, 1000);

    } catch (err) {
      console.error('Error uploading file:', err);
      setError(err.message || 'Failed to upload file');
      setUploading(false);
      setUploadProgress(0);
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
            <LinearProgress variant="determinate" value={uploadProgress} />
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              Uploading and processing... {uploadProgress}%
            </Typography>
          </Box>
        ) : (
          <Button
            variant="contained"
            component="label"
            startIcon={<CloudUpload />}
            disabled={uploading}
          >
            Select ZIP File
            <input
              type="file"
              hidden
              accept=".zip"
              onChange={handleFileUpload}
            />
          </Button>
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