import React, { useState, useEffect } from 'react';
import {
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
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemIcon
} from '@mui/material';
import {
  CheckCircle,
  Assignment,
  TrendingUp,
  Business,
  Group,
  Science,
  Lightbulb
} from '@mui/icons-material';
import { useTranslation } from 'react-i18next';

const ReviewResults = ({ pitchDeckId, onClose }) => {
  const { t } = useTranslation('review');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [processingStatus, setProcessingStatus] = useState('processing');

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
      setError('Failed to fetch results');
      setLoading(false);
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
      <Paper elevation={3} sx={{ p: 3, maxWidth: 800, mx: 'auto', mt: 3 }}>
        <Box display="flex" flexDirection="column" alignItems="center" gap={2}>
          <CircularProgress />
          <Typography variant="h6">
            {processingStatus === 'processing' 
              ? t('processing.analyzing') 
              : t('processing.loading')}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {t('processing.pleaseWait')}
          </Typography>
        </Box>
      </Paper>
    );
  }

  if (error) {
    return (
      <Paper elevation={3} sx={{ p: 3, maxWidth: 800, mx: 'auto', mt: 3 }}>
        <Alert severity="error">{error}</Alert>
      </Paper>
    );
  }

  if (!results) {
    return (
      <Paper elevation={3} sx={{ p: 3, maxWidth: 800, mx: 'auto', mt: 3 }}>
        <Alert severity="info">{t('results.noResults')}</Alert>
      </Paper>
    );
  }

  return (
    <Paper elevation={3} sx={{ p: 3, maxWidth: 1000, mx: 'auto', mt: 3 }}>
      {/* Header */}
      <Box mb={3}>
        <Typography variant="h4" gutterBottom>
          {t('results.title')}
        </Typography>
        <Typography variant="body1" color="text.secondary">
          {results.company_offering || t('results.analysisComplete')}
        </Typography>
      </Box>

      {/* Overall Score */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box display="flex" alignItems="center" justifyContent="space-between">
            <Typography variant="h6">{t('results.overallScore')}</Typography>
            <Chip
              label={`${results.score || 0}/7`}
              color={getScoreColor(results.score || 0)}
              size="large"
            />
          </Box>
          <Box mt={2}>
            <LinearProgress
              variant="determinate"
              value={(results.score || 0) * 100 / 7}
              color={getScoreColor(results.score || 0)}
            />
          </Box>
        </CardContent>
      </Card>

      {/* Detailed Scores */}
      <Typography variant="h6" gutterBottom sx={{ mt: 3 }}>
        {t('results.detailedAnalysis')}
      </Typography>
      
      <Grid container spacing={2} sx={{ mb: 3 }}>
        {results.report_scores && Object.entries(results.report_scores).map(([area, score]) => (
          <Grid item xs={12} md={6} key={area}>
            <Card variant="outlined">
              <CardContent>
                <Box display="flex" alignItems="center" gap={2}>
                  {getScoreIcon(area)}
                  <Box flex={1}>
                    <Typography variant="subtitle1" fontWeight="bold">
                      {t(`areas.${area}`, area.replace('_', ' '))}
                    </Typography>
                    <Box display="flex" alignItems="center" gap={1}>
                      <LinearProgress
                        variant="determinate"
                        value={score * 100 / 7}
                        color={getScoreColor(score)}
                        sx={{ flex: 1, height: 8 }}
                      />
                      <Typography variant="body2" fontWeight="bold">
                        {score}/7
                      </Typography>
                    </Box>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Analysis Details */}
      {results.report_chapters && (
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            {t('results.analysisDetails')}
          </Typography>
          {Object.entries(results.report_chapters).map(([area, analysis]) => (
            <Card key={area} variant="outlined" sx={{ mb: 2 }}>
              <CardContent>
                <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
                  {t(`areas.${area}`, area.replace('_', ' '))}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {analysis || t('results.noAnalysisAvailable')}
                </Typography>
              </CardContent>
            </Card>
          ))}
        </Box>
      )}

      {/* Scientific Hypotheses */}
      {results.scientific_hypotheses && (
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            {t('results.scientificHypotheses')}
          </Typography>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="body2" color="text.secondary">
                {results.scientific_hypotheses}
              </Typography>
            </CardContent>
          </Card>
        </Box>
      )}

      {/* Key Points */}
      {results.key_points && results.key_points.length > 0 && (
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            {t('results.keyPoints')}
          </Typography>
          <List>
            {results.key_points.map((point, index) => (
              <ListItem key={index}>
                <ListItemIcon>
                  <CheckCircle color="success" />
                </ListItemIcon>
                <ListItemText primary={point} />
              </ListItem>
            ))}
          </List>
        </Box>
      )}

      {/* Recommendations */}
      {results.recommendations && results.recommendations.length > 0 && (
        <Box sx={{ mb: 3 }}>
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
        </Box>
      )}

      {/* Processing Metadata */}
      {results.processing_metadata && (
        <Box sx={{ mt: 3, pt: 2, borderTop: 1, borderColor: 'divider' }}>
          <Typography variant="caption" color="text.secondary">
            {t('results.processedBy')} {results.model_version || 'AI v1.0'} • 
            {t('results.confidence')}: {Math.round((results.confidence_score || 0) * 100)}%
          </Typography>
        </Box>
      )}
    </Paper>
  );
};

export default ReviewResults;