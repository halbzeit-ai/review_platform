import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Container,
  Paper,
  Typography,
  Box,
  Grid,
  Card,
  CardContent,
  Button,
  Alert,
  CircularProgress,
  Breadcrumbs,
  Link,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Divider
} from '@mui/material';
import {
  Settings,
  Home,
  Memory,
  Download,
  Delete,
  Add,
  CheckCircle,
  Error,
  Refresh
} from '@mui/icons-material';
import { useTranslation } from 'react-i18next';

const ConfigPage = () => {
  const navigate = useNavigate();
  const { t } = useTranslation('dashboard');
  const [loading, setLoading] = useState(true);
  const [models, setModels] = useState([]);
  const [availableModels, setAvailableModels] = useState([]);
  const [activeModel, setActiveModel] = useState(null);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [pullDialog, setPullDialog] = useState(false);
  const [newModelName, setNewModelName] = useState('');
  const [pulling, setPulling] = useState(false);

  useEffect(() => {
    const user = JSON.parse(localStorage.getItem('user'));
    if (user?.role !== 'gp') {
      navigate('/dashboard/startup');
      return;
    }
    
    fetchModels();
    fetchAvailableModels();
  }, [navigate]);

  const fetchModels = async () => {
    try {
      const user = JSON.parse(localStorage.getItem('user'));
      const token = user?.token;
      
      const response = await fetch('/api/config/models', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to fetch models');
      }

      const data = await response.json();
      setModels(data.models || []);
      setActiveModel(data.active_model);
      setLoading(false);
    } catch (err) {
      setError('Failed to fetch models');
      setLoading(false);
    }
  };

  const fetchAvailableModels = async () => {
    try {
      const user = JSON.parse(localStorage.getItem('user'));
      const token = user?.token;
      
      const response = await fetch('/api/config/available-models', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to fetch available models');
      }

      const data = await response.json();
      setAvailableModels(data.models || []);
    } catch (err) {
      console.error('Failed to fetch available models:', err);
    }
  };

  const handleSetActiveModel = async (modelName) => {
    try {
      const user = JSON.parse(localStorage.getItem('user'));
      const token = user?.token;
      
      const response = await fetch('/api/config/set-active-model', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ model_name: modelName })
      });

      if (!response.ok) {
        throw new Error('Failed to set active model');
      }

      setActiveModel(modelName);
      setSuccess(`Successfully set ${modelName} as active model`);
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError('Failed to set active model');
      setTimeout(() => setError(null), 3000);
    }
  };

  const handlePullModel = async () => {
    if (!newModelName.trim()) return;
    
    setPulling(true);
    try {
      const user = JSON.parse(localStorage.getItem('user'));
      const token = user?.token;
      
      const response = await fetch('/api/config/pull-model', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ model_name: newModelName.trim() })
      });

      if (!response.ok) {
        throw new Error('Failed to pull model');
      }

      setSuccess(`Successfully started pulling ${newModelName}`);
      setPullDialog(false);
      setNewModelName('');
      
      // Refresh models list
      setTimeout(() => {
        fetchModels();
        setSuccess(null);
      }, 3000);
    } catch (err) {
      setError('Failed to pull model');
      setTimeout(() => setError(null), 3000);
    } finally {
      setPulling(false);
    }
  };

  const handleDeleteModel = async (modelName) => {
    if (!window.confirm(`Are you sure you want to delete ${modelName}?`)) return;
    
    try {
      const user = JSON.parse(localStorage.getItem('user'));
      const token = user?.token;
      
      const response = await fetch('/api/config/delete-model', {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ model_name: modelName })
      });

      if (!response.ok) {
        throw new Error('Failed to delete model');
      }

      setSuccess(`Successfully deleted ${modelName}`);
      fetchModels();
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError('Failed to delete model');
      setTimeout(() => setError(null), 3000);
    }
  };

  const formatModelSize = (size) => {
    if (size > 1000000000) return `${(size / 1000000000).toFixed(1)}GB`;
    if (size > 1000000) return `${(size / 1000000).toFixed(1)}MB`;
    return `${size} bytes`;
  };

  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
        <Paper elevation={3} sx={{ p: 4 }}>
          <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px">
            <CircularProgress />
          </Box>
        </Paper>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      {/* Breadcrumbs */}
      <Breadcrumbs aria-label="breadcrumb" sx={{ mb: 3 }}>
        <Link
          underline="hover"
          color="inherit"
          href="#"
          onClick={() => navigate('/dashboard/gp')}
          sx={{ display: 'flex', alignItems: 'center' }}
        >
          <Home sx={{ mr: 0.5 }} fontSize="inherit" />
          Dashboard
        </Link>
        <Typography color="text.primary">Model Configuration</Typography>
      </Breadcrumbs>

      {/* Header */}
      <Paper elevation={3} sx={{ p: 4, mb: 4 }}>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
          <Box>
            <Typography variant="h4" gutterBottom>
              AI Model Configuration
            </Typography>
            <Typography variant="subtitle1" color="text.secondary">
              Manage the AI models used for pitch deck analysis
            </Typography>
          </Box>
          <Settings fontSize="large" color="primary" />
        </Box>

        {/* Status Messages */}
        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}
        {success && (
          <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess(null)}>
            {success}
          </Alert>
        )}

        {/* Active Model */}
        <Card variant="outlined" sx={{ mb: 3, bgcolor: 'success.50' }}>
          <CardContent>
            <Typography variant="h6" gutterBottom color="success.main">
              Active Model
            </Typography>
            <Box display="flex" alignItems="center" gap={2}>
              <CheckCircle color="success" />
              <Typography variant="h6">
                {activeModel || 'No active model set'}
              </Typography>
            </Box>
          </CardContent>
        </Card>

        {/* Actions */}
        <Box display="flex" gap={2} mb={3}>
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={() => setPullDialog(true)}
          >
            Pull New Model
          </Button>
          <Button
            variant="outlined"
            startIcon={<Refresh />}
            onClick={() => {
              setLoading(true);
              fetchModels();
            }}
          >
            Refresh
          </Button>
        </Box>
      </Paper>

      {/* Available Models */}
      <Paper elevation={3} sx={{ p: 4, mb: 4 }}>
        <Typography variant="h5" gutterBottom>
          Installed Models
        </Typography>
        
        {models.length === 0 ? (
          <Alert severity="info">
            No models installed. Pull a model to get started.
          </Alert>
        ) : (
          <List>
            {models.map((model, index) => (
              <React.Fragment key={model.name}>
                <ListItem>
                  <ListItemText
                    primary={
                      <Box display="flex" alignItems="center" gap={2}>
                        <Typography variant="h6">{model.name}</Typography>
                        {model.name === activeModel && (
                          <Chip 
                            label="Active" 
                            color="success" 
                            size="small"
                            icon={<CheckCircle />}
                          />
                        )}
                      </Box>
                    }
                    secondary={
                      <Box>
                        <Typography variant="body2" color="text.secondary">
                          Size: {formatModelSize(model.size)}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Modified: {new Date(model.modified_at).toLocaleDateString()}
                        </Typography>
                      </Box>
                    }
                  />
                  <ListItemSecondaryAction>
                    <Box display="flex" gap={1}>
                      {model.name !== activeModel && (
                        <Button
                          variant="outlined"
                          size="small"
                          onClick={() => handleSetActiveModel(model.name)}
                        >
                          Set Active
                        </Button>
                      )}
                      <IconButton
                        edge="end"
                        aria-label="delete"
                        onClick={() => handleDeleteModel(model.name)}
                        color="error"
                      >
                        <Delete />
                      </IconButton>
                    </Box>
                  </ListItemSecondaryAction>
                </ListItem>
                {index < models.length - 1 && <Divider />}
              </React.Fragment>
            ))}
          </List>
        )}
      </Paper>

      {/* Available Models from Ollama */}
      {availableModels.length > 0 && (
        <Paper elevation={3} sx={{ p: 4, mb: 4 }}>
          <Typography variant="h5" gutterBottom>
            Popular Models
          </Typography>
          <Typography variant="body2" color="text.secondary" paragraph>
            These models are available for download from Ollama
          </Typography>
          
          <Grid container spacing={2}>
            {availableModels.map((model) => (
              <Grid item xs={12} md={6} lg={4} key={model.name}>
                <Card variant="outlined">
                  <CardContent>
                    <Typography variant="h6" gutterBottom>
                      {model.name}
                    </Typography>
                    <Typography variant="body2" color="text.secondary" paragraph>
                      {model.description || 'No description available'}
                    </Typography>
                    <Box display="flex" justifyContent="space-between" alignItems="center">
                      <Typography variant="caption">
                        {model.size || 'Size unknown'}
                      </Typography>
                      <Button
                        variant="outlined"
                        size="small"
                        startIcon={<Download />}
                        onClick={() => {
                          setNewModelName(model.name);
                          setPullDialog(true);
                        }}
                      >
                        Pull
                      </Button>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </Paper>
      )}

      {/* Pull Model Dialog */}
      <Dialog open={pullDialog} onClose={() => setPullDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Pull New Model</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Model Name"
            type="text"
            fullWidth
            variant="outlined"
            value={newModelName}
            onChange={(e) => setNewModelName(e.target.value)}
            placeholder="e.g., llama3.1, gemma2, phi3"
            helperText="Enter the name of the model you want to pull from Ollama"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPullDialog(false)}>Cancel</Button>
          <Button 
            onClick={handlePullModel} 
            variant="contained"
            disabled={pulling || !newModelName.trim()}
            startIcon={pulling ? <CircularProgress size={20} /> : <Download />}
          >
            {pulling ? 'Pulling...' : 'Pull Model'}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default ConfigPage;