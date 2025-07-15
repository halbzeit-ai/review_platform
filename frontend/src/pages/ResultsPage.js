import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Container,
  Paper,
  Typography,
  Box,
  Grid,
  Card,
  CardContent,
  Chip,
  LinearProgress,
  Alert,
  CircularProgress,
  Breadcrumbs,
  Link,
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  IconButton
} from '@mui/material';
import {
  ArrowBack,
  CheckCircle,
  Assignment,
  TrendingUp,
  Business,
  Group,
  Science,
  Lightbulb,
  Home
} from '@mui/icons-material';
import { useTranslation } from 'react-i18next';

const ResultsPage = () => {
  const { pitchDeckId } = useParams();
  const navigate = useNavigate();
  const { t } = useTranslation('review');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [processingStatus, setProcessingStatus] = useState('processing');
  const [deckInfo, setDeckInfo] = useState(null);

  useEffect(() => {
    if (pitchDeckId) {
      checkProcessingStatus();
    }
  }, [pitchDeckId]);

  const checkProcessingStatus = async () => {
    try {
      const user = JSON.parse(localStorage.getItem('user'));
      const token = user?.token;
      
      if (!token) {
        setError('Not authenticated');
        setLoading(false);
        return;
      }
      
      const response = await fetch(`/api/documents/processing-status/${pitchDeckId}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to check processing status');
      }

      const data = await response.json();
      setProcessingStatus(data.processing_status);
      setDeckInfo({
        id: data.pitch_deck_id,
        fileName: data.file_name,
        createdAt: data.created_at
      });

      if (data.processing_status === 'completed') {
        await fetchResults();
      } else if (data.processing_status === 'failed') {
        setError('Processing failed. Please try again.');
        setLoading(false);
      } else {
        // Still processing, check again in 5 seconds
        setTimeout(checkProcessingStatus, 5000);
      }
    } catch (err) {
      setError('Failed to check processing status');
      setLoading(false);
    }
  };

  const fetchResults = async () => {
    try {
      const user = JSON.parse(localStorage.getItem('user'));
      const token = user?.token;
      
      if (!token) {
        setError('Not authenticated');
        setLoading(false);
        return;
      }
      
      const response = await fetch(`/api/documents/results/${pitchDeckId}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to fetch results');
      }

      const data = await response.json();
      setResults(data.results);
      setLoading(false);
    } catch (err) {
      console.log('Results not ready yet, will retry in 5 seconds');
      // Results might not be ready yet, continue polling
      setTimeout(checkProcessingStatus, 5000);
    }
  };

  const getScoreColor = (score) => {
    if (score >= 6) return 'success';
    if (score >= 4) return 'warning';
    return 'error';
  };

  const getScoreIcon = (area) => {
    const icons = {
      'problem': <Assignment />,
      'solution': <Lightbulb />,
      'product_market_fit': <TrendingUp />,
      'monetisation': <Business />,
      'organisation': <Group />,
      'competition': <Science />,
      'execution': <CheckCircle />
    };
    return icons[area] || <Assignment />;
  };

  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
        <Paper elevation={3} sx={{ p: 4 }}>
          <Box display="flex" flexDirection="column" alignItems="center" gap={2}>
            <CircularProgress size={60} />
            <Typography variant="h5">
              {processingStatus === 'processing' 
                ? t('processing.analyzing') 
                : t('processing.loading')}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {t('processing.pleaseWait')}
            </Typography>
          </Box>
        </Paper>
      </Container>
    );
  }

  if (error) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
        <Paper elevation={3} sx={{ p: 4 }}>
          <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>
          <Box display="flex" gap={2}>
            <IconButton onClick={() => navigate('/dashboard/startup')}>
              <ArrowBack />
            </IconButton>
            <Typography variant="h6">Back to Dashboard</Typography>
          </Box>
        </Paper>
      </Container>
    );
  }

  if (!results) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
        <Paper elevation={3} sx={{ p: 4 }}>
          <Alert severity="info">{t('results.noResults')}</Alert>
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
          onClick={() => navigate('/dashboard/startup')}
          sx={{ display: 'flex', alignItems: 'center' }}
        >
          <Home sx={{ mr: 0.5 }} fontSize="inherit" />
          Dashboard
        </Link>
        <Typography color="text.primary">Analysis Results</Typography>
      </Breadcrumbs>

      {/* Header */}
      <Paper elevation={3} sx={{ p: 4, mb: 4 }}>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
          <Box>
            <Typography variant="h4" gutterBottom>
              {t('results.title')}
            </Typography>
            <Typography variant="subtitle1" color="text.secondary">
              {deckInfo?.fileName}
            </Typography>
          </Box>
          <IconButton onClick={() => navigate('/dashboard/startup')}>
            <ArrowBack />
          </IconButton>
        </Box>

        {/* Company Summary - Always First */}
        <Card variant="outlined" sx={{ mb: 3, bgcolor: 'primary.50' }}>
          <CardContent>
            <Typography variant="h6" gutterBottom color="primary">
              Company Overview
            </Typography>
            <Typography variant="body1" paragraph>
              {results.company_offering || 'No company summary available'}
            </Typography>
            {results.key_points && results.key_points.length > 0 && (
              <Box>
                <Typography variant="subtitle2" gutterBottom>
                  Key Points:
                </Typography>
                <List dense>
                  {results.key_points.slice(0, 3).map((point, index) => (
                    <ListItem key={index} sx={{ py: 0.5 }}>
                      <ListItemIcon sx={{ minWidth: 32 }}>
                        <CheckCircle color="success" fontSize="small" />
                      </ListItemIcon>
                      <ListItemText primary={point} />
                    </ListItem>
                  ))}
                </List>
              </Box>
            )}
          </CardContent>
        </Card>

        {/* Overall Score */}
        <Card variant="outlined" sx={{ mb: 3 }}>
          <CardContent>
            <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
              <Typography variant="h6">{t('results.overallScore')}</Typography>
              <Chip
                label={`${results.score || 0}/7`}
                color={getScoreColor(results.score || 0)}
                size="large"
                sx={{ fontSize: '1.1rem', fontWeight: 'bold' }}
              />
            </Box>
            <LinearProgress
              variant="determinate"
              value={(results.score || 0) * 100 / 7}
              color={getScoreColor(results.score || 0)}
              sx={{ height: 12, borderRadius: 6 }}
            />
          </CardContent>
        </Card>
      </Paper>

      {/* Detailed Analysis */}
      <Paper elevation={3} sx={{ p: 4, mb: 4 }}>
        <Typography variant="h5" gutterBottom>
          {t('results.detailedAnalysis')}
        </Typography>
        
        {/* Detailed Scores */}
        <Grid container spacing={3} sx={{ mb: 4 }}>
          {results.report_scores && Object.entries(results.report_scores).map(([area, score]) => (
            <Grid item xs={12} md={6} key={area}>
              <Card variant="outlined" sx={{ height: '100%' }}>
                <CardContent>
                  <Box display="flex" alignItems="center" gap={2} mb={2}>
                    {getScoreIcon(area)}
                    <Typography variant="h6" fontWeight="bold">
                      {t(`areas.${area}`, area.replace('_', ' '))}
                    </Typography>
                  </Box>
                  <Box display="flex" alignItems="center" gap={2}>
                    <LinearProgress
                      variant="determinate"
                      value={score * 100 / 7}
                      color={getScoreColor(score)}
                      sx={{ flex: 1, height: 10, borderRadius: 5 }}
                    />
                    <Typography variant="h6" fontWeight="bold" color={getScoreColor(score) + '.main'}>
                      {score}/7
                    </Typography>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>

        <Divider sx={{ my: 4 }} />

        {/* Analysis Details */}
        {results.report_chapters && (
          <Box>
            <Typography variant="h6" gutterBottom>
              {t('results.analysisDetails')}
            </Typography>
            {Object.entries(results.report_chapters).map(([area, analysis]) => (
              <Card key={area} variant="outlined" sx={{ mb: 3 }}>
                <CardContent>
                  <Box display="flex" alignItems="center" gap={2} mb={2}>
                    {getScoreIcon(area)}
                    <Typography variant="h6" fontWeight="bold">
                      {t(`areas.${area}`, area.replace('_', ' '))}
                    </Typography>
                  </Box>
                  <Typography variant="body1" paragraph>
                    {analysis || t('results.noAnalysisAvailable')}
                  </Typography>
                </CardContent>
              </Card>
            ))}
          </Box>
        )}
      </Paper>

      {/* Additional Insights */}
      <Paper elevation={3} sx={{ p: 4, mb: 4 }}>
        <Typography variant="h5" gutterBottom>
          Additional Insights
        </Typography>

        {/* Scientific Hypotheses */}
        {results.scientific_hypotheses && (
          <Card variant="outlined" sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                {t('results.scientificHypotheses')}
              </Typography>
              <Typography variant="body1">
                {results.scientific_hypotheses}
              </Typography>
            </CardContent>
          </Card>
        )}

        {/* Recommendations */}
        {results.recommendations && results.recommendations.length > 0 && (
          <Card variant="outlined" sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                {t('results.recommendations')}
              </Typography>
              <List>
                {results.recommendations.map((rec, index) => (
                  <ListItem key={index}>
                    <ListItemIcon>
                      <Lightbulb color="warning" />
                    </ListItemIcon>
                    <ListItemText primary={rec} />
                  </ListItem>
                ))}
              </List>
            </CardContent>
          </Card>
        )}

        {/* Processing Metadata */}
        {results.processing_metadata && (
          <Box sx={{ mt: 4, pt: 2, borderTop: 1, borderColor: 'divider' }}>
            <Typography variant="caption" color="text.secondary">
              {t('results.processedBy')} {results.model_version || 'AI v1.0'} • 
              {t('results.confidence')}: {Math.round((results.confidence_score || 0) * 100)}%
            </Typography>
          </Box>
        )}
      </Paper>
    </Container>
  );
};

export default ResultsPage;