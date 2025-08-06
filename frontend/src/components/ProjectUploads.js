import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Button,
  Alert,
  CircularProgress,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  IconButton,
} from '@mui/material';
import {
  Upload as UploadIcon,
  Delete as DeleteIcon,
  PictureAsPdf as PdfIcon,
  Info as InfoIcon,
} from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import { getProjectUploads, uploadPitchDeck, deleteDeck } from '../services/api';

const ProjectUploads = ({ companyId, onUploadComplete }) => {
  const { t } = useTranslation();
  const [uploads, setUploads] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [deleting, setDeleting] = useState(null);

  // Simple effect - no complex logic, no refs, no callbacks
  useEffect(() => {
    console.log('ProjectUploads useEffect triggered - companyId:', companyId);
    const loadData = async () => {
      if (!companyId) return;
      
      console.log('ProjectUploads loading data for companyId:', companyId);
      setLoading(true);
      setError(null);
      
      try {
        const response = await getProjectUploads(companyId);
        const data = response.data || response;
        setUploads(data.uploads || []);
        console.log('ProjectUploads data loaded successfully');
      } catch (err) {
        setError(err.response?.data?.detail || 'Failed to load uploads');
        console.log('ProjectUploads data loading failed:', err);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [companyId]); // Only companyId dependency

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    // File validation
    if (file.size > 50 * 1024 * 1024) {
      setUploadStatus({ type: 'error', message: 'File too large. Max 50MB.' });
      event.target.value = '';
      return;
    }

    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setUploadStatus({ type: 'error', message: 'Only PDF files allowed.' });
      event.target.value = '';
      return;
    }

    setUploading(true);
    setUploadStatus(null);

    try {
      await uploadPitchDeck(file);
      setUploadStatus({ type: 'success', message: 'Upload successful!' });
      
      // Reload uploads
      const response = await getProjectUploads(companyId);
      const data = response.data || response;
      setUploads(data.uploads || []);
      
      if (onUploadComplete) onUploadComplete();
      event.target.value = '';
    } catch (error) {
      setUploadStatus({ 
        type: 'error', 
        message: error.response?.data?.detail || 'Upload failed' 
      });
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (deckId) => {
    setDeleting(deckId);
    try {
      await deleteDeck(deckId);
      setUploads(prev => prev.filter(u => u.id !== deckId));
    } catch (error) {
      setError(error.response?.data?.detail || 'Delete failed');
    } finally {
      setDeleting(null);
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Upload Pitch Deck
        </Typography>
        
        <input
          accept=".pdf"
          style={{ display: 'none' }}
          id="upload-file"
          type="file"
          onChange={handleFileUpload}
          disabled={uploading}
        />
        <label htmlFor="upload-file">
          <Button
            variant="contained"
            component="span"
            startIcon={uploading ? <CircularProgress size={20} /> : <UploadIcon />}
            disabled={uploading}
            sx={{ mb: 2 }}
          >
            {uploading ? 'Uploading...' : 'Choose PDF File'}
          </Button>
        </label>

        {uploadStatus && (
          <Alert severity={uploadStatus.type} sx={{ mt: 2 }}>
            {uploadStatus.message}
          </Alert>
        )}
      </Paper>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          Uploaded Files ({uploads.length})
        </Typography>

        {uploads.length === 0 ? (
          <Typography color="text.secondary">
            No files uploaded yet.
          </Typography>
        ) : (
          <List>
            {uploads.map((upload) => (
              <ListItem key={upload.id}>
                <ListItemIcon>
                  <PdfIcon />
                </ListItemIcon>
                <ListItemText
                  primary={upload.filename}
                  secondary={`Status: ${upload.processing_status || 'Unknown'}`}
                />
                <IconButton
                  onClick={() => handleDelete(upload.id)}
                  disabled={deleting === upload.id}
                  color="error"
                >
                  {deleting === upload.id ? <CircularProgress size={20} /> : <DeleteIcon />}
                </IconButton>
              </ListItem>
            ))}
          </List>
        )}
      </Paper>
    </Box>
  );
};

export default ProjectUploads;