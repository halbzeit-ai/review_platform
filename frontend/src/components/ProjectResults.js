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
  ListItemIcon,
  Accordion,
  AccordionSummary,
  AccordionDetails
} from '@mui/material';
import {
  CheckCircle,
  Assignment,
  TrendingUp,
  Business,
  Group,
  Science,
  Lightbulb,
  ExpandMore
} from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import { getProjectResults } from '../services/api';

const ProjectResults = ({ companyId, deckId }) => {
  const { t } = useTranslation('review');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (companyId && deckId) {
      fetchResults();
    }
  }, [companyId, deckId]);

  const fetchResults = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await getProjectResults(companyId, deckId);
      const resultsData = response.data || response;
      
      setResults(resultsData);
    } catch (err) {
      console.error('Error fetching project results:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to load results');
    } finally {
      setLoading(false);
    }
  };

  // Helper function to format text content
  const formatText = (text) => {
    if (!text) return '';
    
    // Split into paragraphs
    const paragraphs = text.split('\n\n');
    
    return paragraphs.map((paragraph, index) => {
      // Handle bold text (**text**)
      let formattedParagraph = paragraph.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
      
      // Handle numbered lists (1. text, 2. text, etc.)
      if (paragraph.match(/^\d+\.\s/)) {
        const items = paragraph.split('\n').filter(line => line.match(/^\d+\.\s/));
        return (
          <List key={index} dense sx={{ my: 1 }}>
            {items.map((item, itemIndex) => (
              <ListItem key={itemIndex} sx={{ py: 0.5, pl: 0 }}>
                <ListItemIcon sx={{ minWidth: 32 }}>
                  <Chip 
                    label={item.match(/^(\d+)\./)[1]} 
                    size="small" 
                    color="primary" 
                    sx={{ width: 24, height: 24, fontSize: '0.75rem' }}
                  />
                </ListItemIcon>
                <ListItemText 
                  primary={
                    <span dangerouslySetInnerHTML={{ 
                      __html: item.replace(/^\d+\.\s*/, '').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') 
                    }} />
                  } 
                />
              </ListItem>
            ))}
          </List>
        );
      }
      
      // Handle bullet points
      if (paragraph.trim().startsWith('*') || paragraph.trim().startsWith('-')) {
        const items = paragraph.split('\n').filter(line => line.trim().startsWith('*') || line.trim().startsWith('-'));
        return (
          <List key={index} dense sx={{ my: 1 }}>
            {items.map((item, itemIndex) => (
              <ListItem key={itemIndex} sx={{ py: 0.5 }}>
                <ListItemIcon sx={{ minWidth: 32 }}>
                  <CheckCircle color="success" fontSize="small" />
                </ListItemIcon>
                <ListItemText 
                  primary={
                    <span dangerouslySetInnerHTML={{ 
                      __html: item.replace(/^[\*\-]\s*/, '').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') 
                    }} />
                  } 
                />
              </ListItem>
            ))}
          </List>
        );
      }
      
      // Handle headers (### text)
      if (paragraph.startsWith('###')) {
        return (
          <Typography key={index} variant="h6" sx={{ mt: 2, mb: 1, fontWeight: 'bold', color: 'primary.main' }}>
            {paragraph.replace(/^###\s*/, '')}
          </Typography>
        );
      }
      
      // Handle subheaders (## text)
      if (paragraph.startsWith('##')) {
        return (
          <Typography key={index} variant="h5" sx={{ mt: 2, mb: 1, fontWeight: 'bold', color: 'primary.main' }}>
            {paragraph.replace(/^##\s*/, '')}
          </Typography>
        );
      }
      
      // Regular paragraph
      return (
        <Typography key={index} variant="body1" paragraph sx={{ lineHeight: 1.6 }}>
          <span dangerouslySetInnerHTML={{ __html: formattedParagraph }} />
        </Typography>
      );
    });
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

  if (!results) {
    return (
      <Alert severity="info" sx={{ mb: 3 }}>
        {t('results.noResults')}
      </Alert>
    );
  }

  return (
    <Box>
      {/* Company Summary - Always First */}
      <Card variant="outlined" sx={{ mb: 3, bgcolor: 'primary.50' }}>
        <CardContent>
          <Typography variant="h6" gutterBottom color="primary">
            Company Overview
          </Typography>
          <Box sx={{ mb: 2 }}>
            {formatText(results.company_offering || 'No company summary available')}
          </Box>
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
                    <ListItemText primary={formatText(point)} />
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
              label={`${results.overall_score || results.score || 0}/7`}
              color={getScoreColor(results.overall_score || results.score || 0)}
              size="large"
              sx={{ fontSize: '1.1rem', fontWeight: 'bold' }}
            />
          </Box>
          <LinearProgress
            variant="determinate"
            value={(results.overall_score || results.score || 0) * 100 / 7}
            color={getScoreColor(results.overall_score || results.score || 0)}
            sx={{ height: 12, borderRadius: 6 }}
          />
          {results.classification && (
            <Box sx={{ mt: 2, p: 2, bgcolor: 'success.50', borderRadius: 1 }}>
              <Typography variant="body2" color="success.main">
                <strong>Healthcare Classification:</strong> {results.classification.sector || 'Healthcare'} 
                {results.classification.confidence && (
                  <span> (Confidence: {Math.round(results.classification.confidence * 100)}%)</span>
                )}
              </Typography>
            </Box>
          )}
        </CardContent>
      </Card>

      {/* Detailed Analysis */}
      <Paper elevation={1} sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          {t('results.detailedAnalysis')}
        </Typography>
        
        {/* Detailed Scores */}
        <Grid container spacing={3} sx={{ mb: 4 }}>
          {results.chapter_analysis ? (
            Object.entries(results.chapter_analysis).map(([chapterKey, chapter]) => (
              <Grid item xs={12} md={6} key={chapterKey}>
                <Card variant="outlined" sx={{ height: '100%' }}>
                  <CardContent>
                    <Box display="flex" alignItems="center" gap={2} mb={2}>
                      {getScoreIcon(chapterKey)}
                      <Typography variant="subtitle1" fontWeight="bold">
                        {chapter.name || chapterKey.replace('_', ' ')}
                      </Typography>
                    </Box>
                    <Box display="flex" alignItems="center" gap={2}>
                      <LinearProgress
                        variant="determinate"
                        value={(chapter.weighted_score || 0) * 100 / 7}
                        color={getScoreColor(chapter.weighted_score || 0)}
                        sx={{ flex: 1, height: 8, borderRadius: 4 }}
                      />
                      <Typography variant="subtitle1" fontWeight="bold" color={getScoreColor(chapter.weighted_score || 0) + '.main'}>
                        {chapter.weighted_score?.toFixed(1) || 0}/7
                      </Typography>
                    </Box>
                    <Typography variant="caption" color="text.secondary">
                      {chapter.total_questions || 0} questions • Weight: {chapter.weight || 1}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            ))
          ) : results.report_scores && Object.entries(results.report_scores).map(([area, score]) => (
            <Grid item xs={12} md={6} key={area}>
              <Card variant="outlined" sx={{ height: '100%' }}>
                <CardContent>
                  <Box display="flex" alignItems="center" gap={2} mb={2}>
                    {getScoreIcon(area)}
                    <Typography variant="subtitle1" fontWeight="bold">
                      {t(`areas.${area}`, area.replace('_', ' '))}
                    </Typography>
                  </Box>
                  <Box display="flex" alignItems="center" gap={2}>
                    <LinearProgress
                      variant="determinate"
                      value={score * 100 / 7}
                      color={getScoreColor(score)}
                      sx={{ flex: 1, height: 8, borderRadius: 4 }}
                    />
                    <Typography variant="subtitle1" fontWeight="bold" color={getScoreColor(score) + '.main'}>
                      {score}/7
                    </Typography>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>

        <Divider sx={{ my: 3 }} />

        {/* Analysis Details */}
        {results.chapter_analysis ? (
          <Box>
            <Typography variant="subtitle1" gutterBottom fontWeight="bold">
              {t('results.analysisDetails')}
            </Typography>
            {Object.entries(results.chapter_analysis).map(([chapterKey, chapter]) => (
              <Accordion key={chapterKey} sx={{ mb: 1 }}>
                <AccordionSummary expandIcon={<ExpandMore />}>
                  <Box display="flex" alignItems="center" gap={2}>
                    {getScoreIcon(chapterKey)}
                    <Typography variant="subtitle1" fontWeight="bold">
                      {chapter.name || chapterKey.replace('_', ' ')}
                    </Typography>
                    <Chip
                      label={`${chapter.weighted_score?.toFixed(1) || 0}/7`}
                      color={getScoreColor(chapter.weighted_score || 0)}
                      size="small"
                    />
                    <Typography variant="body2" color="text.secondary">
                      ({chapter.total_questions || 0} questions)
                    </Typography>
                  </Box>
                </AccordionSummary>
                <AccordionDetails>
                  <Box sx={{ pt: 1 }}>
                    {chapter.description && (
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 2, fontStyle: 'italic' }}>
                        {chapter.description}
                      </Typography>
                    )}
                    
                    {/* Individual Questions */}
                    {chapter.questions && chapter.questions.length > 0 && (
                      <Box>
                        {chapter.questions.map((question, qIndex) => (
                          <Card key={qIndex} variant="outlined" sx={{ mb: 2, bgcolor: 'grey.50' }}>
                            <CardContent>
                              <Box display="flex" alignItems="center" gap={2} mb={1}>
                                <Typography variant="subtitle2" fontWeight="bold" color="primary">
                                  Q{qIndex + 1}:
                                </Typography>
                                <Typography variant="body2" fontWeight="bold">
                                  {question.question_text}
                                </Typography>
                                <Box sx={{ ml: 'auto' }}>
                                  <Chip
                                    label={`${question.score}/7`}
                                    color={getScoreColor(question.score)}
                                    size="small"
                                  />
                                </Box>
                              </Box>
                              
                              <Typography variant="body2" sx={{ mb: 1 }}>
                                <strong>Response:</strong>
                              </Typography>
                              <Box sx={{ pl: 2, borderLeft: 2, borderColor: 'primary.main' }}>
                                {formatText(question.response)}
                              </Box>
                              
                              {question.healthcare_focus && (
                                <Box sx={{ mt: 1, p: 1, bgcolor: 'info.50', borderRadius: 1 }}>
                                  <Typography variant="caption" color="info.main" fontWeight="bold">
                                    Healthcare Focus:
                                  </Typography>
                                  <Typography variant="body2" color="info.main">
                                    {question.healthcare_focus}
                                  </Typography>
                                </Box>
                              )}
                            </CardContent>
                          </Card>
                        ))}
                      </Box>
                    )}
                  </Box>
                </AccordionDetails>
              </Accordion>
            ))}
          </Box>
        ) : results.report_chapters && (
          <Box>
            <Typography variant="subtitle1" gutterBottom fontWeight="bold">
              {t('results.analysisDetails')}
            </Typography>
            {Object.entries(results.report_chapters).map(([area, analysis]) => (
              <Accordion key={area} sx={{ mb: 1 }}>
                <AccordionSummary expandIcon={<ExpandMore />}>
                  <Box display="flex" alignItems="center" gap={2}>
                    {getScoreIcon(area)}
                    <Typography variant="subtitle1" fontWeight="bold">
                      {t(`areas.${area}`, area.replace('_', ' '))}
                    </Typography>
                    {results.report_scores && results.report_scores[area] && (
                      <Chip
                        label={`${results.report_scores[area]}/7`}
                        color={getScoreColor(results.report_scores[area])}
                        size="small"
                      />
                    )}
                  </Box>
                </AccordionSummary>
                <AccordionDetails>
                  <Box sx={{ pt: 1 }}>
                    {formatText(analysis || t('results.noAnalysisAvailable'))}
                  </Box>
                </AccordionDetails>
              </Accordion>
            ))}
          </Box>
        )}
      </Paper>

      {/* Additional Insights */}
      <Paper elevation={1} sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Additional Insights
        </Typography>

        {/* Healthcare Specialized Analysis */}
        {results.specialized_analysis && (
          <Box sx={{ mb: 3 }}>
            <Typography variant="h6" gutterBottom>
              Healthcare-Specific Analysis
            </Typography>
            
            {/* Clinical Validation */}
            {results.specialized_analysis.clinical_validation && (
              <Card variant="outlined" sx={{ mb: 2 }}>
                <CardContent>
                  <Typography variant="subtitle1" gutterBottom fontWeight="bold" color="info.main">
                    <Science sx={{ mr: 1, verticalAlign: 'middle' }} />
                    Clinical Validation
                  </Typography>
                  <Box>
                    {formatText(results.specialized_analysis.clinical_validation)}
                  </Box>
                </CardContent>
              </Card>
            )}
            
            {/* Regulatory Pathway */}
            {results.specialized_analysis.regulatory_pathway && (
              <Card variant="outlined" sx={{ mb: 2 }}>
                <CardContent>
                  <Typography variant="subtitle1" gutterBottom fontWeight="bold" color="warning.main">
                    <Assignment sx={{ mr: 1, verticalAlign: 'middle' }} />
                    Regulatory Pathway
                  </Typography>
                  <Box>
                    {formatText(results.specialized_analysis.regulatory_pathway)}
                  </Box>
                </CardContent>
              </Card>
            )}
            
            {/* Scientific Hypothesis */}
            {results.specialized_analysis.scientific_hypothesis && (
              <Card variant="outlined" sx={{ mb: 2 }}>
                <CardContent>
                  <Typography variant="subtitle1" gutterBottom fontWeight="bold" color="success.main">
                    <Lightbulb sx={{ mr: 1, verticalAlign: 'middle' }} />
                    Scientific Hypothesis
                  </Typography>
                  <Box>
                    {formatText(results.specialized_analysis.scientific_hypothesis)}
                  </Box>
                </CardContent>
              </Card>
            )}
          </Box>
        )}

        {/* Scientific Hypotheses (Legacy) */}
        {results.scientific_hypotheses && !results.specialized_analysis && (
          <Card variant="outlined" sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="subtitle1" gutterBottom fontWeight="bold">
                {t('results.scientificHypotheses')}
              </Typography>
              <Box>
                {formatText(results.scientific_hypotheses)}
              </Box>
            </CardContent>
          </Card>
        )}

        {/* Recommendations */}
        {results.recommendations && results.recommendations.length > 0 && (
          <Card variant="outlined" sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="subtitle1" gutterBottom fontWeight="bold">
                {t('results.recommendations')}
              </Typography>
              <List>
                {results.recommendations.map((rec, index) => (
                  <ListItem key={index}>
                    <ListItemIcon>
                      <Lightbulb color="warning" />
                    </ListItemIcon>
                    <ListItemText primary={formatText(rec)} />
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
    </Box>
  );
};

export default ProjectResults;