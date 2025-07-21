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
  Divider,
  Tabs,
  Tab
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
  Refresh,
  Visibility,
  TextFields,
  Assessment,
  Science
} from '@mui/icons-material';
import { useTranslation } from 'react-i18next';

const MODEL_TYPES = [
  { key: 'vision', label: 'Vision Analysis', icon: <Visibility />, description: 'Models for analyzing PDF images and extracting visual content' },
  { key: 'text', label: 'Text Generation', icon: <TextFields />, description: 'Models for generating detailed analysis reports' },
  { key: 'scoring', label: 'Scoring', icon: <Assessment />, description: 'Models for scoring and evaluating content' },
  { key: 'science', label: 'Scientific Analysis', icon: <Science />, description: 'Models for analyzing scientific hypotheses and health-related content' }
];

const ConfigPage = () => {
  const navigate = useNavigate();
  const { t } = useTranslation('dashboard');
  const [loading, setLoading] = useState(true);
  const [models, setModels] = useState([]);
  const [availableModels, setAvailableModels] = useState([]);
  const [activeModels, setActiveModels] = useState({});
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [pullDialog, setPullDialog] = useState(false);
  const [newModelName, setNewModelName] = useState('');
  const [selectedModelType, setSelectedModelType] = useState('vision');
  const [pulling, setPulling] = useState(false);
  const [currentTab, setCurrentTab] = useState(0);

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
      setActiveModels(data.active_models || {});
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

  const handleSetActiveModel = async (modelName, modelType) => {
    try {
      const user = JSON.parse(localStorage.getItem('user'));
      const token = user?.token;
      
      const response = await fetch('/api/config/set-active-model', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ 
          model_name: modelName,
          model_type: modelType
        })
      });

      if (!response.ok) {
        throw new Error('Failed to set active model');
      }

      setActiveModels(prev => ({
        ...prev,
        [modelType]: modelName
      }));
      setSuccess(`Successfully set ${modelName} as active ${modelType} model`);
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
        body: JSON.stringify({ 
          model_name: newModelName.trim(),
          model_type: selectedModelType
        })
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
        body: JSON.stringify({ 
          model_name: modelName,
          model_type: selectedModelType
        })
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

  const getCurrentModelType = () => MODEL_TYPES[currentTab];

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
              {t('modelConfig.title')}
            </Typography>
            <Typography variant="subtitle1" color="text.secondary">
              {t('modelConfig.description')}
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

        {/* Active Models Overview - Compact */}
        <Typography variant="h6" gutterBottom>
          Active Models by Type
        </Typography>
        <Grid container spacing={1} sx={{ mb: 3 }}>
          {MODEL_TYPES.map((modelType) => (
            <Grid item xs={6} md={3} key={modelType.key}>
              <Card variant="outlined" sx={{ 
                bgcolor: activeModels[modelType.key] ? 'success.50' : 'grey.50',
                borderColor: activeModels[modelType.key] ? 'success.main' : 'grey.300'
              }}>
                <CardContent sx={{ py: 1.5, px: 2, '&:last-child': { pb: 1.5 } }}>
                  <Box display="flex" alignItems="center" gap={0.5} mb={0.5}>
                    {modelType.icon}
                    <Typography variant="body2" fontWeight="bold" fontSize={"0.875rem"}>
                      {modelType.label}
                    </Typography>
                  </Box>
                  <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 0.5, lineHeight: 1.2 }}>
                    {activeModels[modelType.key] || 'No model selected'}
                  </Typography>
                  {activeModels[modelType.key] && (
                    <Chip 
                      label="Active" 
                      color="success" 
                      size="small"
                      sx={{ height: 20, fontSize: '0.7rem' }}
                    />
                  )}
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>

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

      {/* Model Type Tabs */}
      <Paper elevation={3} sx={{ p: 4, mb: 4 }}>
        <Tabs 
          value={currentTab} 
          onChange={(e, newValue) => setCurrentTab(newValue)}
          sx={{ mb: 3 }}
        >
          {MODEL_TYPES.map((modelType, index) => (
            <Tab 
              key={modelType.key}
              label={modelType.label}
              icon={modelType.icon}
              iconPosition="start"
            />
          ))}
        </Tabs>

        {/* Current Model Type Description */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            {getCurrentModelType().label} Models
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {getCurrentModelType().description}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            Currently active: <strong>{activeModels[getCurrentModelType().key] || 'None'}</strong>
          </Typography>
        </Box>
        
        {/* Available Models */}
        <Typography variant="h6" gutterBottom>
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
                        {model.name === activeModels[getCurrentModelType().key] && (
                          <Chip 
                            label={t('modelConfig.labels.active')} 
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
                      {model.name !== activeModels[getCurrentModelType().key] && (
                        <Button
                          variant="outlined"
                          size="small"
                          onClick={() => handleSetActiveModel(model.name, getCurrentModelType().key)}
                        >
                          Set as {getCurrentModelType().label}
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


      {/* Pull Model Dialog */}
      <Dialog open={pullDialog} onClose={() => setPullDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Pull New Model</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label={t('modelConfig.labels.modelName')}
            type="text"
            fullWidth
            variant="outlined"
            value={newModelName}
            onChange={(e) => setNewModelName(e.target.value)}
            placeholder="e.g., llama3.1, gemma2, phi3"
            helperText={t('modelConfig.messages.pullModelHelper')}
            sx={{ mb: 2 }}
          />
          <FormControl fullWidth variant="outlined">
            <InputLabel>{t('modelConfig.labels.modelType')}</InputLabel>
            <Select
              value={selectedModelType}
              onChange={(e) => setSelectedModelType(e.target.value)}
              label={t('modelConfig.labels.modelType')}
            >
              {MODEL_TYPES.map((type) => (
                <MenuItem key={type.key} value={type.key}>
                  <Box display="flex" alignItems="center" gap={1}>
                    {type.icon}
                    {type.label}
                  </Box>
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPullDialog(false)}>{t('modelConfig.buttons.cancel')}</Button>
          <Button 
            onClick={handlePullModel} 
            variant="contained"
            disabled={pulling || !newModelName.trim()}
            startIcon={pulling ? <CircularProgress size={20} /> : <Download />}
          >
            {pulling ? t('modelConfig.buttons.pulling') : t('modelConfig.buttons.pullModel')}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default ConfigPage;