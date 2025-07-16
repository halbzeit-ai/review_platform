import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Grid,
  Card,
  CardContent,
  CardActions,
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
  Download as DownloadIcon,
  PictureAsPdf as PdfIcon,
  Visibility as VisibilityIcon,
  Info as InfoIcon,
  Close as CloseIcon
} from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import { getProjectUploads } from '../services/api';

const ProjectUploads = ({ companyId, onUploadComplete }) => {
  const { t } = useTranslation();
  const [uploads, setUploads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedUpload, setSelectedUpload] = useState(null);
  const [detailsOpen, setDetailsOpen] = useState(false);

  useEffect(() => {
    if (companyId) {
      loadUploads();
    }
  }, [companyId]);

  const loadUploads = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await getProjectUploads(companyId);
      const uploadsData = response.data || response;
      
      setUploads(uploadsData.uploads || []);
    } catch (err) {
      console.error('Error loading uploads:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to load uploads');
    } finally {
      setLoading(false);
    }
  };

  const handleViewDetails = (upload) => {
    setSelectedUpload(upload);
    setDetailsOpen(true);
  };

  const handleCloseDetails = () => {
    setDetailsOpen(false);
    setSelectedUpload(null);
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

  const UploadCard = ({ upload }) => (
    <Card 
      sx={{ 
        cursor: 'pointer',
        transition: 'all 0.2s',
        '&:hover': { 
          transform: 'translateY(-2px)',
          boxShadow: 3 
        }
      }}
      onClick={() => handleViewDetails(upload)}
    >
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          {getFileIcon(upload.file_type)}
          <Box sx={{ ml: 2, flex: 1 }}>
            <Typography variant="h6" noWrap>
              {upload.filename}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {formatFileSize(upload.file_size)}
            </Typography>
          </Box>
        </Box>
        
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 2 }}>
          <Chip 
            label={upload.file_type.toUpperCase()} 
            variant="outlined"
            size="small"
          />
          <Chip 
            label={new Date(upload.upload_date).toLocaleDateString()} 
            variant="outlined"
            size="small"
            color="primary"
          />
        </Box>
      </CardContent>
      
      <CardActions>
        <Button
          size="small"
          startIcon={<InfoIcon />}
          onClick={(e) => {
            e.stopPropagation();
            handleViewDetails(upload);
          }}
        >
          Details
        </Button>
        <Button
          size="small"
          startIcon={<DownloadIcon />}
          onClick={(e) => {
            e.stopPropagation();
            // TODO: Implement download functionality
          }}
          disabled
        >
          Download
        </Button>
      </CardActions>
    </Card>
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
                  secondary={new Date(selectedUpload.upload_date).toLocaleString()}
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
          startIcon={<DownloadIcon />}
          onClick={() => {
            // TODO: Implement download functionality
          }}
          disabled
        >
          Download
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
        <Button 
          variant="outlined" 
          startIcon={<UploadIcon />}
          onClick={() => {
            // TODO: Implement upload functionality or navigate to upload page
          }}
        >
          Upload New File
        </Button>
      </Box>
      
      <Grid container spacing={3}>
        {uploads.map((upload, index) => (
          <Grid item xs={12} md={6} lg={4} key={index}>
            <UploadCard upload={upload} />
          </Grid>
        ))}
      </Grid>
      
      {uploads.length === 0 && (
        <Paper sx={{ p: 4, textAlign: 'center', mt: 3 }}>
          <UploadIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
          <Typography variant="h6" color="text.secondary" gutterBottom>
            No files uploaded
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Upload your first pitch deck to get started with the analysis.
          </Typography>
          <Button 
            variant="contained" 
            startIcon={<UploadIcon />}
            onClick={() => {
              // TODO: Implement upload functionality or navigate to upload page
            }}
          >
            Upload Pitch Deck
          </Button>
        </Paper>
      )}
      
      <DetailsDialog />
    </Box>
  );
};

export default ProjectUploads;