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

  // Helper function to format text content with proper markdown parsing
  const formatText = (text) => {
    if (!text) return '';
    
    // Split into lines for better parsing
    const lines = text.split('\n');
    const elements = [];
    let currentKey = 0;
    
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();
      
      // Skip empty lines
      if (!line) {
        continue;
      }
      
      // Handle headers (####, ###, ##, #)
      if (line.startsWith('####')) {
        elements.push(
          <Typography key={currentKey++} variant="subtitle1" sx={{ 
            mt: 1.5, mb: 0.8, fontWeight: 'bold', color: 'primary.dark', fontSize: '1rem' 
          }}>
            {line.replace(/^####\s*/, '')}
          </Typography>
        );
        continue;
      }
      
      if (line.startsWith('###')) {
        elements.push(
          <Typography key={currentKey++} variant="h6" sx={{ 
            mt: 2, mb: 1, fontWeight: 'bold', color: 'primary.main' 
          }}>
            {line.replace(/^###\s*/, '')}
          </Typography>
        );
        continue;
      }
      
      if (line.startsWith('##')) {
        elements.push(
          <Typography key={currentKey++} variant="h5" sx={{ 
            mt: 2.5, mb: 1.2, fontWeight: 'bold', color: 'primary.main' 
          }}>
            {line.replace(/^##\s*/, '')}
          </Typography>
        );
        continue;
      }
      
      if (line.startsWith('#') && !line.startsWith('##')) {
        elements.push(
          <Typography key={currentKey++} variant="h4" sx={{ 
            mt: 3, mb: 1.5, fontWeight: 'bold', color: 'primary.main' 
          }}>
            {line.replace(/^#\s*/, '')}
          </Typography>
        );
        continue;
      }
      
      // Handle numbered lists
      if (line.match(/^\d+\.\s/)) {
        const listItems = [];
        let j = i;
        
        // Collect consecutive numbered items
        while (j < lines.length && lines[j].trim().match(/^\d+\.\s/)) {
          listItems.push(lines[j].trim());
          j++;
        }
        
        elements.push(
          <List key={currentKey++} dense sx={{ my: 0.8, pl: 2 }}>
            {listItems.map((item, itemIndex) => (
              <ListItem key={itemIndex} sx={{ py: 0.2, pl: 0 }}>
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
                    <Typography variant="body1" sx={{ fontSize: '0.9rem', lineHeight: 1.4 }}>
                      <span dangerouslySetInnerHTML={{ 
                        __html: item
                          .replace(/^\d+\.\s*/, '')
                          .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                      }} />
                    </Typography>
                  } 
                />
              </ListItem>
            ))}
          </List>
        );
        
        i = j - 1; // Skip processed lines
        continue;
      }
      
      // Handle bullet points and dashes
      if (line.startsWith('*') || line.startsWith('-') || line.startsWith('•')) {
        const listItems = [];
        let j = i;
        
        // Collect consecutive bullet items (including nested ones)
        while (j < lines.length && lines[j].trim() && 
               (lines[j].trim().startsWith('*') || 
                lines[j].trim().startsWith('-') || 
                lines[j].trim().startsWith('•') ||
                lines[j].startsWith('  ') || 
                lines[j].startsWith('\t'))) {
          if (lines[j].trim()) {
            listItems.push(lines[j].trim());
          }
          j++;
        }
        
        elements.push(
          <List key={currentKey++} dense sx={{ my: 0.8, pl: 2 }}>
            {listItems.map((item, itemIndex) => {
              // Check if this is a nested item
              const isNested = item.startsWith('  ') || item.startsWith('\t') || 
                              (!item.startsWith('*') && !item.startsWith('-') && !item.startsWith('•'));
              
              return (
                <ListItem key={itemIndex} sx={{ 
                  py: 0.1, 
                  pl: isNested ? 3 : 0,
                  display: 'flex',
                  alignItems: 'flex-start'
                }}>
                  <ListItemIcon sx={{ minWidth: 20, mt: 0.5 }}>
                    <Box sx={{ 
                      width: isNested ? 3 : 4, 
                      height: isNested ? 3 : 4, 
                      borderRadius: '50%', 
                      bgcolor: isNested ? 'text.disabled' : 'text.secondary'
                    }} />
                  </ListItemIcon>
                  <ListItemText 
                    primary={
                      <Typography variant="body1" sx={{ fontSize: '0.9rem', lineHeight: 1.4 }}>
                        <span dangerouslySetInnerHTML={{ 
                          __html: item
                            .replace(/^[*\-•]\s*/, '')
                            .replace(/^\s+/, '')
                            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                        }} />
                      </Typography>
                    } 
                  />
                </ListItem>
              );
            })}
          </List>
        );
        
        i = j - 1; // Skip processed lines
        continue;
      }
      
      // Handle regular paragraphs
      const paragraphLines = [];
      let j = i;
      
      // Collect consecutive non-header, non-list lines
      while (j < lines.length && lines[j].trim() && 
             !lines[j].trim().startsWith('#') &&
             !lines[j].trim().match(/^\d+\.\s/) &&
             !lines[j].trim().startsWith('*') &&
             !lines[j].trim().startsWith('-') &&
             !lines[j].trim().startsWith('•')) {
        paragraphLines.push(lines[j].trim());
        j++;
      }
      
      if (paragraphLines.length > 0) {
        const paragraphText = paragraphLines.join(' ');
        elements.push(
          <Typography key={currentKey++} variant="body1" paragraph sx={{ 
            lineHeight: 1.6, 
            fontSize: '0.9rem',
            color: 'text.primary',
            mb: 1.2,
            textAlign: 'justify'
          }}>
            <span dangerouslySetInnerHTML={{ 
              __html: paragraphText
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/✓\s*/g, '')
                .replace(/✔\s*/g, '')
            }} />
          </Typography>
        );
        
        i = j - 1; // Skip processed lines
      }
    }
    
    return elements;
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

  return (
    <Box>
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
                                <Typography variant="body2" fontWeight="bold" sx={{ 
                                  fontSize: '0.9rem', 
                                  lineHeight: 1.4,
                                  flex: 1
                                }}>
                                  {question.question_text}
                                </Typography>
                                <Chip
                                  label={`${question.score}/7`}
                                  color={getScoreColor(question.score)}
                                  size="small"
                                  sx={{ fontSize: '0.75rem' }}
                                />
                              </Box>
                              
                              <Box sx={{ pl: 1, borderLeft: 3, borderColor: 'primary.main', ml: 5 }}>
                                <Box sx={{ fontSize: '0.9rem' }}>
                                  {formatText(question.response)}
                                </Box>
                              </Box>
                              
                              {question.healthcare_focus && (
                                <Box sx={{ mt: 1.5, p: 1.5, bgcolor: 'info.50', borderRadius: 1, ml: 5 }}>
                                  <Typography variant="caption" color="info.main" fontWeight="bold" sx={{ fontSize: '0.75rem' }}>
                                    {t('results.healthcareFocus')}:
                                  </Typography>
                                  <Typography variant="body2" color="info.main" sx={{ fontSize: '0.85rem', mt: 0.5 }}>
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
    </Box>
  );
};

export default ProjectResults;