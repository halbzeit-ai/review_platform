import React, { useState, useEffect } from 'react';
import {
  Paper,
  Typography,
  Box,
  Card,
  CardContent,
  Chip,
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
import { RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, ResponsiveContainer } from 'recharts';
import { formatMarkdownText } from '../utils/markdownFormatter';

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

  // Use shared markdown formatting utility
  const formatText = formatMarkdownText;

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

  // Prepare radar chart data
  const prepareRadarData = () => {
    if (!results) return [];
    
    // Use healthcare template data if available
    if (results.chapter_analysis) {
      return Object.entries(results.chapter_analysis).map(([key, chapter]) => {
        let dimensionName = chapter.name || key.replace('_', ' ');
        
        // Shorten long dimension names for better display
        if (dimensionName.length > 20) {
          dimensionName = dimensionName.substring(0, 17) + '...';
        }
        
        return {
          dimension: dimensionName,
          score: chapter.weighted_score || 0,
          maxScore: 7,
          originalKey: key
        };
      });
    }
    
    // Fallback to legacy report_scores
    if (results.report_scores) {
      return Object.entries(results.report_scores).map(([key, score]) => {
        let dimensionName = key.replace('_', ' ');
        
        // Capitalize first letter of each word
        dimensionName = dimensionName.replace(/\b\w/g, l => l.toUpperCase());
        
        return {
          dimension: dimensionName,
          score: score || 0,
          maxScore: 7,
          originalKey: key
        };
      });
    }
    
    return [];
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

  // Check if this is a dojo template processing result
  const isDojoTemplateResult = results.analysis_metadata?.source === 'dojo_experiment' || 
                               results.analysis_metadata?.source === 'template_processing';

  return (
    <Box>
      {/* Dojo Template Processing Results */}
      {isDojoTemplateResult ? (
        <>
          {/* Template Processing Header */}
          <Card variant="outlined" sx={{ mb: 3, bgcolor: 'info.50' }}>
            <CardContent>
              <Typography variant="h6" gutterBottom color="info.main">
                Template Analysis Results
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Template: {results.template_used} {results.experiment_name && `| Experiment: ${results.experiment_name}`}
              </Typography>
              {results.analysis_metadata?.processed_at && (
                <Typography variant="body2" color="text.secondary">
                  Processed: {new Date(results.analysis_metadata.processed_at).toLocaleString()}
                </Typography>
              )}
            </CardContent>
          </Card>

          {/* Template Analysis Content */}
          <Card variant="outlined" sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Analysis
              </Typography>
              <Box sx={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>
                {formatText(results.template_analysis || 'No template analysis available')}
              </Box>
            </CardContent>
          </Card>

          {/* Slide Images (if available) */}
          {results.slide_images && results.slide_images.length > 0 && (
            <Card variant="outlined" sx={{ mb: 3 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Slide Images ({results.slide_images.length})
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  Slide images generated during template processing
                </Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                  {results.slide_images.slice(0, 6).map((imagePath, index) => (
                    <Chip 
                      key={index}
                      label={`Slide ${index + 1}`}
                      variant="outlined"
                      size="small"
                    />
                  ))}
                  {results.slide_images.length > 6 && (
                    <Chip 
                      label={`+${results.slide_images.length - 6} more`}
                      variant="outlined"
                      size="small"
                      color="primary"
                    />
                  )}
                </Box>
              </CardContent>
            </Card>
          )}
        </>
      ) : (
        <>
          {/* Regular Analysis Results */}
          {/* Company Summary - Always First */}
          <Card variant="outlined" sx={{ mb: 3, bgcolor: 'primary.50' }}>
            <CardContent>
              <Typography variant="h6" gutterBottom color="primary">
                {t('results.companyOverview')}
              </Typography>
              <Box sx={{ mb: 2 }}>
                {formatText(results.company_offering || 'No company summary available')}
              </Box>
          {results.key_points && results.key_points.length > 0 && (
            <Box>
              <Typography variant="subtitle2" gutterBottom>
                {t('results.keyPoints')}:
              </Typography>
              <List dense sx={{ pl: 1 }}>
                {results.key_points.slice(0, 3).map((point, index) => (
                  <ListItem key={index} sx={{ py: 0.3, pl: 0 }}>
                    <ListItemIcon sx={{ minWidth: 20 }}>
                      <Box sx={{ 
                        width: 6, 
                        height: 6, 
                        borderRadius: '50%', 
                        bgcolor: 'primary.main',
                        mt: 1
                      }} />
                    </ListItemIcon>
                    <ListItemText 
                      primary={
                        <Typography variant="body2" sx={{ fontSize: '0.9rem', lineHeight: 1.4 }}>
                          {formatText(point)}
                        </Typography>
                      } 
                    />
                  </ListItem>
                ))}
              </List>
            </Box>
          )}
        </CardContent>
      </Card>

      {/* Healthcare Classification (if available) */}
      {results.classification && (
        <Card variant="outlined" sx={{ mb: 3 }}>
          <CardContent>
            <Box sx={{ p: 2, bgcolor: 'success.50', borderRadius: 1 }}>
              <Typography variant="body2" color="success.main">
                <strong>{t('results.healthcareClassification')}:</strong> {results.classification.sector || 'Healthcare'} 
                {results.classification.confidence && (
                  <span> ({t('results.confidence')}: {Math.round(results.classification.confidence * 100)}%)</span>
                )}
              </Typography>
            </Box>
          </CardContent>
        </Card>
      )}

      {/* Detailed Analysis */}
      <Paper elevation={1} sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          {t('results.detailedAnalysis')}
        </Typography>
        
        {/* Radar Chart with Overall Score */}
        <Card variant="outlined" sx={{ mb: 4 }}>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Typography 
                  variant="h4" 
                  component="div" 
                  sx={{ 
                    fontWeight: 'bold',
                    color: getScoreColor(results.overall_score || results.score || 0) === 'success' ? 'success.main' :
                           getScoreColor(results.overall_score || results.score || 0) === 'warning' ? 'warning.main' : 'error.main'
                  }}
                >
                  {(results.overall_score || results.score || 0).toFixed(1)}
                </Typography>
                <Box>
                  <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.2 }}>
                    {t('results.overallScore')}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.2 }}>
                    out of 7
                  </Typography>
                </Box>
              </Box>
              <Typography variant="h6" sx={{ textAlign: 'center', flex: 1 }}>
                {t('results.analysisDimensions')}
              </Typography>
            </Box>
            <Box sx={{ height: 400, width: '100%' }}>
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={prepareRadarData()} margin={{ top: 40, right: 100, bottom: 40, left: 100 }}>
                  <PolarGrid 
                    gridType="polygon" 
                    stroke="#e0e0e0"
                    strokeWidth={1}
                  />
                  <PolarAngleAxis 
                    dataKey="dimension" 
                    tick={{ 
                      fontSize: 11, 
                      fill: '#555',
                      fontWeight: 500
                    }}
                    className="radar-axis"
                  />
                  <PolarRadiusAxis 
                    angle={90} 
                    domain={[0, 7]} 
                    tick={{ fontSize: 9, fill: '#999' }}
                    tickCount={8}
                    stroke="#e0e0e0"
                  />
                  <Radar 
                    dataKey="score" 
                    stroke="#1976d2" 
                    fill="#1976d2" 
                    fillOpacity={0.25}
                    strokeWidth={2}
                    dot={{ r: 4, fill: '#1976d2', strokeWidth: 2, stroke: '#fff' }}
                  />
                </RadarChart>
              </ResponsiveContainer>
            </Box>
            
            {/* Legend/Summary */}
            <Box sx={{ mt: 2, display: 'flex', flexWrap: 'wrap', gap: 1, justifyContent: 'center' }}>
              {prepareRadarData().map((item, index) => (
                <Chip
                  key={index}
                  label={`${item.dimension}: ${item.score.toFixed(1)}/7`}
                  size="small"
                  color={getScoreColor(item.score)}
                  sx={{ fontSize: '0.75rem' }}
                />
              ))}
            </Box>
          </CardContent>
        </Card>

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
                    <Typography variant="subtitle1" fontWeight="bold" sx={{ fontSize: '1rem' }}>
                      {chapter.name || chapterKey.replace('_', ' ')}
                    </Typography>
                    <Chip
                      label={`${chapter.weighted_score?.toFixed(1) || 0}/7`}
                      color={getScoreColor(chapter.weighted_score || 0)}
                      size="small"
                      sx={{ fontSize: '0.75rem' }}
                    />
                    <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.8rem' }}>
                      ({chapter.total_questions || 0} {t('results.questions')})
                    </Typography>
                  </Box>
                </AccordionSummary>
                <AccordionDetails>
                  <Box sx={{ pt: 1 }}>
                    {chapter.description && (
                      <Typography variant="body2" color="text.secondary" sx={{ 
                        mb: 2, 
                        fontStyle: 'italic',
                        fontSize: '0.85rem',
                        lineHeight: 1.4
                      }}>
                        {chapter.description}
                      </Typography>
                    )}
                    
                    {/* Individual Questions */}
                    {chapter.questions && chapter.questions.length > 0 && (
                      <Box>
                        {chapter.questions.map((question, qIndex) => (
                          <Card key={qIndex} variant="outlined" sx={{ mb: 1.5, bgcolor: 'grey.50' }}>
                            <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                              <Box display="flex" alignItems="flex-start" gap={2} mb={1}>
                                <Chip
                                  label={`Q${qIndex + 1}`}
                                  color="primary"
                                  size="small"
                                  sx={{ minWidth: 36, fontSize: '0.75rem' }}
                                />
                                <Box sx={{ flex: 1 }}>
                                  <Typography variant="body2" fontWeight="bold" sx={{ 
                                    fontSize: '0.9rem', 
                                    lineHeight: 1.4
                                  }}>
                                    {question.question_text}
                                  </Typography>
                                  {question.healthcare_focus && (
                                    <Typography variant="body2" color="info.main" sx={{ 
                                      fontSize: '0.85rem', 
                                      mt: 0.5,
                                      fontStyle: 'italic'
                                    }}>
                                      {question.healthcare_focus}
                                    </Typography>
                                  )}
                                </Box>
                                <Chip
                                  label={`${question.score}/7`}
                                  color={getScoreColor(question.score)}
                                  size="small"
                                  sx={{ fontSize: '0.75rem' }}
                                />
                              </Box>
                              
                              <Box sx={{ pl: 1, ml: 5 }}>
                                <Box sx={{ fontSize: '0.9rem' }}>
                                  {formatText(question.response)}
                                </Box>
                                
                                {/* Debug: Show scoring response */}
                                {question.scoring_response && (
                                  <Box sx={{ mt: 1.5, p: 1.5, bgcolor: 'warning.50', borderRadius: 1, border: '1px solid', borderColor: 'warning.200' }}>
                                    <Typography variant="caption" color="warning.dark" fontWeight="bold" sx={{ fontSize: '0.75rem' }}>
                                      {t('debug.scoringResponse')}
                                    </Typography>
                                    <Box sx={{ mt: 0.5, '& .MuiTypography-root': { color: 'warning.dark', fontSize: '0.8rem' } }}>
                                      {formatText(question.scoring_response)}
                                    </Box>
                                  </Box>
                                )}
                              </Box>
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
          {t('results.additionalInsights')}
        </Typography>

        {/* Healthcare Specialized Analysis */}
        {results.specialized_analysis && (
          <Box sx={{ mb: 3 }}>
            <Typography variant="h6" gutterBottom>
              {t('results.healthcareSpecificAnalysis')}
            </Typography>
            
            {/* Clinical Validation */}
            {results.specialized_analysis.clinical_validation && (
              <Card variant="outlined" sx={{ mb: 2 }}>
                <CardContent>
                  <Typography variant="subtitle1" gutterBottom fontWeight="bold" color="info.main">
                    <Science sx={{ mr: 1, verticalAlign: 'middle' }} />
                    {t('results.clinicalValidation')}
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
                    {t('results.regulatoryPathway')}
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
                    {t('results.scientificHypothesis')}
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
              <Typography variant="subtitle1" gutterBottom fontWeight="bold" sx={{ fontSize: '1rem' }}>
                {t('results.recommendations')}
              </Typography>
              <List sx={{ pl: 1 }}>
                {results.recommendations.map((rec, index) => (
                  <ListItem key={index} sx={{ py: 0.5, pl: 0, alignItems: 'flex-start' }}>
                    <ListItemIcon sx={{ minWidth: 24, mt: 0.5 }}>
                      <Lightbulb color="warning" fontSize="small" />
                    </ListItemIcon>
                    <ListItemText 
                      primary={
                        <Box sx={{ fontSize: '0.9rem' }}>
                          {formatText(rec)}
                        </Box>
                      } 
                    />
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
        </>
      )}
    </Box>
  );
};

export default ProjectResults;