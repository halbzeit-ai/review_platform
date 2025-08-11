import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Grid,
  Card,
  CardContent,
  CardMedia,
  Button,
  Breadcrumbs,
  Link,
  Alert,
  CircularProgress,
  Chip,
  Divider,
  IconButton,
  Skeleton,
  TextField,
  Avatar
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  NavigateBefore as NavigateBeforeIcon,
  NavigateNext as NavigateNextIcon,
  ZoomIn as ZoomInIcon,
  ZoomOut as ZoomOutIcon,
  SmartToy as SmartToyIcon,
  CheckCircle as CheckCircleIcon,
  Add as AddIcon
} from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';

import { 
  getProjectDeckAnalysis,
  getSlideFeedback,
  addManualFeedback
} from '../services/api';
import api from '../services/api';
import { formatMarkdownText } from '../utils/markdownFormatter';

// Individual Feedback Bubble Component
const FeedbackBubble = ({ feedbackItem }) => {
  const getAvatarProps = () => {
    if (feedbackItem.feedback_type === 'ai_analysis') {
      return {
        text: 'HZ',
        backgroundColor: feedbackItem.has_issues ? 'primary.main' : 'success.main',
        bubbleColor: feedbackItem.has_issues ? '#f8f9ff' : '#f1f8e9',
        borderColor: feedbackItem.has_issues ? '#e3f2fd' : '#c8e6c9'
      };
    } else if (feedbackItem.feedback_type === 'gp_feedback') {
      return {
        text: 'GP',
        backgroundColor: 'secondary.main',
        bubbleColor: '#fdf4ff',
        borderColor: '#f3e8ff'
      };
    } else {
      return {
        text: 'SU',
        backgroundColor: 'info.main',
        bubbleColor: '#f0f9ff',
        borderColor: '#e0f2fe'
      };
    }
  };

  const avatarProps = getAvatarProps();
  
  // Handle "no issues" case for AI feedback
  const displayText = feedbackItem.feedback_text || 
    (feedbackItem.feedback_type === 'ai_analysis' && !feedbackItem.has_issues 
      ? 'No issues identified - this slide is clear and effective' 
      : '');

  return (
    <Box sx={{ 
      display: 'flex', 
      alignItems: 'flex-start', 
      mb: 2,
      gap: 1
    }}>
      <Avatar sx={{ 
        width: 32, 
        height: 32,
        backgroundColor: avatarProps.backgroundColor,
        fontSize: '0.75rem',
        fontWeight: 'bold'
      }}>
        {avatarProps.text}
      </Avatar>
      <Paper sx={{ 
        p: 2, 
        backgroundColor: avatarProps.bubbleColor,
        border: `1px solid ${avatarProps.borderColor}`,
        borderRadius: 2,
        flex: 1,
        position: 'relative'
      }}>
        <Box sx={{ 
          position: 'absolute',
          left: -8,
          top: 12,
          width: 0,
          height: 0,
          borderTop: '8px solid transparent',
          borderBottom: '8px solid transparent',
          borderRight: `8px solid ${avatarProps.bubbleColor}`
        }} />
        <Typography variant="body2" sx={{ lineHeight: 1.6 }}>
          {displayText}
        </Typography>
      </Paper>
    </Box>
  );
};

// Slide Feedback Display Component
const SlideFeedbackDisplay = ({ slideNumber, feedback, loading = false, projectId, deckId, currentUser, onFeedbackAdded }) => {
  const { t } = useTranslation(['deckViewer', 'common']);
  const [showAddFeedback, setShowAddFeedback] = useState(false);
  const [newFeedback, setNewFeedback] = useState('');
  const [submittingFeedback, setSubmittingFeedback] = useState(false);
  
  if (loading) {
    return (
      <Box sx={{ mb: 3 }}>
        <Typography variant="h6" sx={{ mb: 2, display: 'flex', alignItems: 'center' }}>
          <SmartToyIcon sx={{ mr: 1, color: 'primary.main' }} />
          Feedback
        </Typography>
        <Paper sx={{ p: 2, backgroundColor: 'grey.50' }}>
          <Skeleton variant="text" width="80%" />
          <Skeleton variant="text" width="60%" />
        </Paper>
      </Box>
    );
  }
  
  const handleAddFeedback = async () => {
    if (!newFeedback.trim()) return;
    
    setSubmittingFeedback(true);
    try {
      const feedbackData = {
        feedback_text: newFeedback,
        feedback_type: currentUser?.role === 'gp' ? 'gp_feedback' : 'startup_feedback'
      };
      
      await addManualFeedback(projectId, deckId, slideNumber, feedbackData);
      
      setNewFeedback('');
      setShowAddFeedback(false);
      
      // Refresh feedback data
      if (onFeedbackAdded) {
        onFeedbackAdded();
      }
      
    } catch (error) {
      console.error('Error submitting feedback:', error);
      // TODO: Show error message to user
    } finally {
      setSubmittingFeedback(false);
    }
  };
  
  return (
    <Box sx={{ mb: 3 }}>
      <Typography variant="h6" sx={{ mb: 2 }}>
        Feedback
      </Typography>
      
      {/* Display all feedback entries */}
      {Array.isArray(feedback) ? (
        feedback.map((feedbackItem, index) => (
          <FeedbackBubble key={index} feedbackItem={feedbackItem} />
        ))
      ) : feedback ? (
        <FeedbackBubble feedbackItem={feedback} />
      ) : null}
      
      {/* Add Feedback Section */}
      {!showAddFeedback ? (
        <Box sx={{ display: 'flex', justifyContent: 'flex-start' }}>
          <Button
            startIcon={<AddIcon />}
            onClick={() => setShowAddFeedback(true)}
            variant="outlined"
            size="small"
            sx={{ 
              borderColor: 'grey.300',
              color: 'text.secondary',
              '&:hover': {
                borderColor: 'primary.main',
                backgroundColor: 'primary.light'
              }
            }}
          >
            Add feedback
          </Button>
        </Box>
      ) : (
        <Box sx={{ 
          display: 'flex', 
          alignItems: 'flex-start', 
          gap: 1,
          mt: 2
        }}>
          <Avatar sx={{ 
            width: 32, 
            height: 32,
            backgroundColor: currentUser?.role === 'gp' ? 'secondary.main' : 'primary.main',
            fontSize: '0.875rem'
          }}>
            {currentUser?.role === 'gp' ? 'GP' : 'SU'}
          </Avatar>
          <Box sx={{ flex: 1 }}>
            <TextField
              fullWidth
              multiline
              rows={3}
              placeholder={`Add your feedback as ${currentUser?.role === 'gp' ? 'GP' : 'Startup'}...`}
              value={newFeedback}
              onChange={(e) => setNewFeedback(e.target.value)}
              variant="outlined"
              size="small"
              sx={{
                backgroundColor: 'white',
                '& .MuiOutlinedInput-root': {
                  borderRadius: 2
                }
              }}
            />
            <Box sx={{ display: 'flex', gap: 1, mt: 1, justifyContent: 'flex-end' }}>
              <Button
                size="small"
                onClick={() => {
                  setShowAddFeedback(false);
                  setNewFeedback('');
                }}
                disabled={submittingFeedback}
              >
                Cancel
              </Button>
              <Button
                size="small"
                variant="contained"
                onClick={handleAddFeedback}
                disabled={!newFeedback.trim() || submittingFeedback}
              >
                {submittingFeedback ? 'Adding...' : 'Add Feedback'}
              </Button>
            </Box>
          </Box>
        </Box>
      )}
    </Box>
  );
};

const DeckViewer = () => {
  const { t } = useTranslation(['deckViewer', 'common']);
  const navigate = useNavigate();
  const { projectId, deckId } = useParams();
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [currentSlide, setCurrentSlide] = useState(0);
  const [imageZoom, setImageZoom] = useState('fit'); // 'fit' for auto-fit, or number for manual zoom
  
  // Deck analysis data
  const [deckAnalysis, setDeckAnalysis] = useState(null);
  const [slides, setSlides] = useState([]);
  const [imageUrls, setImageUrls] = useState({});
  
  // Slide feedback data
  const [slideFeedback, setSlideFeedback] = useState({});
  const [feedbackLoading, setFeedbackLoading] = useState(false);
  
  const [breadcrumbs, setBreadcrumbs] = useState([
    { label: t('common:navigation.dashboard'), path: '/dashboard' },
    { label: t('navigation.projectDashboard'), path: `/project/${projectId}` },
    { label: t('title'), path: null }
  ]);

  useEffect(() => {
    loadDeckAnalysis();
  }, [projectId, deckId]);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyPress = (e) => {
      if (e.key === 'ArrowLeft' && currentSlide > 0) {
        handleSlideChange(currentSlide - 1);
      } else if (e.key === 'ArrowRight' && currentSlide < slides.length - 1) {
        handleSlideChange(currentSlide + 1);
      } else if (e.key === 'f' || e.key === 'F') {
        handleZoomFit();
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [currentSlide, slides.length]);

  const loadDeckAnalysis = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await getProjectDeckAnalysis(projectId, deckId);
      const analysisData = response.data || response;
      
      setDeckAnalysis(analysisData);
      setSlides(analysisData.slides || []);
      
      // Update breadcrumbs
      setBreadcrumbs([
        { label: t('common:navigation.dashboard'), path: '/dashboard' },
        { label: t('navigation.projectDashboard'), path: `/project/${projectId}` },
        { label: `${t('title')}: ${analysisData.deck_name}`, path: null }
      ]);
      
      // Load slide images
      loadSlideImages(analysisData.slides || []);
      
      // Load slide feedback
      loadSlideFeedback();
      
    } catch (err) {
      console.error('Error loading deck analysis:', err);
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to load deck analysis';
      
      // Handle the specific case where analysis is not ready yet
      if (errorMessage.includes('Analysis results not found') || errorMessage.includes('analysis not found')) {
        setError('This deck is still being processed. Please check back in a few minutes once the analysis is complete.');
      } else {
        setError(errorMessage);
      }
    } finally {
      setLoading(false);
    }
  };

  const loadSlideImages = async (slidesData) => {
    const imageUrlsTemp = {};
    
    for (const slide of slidesData) {
      if (slide.slide_image_path) {
        try {
          // Use standard slide naming pattern
          const filename = `slide_${slide.page_number}.jpg`;
          // Extract deck name from slide_image_path or use fallback
          let deckName = 'test-pitch-deck'; // Default for current test case
          if (slide.slide_image_path) {
            const pathParts = slide.slide_image_path.split('/');
            if (pathParts.length >= 2) {
              deckName = pathParts[pathParts.length - 2]; // Get parent folder name
            }
          }
          
          // Use correct document-based endpoint  
          const response = await api.get(`/projects/documents/${deckId}/slide-image/${filename}`, {
            responseType: 'blob'
          });
          
          const imageBlob = response.data;
          const imageUrl = URL.createObjectURL(imageBlob);
          imageUrlsTemp[slide.page_number] = imageUrl;
          
        } catch (err) {
          console.error(`Error loading image for slide ${slide.page_number}:`, err);
          
          // Fallback: try with slide_image_path if available
          if (slide.slide_image_path) {
            try {
              const pathParts = slide.slide_image_path.split('/');
              const deckName = pathParts[pathParts.length - 2];
              const filename = pathParts[pathParts.length - 1];
              
              const response = await api.get(`/projects/documents/${deckId}/slide-image/${filename}`, {
                responseType: 'blob'
              });
              
              const imageBlob = response.data;
              const imageUrl = URL.createObjectURL(imageBlob);
              imageUrlsTemp[slide.page_number] = imageUrl;
            } catch (fallbackErr) {
              console.error(`Fallback image loading also failed for slide ${slide.page_number}:`, fallbackErr);
            }
          }
        }
      }
    }
    
    setImageUrls(imageUrlsTemp);
  };

  const loadSlideFeedback = async () => {
    try {
      setFeedbackLoading(true);
      
      // Use authenticated endpoint
      const response = await getSlideFeedback(projectId, deckId);
      const feedbackData = response.data || response;
      
      // feedbackData.feedback is already keyed by slide number
      const feedbackBySlide = feedbackData.feedback || {};
      
      setSlideFeedback(feedbackBySlide);
      
    } catch (err) {
      console.error('Error loading slide feedback:', err);
      // Don't show error for feedback - it's optional
    } finally {
      setFeedbackLoading(false);
    }
  };

  const handleSlideChange = (slideIndex) => {
    setCurrentSlide(slideIndex);
    // Keep current zoom level when changing slides - don't reset
  };

  const handleNextSlide = () => {
    if (currentSlide < slides.length - 1) {
      handleSlideChange(currentSlide + 1);
    }
  };

  const handlePreviousSlide = () => {
    if (currentSlide > 0) {
      handleSlideChange(currentSlide - 1);
    }
  };

  const handleZoomIn = () => {
    setImageZoom(prev => {
      const currentZoom = prev === 'fit' ? 1 : prev;
      return Math.min(currentZoom + 0.2, 3);
    });
  };

  const handleZoomOut = () => {
    setImageZoom(prev => {
      const currentZoom = prev === 'fit' ? 1 : prev;
      return Math.max(currentZoom - 0.2, 0.5);
    });
  };

  const handleZoomFit = () => {
    setImageZoom('fit');
  };

  const SlideNavigationCard = ({ slide, index, isActive }) => (
    <Card 
      sx={{ 
        cursor: 'pointer',
        transition: 'all 0.2s',
        '&:hover': { 
          transform: 'translateY(-2px)',
          boxShadow: 3 
        },
        border: isActive ? 2 : 1,
        borderColor: isActive ? 'primary.main' : 'grey.300'
      }}
      onClick={() => handleSlideChange(index)}
    >
      <CardContent sx={{ p: 1.5 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 'bold', fontSize: '0.85rem' }}>
            {t('slideInfo.slideNumber', { number: slide.page_number })}
          </Typography>
        </Box>
        
        {imageUrls[slide.page_number] && (
          <Box sx={{ 
            width: '100%', 
            aspectRatio: '16/9', 
            mb: 1,
            overflow: 'hidden',
            borderRadius: 1,
            backgroundColor: 'grey.100'
          }}>
            <CardMedia
              component="img"
              image={imageUrls[slide.page_number]}
              alt={t('slideInfo.slideAlt', { number: slide.page_number })}
              sx={{ 
                width: '100%',
                height: '100%',
                objectFit: 'contain'
              }}
            />
          </Box>
        )}
        
        <Typography variant="body2" color="text.secondary" sx={{ 
          fontSize: '0.75rem',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          display: '-webkit-box',
          WebkitLineClamp: 2,
          WebkitBoxOrient: 'vertical',
          lineHeight: 1.2
        }}>
          {slide.description.replace(/\*\*(.*?)\*\*/g, '$1').substring(0, 80)}...
        </Typography>
      </CardContent>
    </Card>
  );

  const currentSlideData = slides[currentSlide];

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', mt: 4 }}>
        <CircularProgress />
        <Typography sx={{ ml: 2 }}>{t('messages.loading')}</Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
        <Button onClick={() => navigate(`/project/${projectId}`)}>
          {t('navigation.backToProject')}
        </Button>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <Button
          startIcon={<ArrowBackIcon />}
          onClick={() => navigate(`/project/${projectId}`)}
          sx={{ mr: 2 }}
        >
          {t('navigation.backToProject')}
        </Button>
        <Typography variant="h4">
          {t('title')}
        </Typography>
      </Box>

      {/* Breadcrumbs */}
      <Breadcrumbs sx={{ mb: 3 }}>
        {breadcrumbs.map((crumb, index) => (
          crumb.path ? (
            <Link 
              key={index} 
              component="button" 
              variant="body2" 
              onClick={() => {
                if (crumb.path === '/dashboard') {
                  const user = JSON.parse(localStorage.getItem('user'));
                  if (user?.role === 'gp') {
                    navigate('/dashboard/gp');
                  } else {
                    navigate('/dashboard');
                  }
                } else {
                  navigate(crumb.path);
                }
              }}
              sx={{ textDecoration: 'none' }}
            >
              {crumb.label}
            </Link>
          ) : (
            <Typography key={index} variant="body2" color="text.primary">
              {crumb.label}
            </Typography>
          )
        ))}
      </Breadcrumbs>

      {/* Deck Info */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box>
            <Typography variant="h6">
              {deckAnalysis?.deck_name}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {t('slideInfo.slideCount', { count: slides.length })} • {t('slideInfo.project')}: {projectId}
            </Typography>
          </Box>
          
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Chip 
              label={`${currentSlide + 1} / ${slides.length}`} 
              color="primary"
              size="small"
            />
            <Chip 
              label={deckAnalysis?.processing_metadata?.vision_model || 'AI Analyzed'} 
              variant="outlined"
              size="small"
            />
          </Box>
        </Box>
      </Paper>

      <Grid container spacing={3}>
        {/* Slide Navigation */}
        <Grid item xs={12} md={3}>
          <Paper sx={{ p: 2, height: 'fit-content', maxHeight: '80vh', overflow: 'auto' }}>
            <Typography variant="h6" sx={{ mb: 2, fontSize: '1.1rem' }}>
              {t('sections.slides', { count: slides.length })}
            </Typography>
            
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
              {slides.map((slide, index) => (
                <SlideNavigationCard 
                  key={slide.page_number} 
                  slide={slide} 
                  index={index}
                  isActive={index === currentSlide}
                />
              ))}
            </Box>
          </Paper>
        </Grid>

        {/* Main Slide View */}
        <Grid item xs={12} md={9}>
          <Paper sx={{ p: 2 }}>
            {currentSlideData && (
              <>
                {/* Slide Controls */}
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <IconButton
                      onClick={handlePreviousSlide}
                      disabled={currentSlide === 0}
                      size="small"
                    >
                      <NavigateBeforeIcon />
                    </IconButton>
                    
                    <Typography variant="h6">
                      {t('slideInfo.slideNumber', { number: currentSlideData.page_number })}
                    </Typography>
                    
                    <IconButton
                      onClick={handleNextSlide}
                      disabled={currentSlide === slides.length - 1}
                      size="small"
                    >
                      <NavigateNextIcon />
                    </IconButton>
                  </Box>
                  
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <IconButton 
                      onClick={handleZoomOut} 
                      size="small"
                      disabled={imageZoom === 'fit' || imageZoom <= 0.5}
                      title={t('controls.zoomOut')}
                    >
                      <ZoomOutIcon />
                    </IconButton>
                    <Typography variant="body2" sx={{ minWidth: '70px', textAlign: 'center' }}>
                      {imageZoom === 'fit' ? t('controls.fit') : `${Math.round(imageZoom * 100)}%`}
                    </Typography>
                    <IconButton 
                      onClick={handleZoomIn} 
                      size="small"
                      disabled={imageZoom === 'fit' ? false : imageZoom >= 3}
                      title={t('controls.zoomIn')}
                    >
                      <ZoomInIcon />
                    </IconButton>
                    <Button 
                      onClick={handleZoomFit} 
                      size="small" 
                      variant="outlined"
                      sx={{ ml: 1, fontSize: '0.75rem', minWidth: 'auto', px: 1 }}
                      title={t('shortcuts.fitToContainer')}
                    >
                      {t('controls.fit')}
                    </Button>
                  </Box>
                </Box>

                <Divider sx={{ mb: 3 }} />

                {/* Slide Image */}
                <Box sx={{ 
                  position: 'relative',
                  width: '100%',
                  aspectRatio: '16/9',
                  mb: 3,
                  overflow: imageZoom === 'fit' ? 'hidden' : 'auto',
                  backgroundColor: 'grey.50',
                  borderRadius: 1,
                  border: '1px solid',
                  borderColor: 'grey.200'
                }}>
                  {imageUrls[currentSlideData.page_number] ? (
                    <img
                      src={imageUrls[currentSlideData.page_number]}
                      alt={t('slideInfo.slideAlt', { number: currentSlideData.page_number })}
                      style={{
                        position: 'absolute',
                        top: '50%',
                        left: '50%',
                        transform: imageZoom === 'fit' 
                          ? 'translate(-50%, -50%)' 
                          : `translate(-50%, -50%) scale(${imageZoom})`,
                        maxWidth: imageZoom === 'fit' ? '100%' : 'none',
                        maxHeight: imageZoom === 'fit' ? '100%' : 'none',
                        width: imageZoom === 'fit' ? 'auto' : '100%',
                        height: imageZoom === 'fit' ? 'auto' : 'auto',
                        objectFit: 'contain',
                        transition: 'transform 0.2s ease-in-out',
                        cursor: imageZoom !== 'fit' ? 'grab' : 'default'
                      }}
                    />
                  ) : (
                    <Box sx={{ 
                      position: 'absolute',
                      top: '50%',
                      left: '50%',
                      transform: 'translate(-50%, -50%)'
                    }}>
                      <Skeleton 
                        variant="rectangular" 
                        width={400} 
                        height={225} 
                        sx={{ borderRadius: 1 }} 
                      />
                    </Box>
                  )}
                </Box>

                {/* Slide Feedback */}
                <SlideFeedbackDisplay 
                  slideNumber={currentSlideData.page_number}
                  feedback={slideFeedback[currentSlideData.page_number]}
                  loading={feedbackLoading}
                  projectId={projectId}
                  deckId={deckId}
                  currentUser={JSON.parse(localStorage.getItem('user'))}
                  onFeedbackAdded={loadSlideFeedback}
                />

                <Divider sx={{ mb: 3 }} />

                {/* AI Analysis */}
                <Box>
                  <Typography variant="h6" sx={{ mb: 2 }}>
                    {t('sections.aiAnalysis')}
                  </Typography>
                  
                  <Paper sx={{ p: 2, backgroundColor: 'grey.50' }}>
                    <Box>
                      {formatMarkdownText(currentSlideData.description)}
                    </Box>
                  </Paper>
                </Box>
              </>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default DeckViewer;