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
  Skeleton
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  NavigateBefore as NavigateBeforeIcon,
  NavigateNext as NavigateNextIcon,
  ZoomIn as ZoomInIcon,
  ZoomOut as ZoomOutIcon
} from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';

import { 
  getProjectDeckAnalysis,
  api
} from '../services/api';

const DeckViewer = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { companyId, deckId } = useParams();
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [currentSlide, setCurrentSlide] = useState(0);
  const [imageZoom, setImageZoom] = useState(1);
  
  // Deck analysis data
  const [deckAnalysis, setDeckAnalysis] = useState(null);
  const [slides, setSlides] = useState([]);
  const [imageUrls, setImageUrls] = useState({});
  
  const [breadcrumbs, setBreadcrumbs] = useState([
    { label: t('navigation.dashboard'), path: '/dashboard' },
    { label: 'Project Dashboard', path: `/project/${companyId}` },
    { label: 'Deck Viewer', path: null }
  ]);

  useEffect(() => {
    loadDeckAnalysis();
  }, [companyId, deckId]);

  const loadDeckAnalysis = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await getProjectDeckAnalysis(companyId, deckId);
      const analysisData = response.data || response;
      
      setDeckAnalysis(analysisData);
      setSlides(analysisData.slides || []);
      
      // Update breadcrumbs
      setBreadcrumbs([
        { label: t('navigation.dashboard'), path: '/dashboard' },
        { label: 'Project Dashboard', path: `/project/${companyId}` },
        { label: `Deck Viewer: ${analysisData.deck_name}`, path: null }
      ]);
      
      // Load slide images
      loadSlideImages(analysisData.slides || []);
      
    } catch (err) {
      console.error('Error loading deck analysis:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to load deck analysis');
    } finally {
      setLoading(false);
    }
  };

  const loadSlideImages = async (slidesData) => {
    const imageUrlsTemp = {};
    
    for (const slide of slidesData) {
      if (slide.slide_image_path) {
        try {
          // Extract filename from path
          const pathParts = slide.slide_image_path.split('/');
          const deckName = pathParts[pathParts.length - 2];
          const filename = pathParts[pathParts.length - 1];
          
          // Create blob URL for image
          const response = await api.get(`/projects/${companyId}/slide-image/${deckName}/${filename}`, {
            responseType: 'blob'
          });
          
          const imageBlob = response.data;
          const imageUrl = URL.createObjectURL(imageBlob);
          imageUrlsTemp[slide.page_number] = imageUrl;
          
        } catch (err) {
          console.error(`Error loading image for slide ${slide.page_number}:`, err);
        }
      }
    }
    
    setImageUrls(imageUrlsTemp);
  };

  const handleSlideChange = (slideIndex) => {
    setCurrentSlide(slideIndex);
    setImageZoom(1); // Reset zoom when changing slides
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
    setImageZoom(prev => Math.min(prev + 0.2, 3));
  };

  const handleZoomOut = () => {
    setImageZoom(prev => Math.max(prev - 0.2, 0.5));
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
      <CardContent sx={{ p: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>
            Slide {slide.page_number}
          </Typography>
        </Box>
        
        {imageUrls[slide.page_number] && (
          <CardMedia
            component="img"
            height="80"
            image={imageUrls[slide.page_number]}
            alt={`Slide ${slide.page_number}`}
            sx={{ objectFit: 'contain', mb: 1 }}
          />
        )}
        
        <Typography variant="body2" color="text.secondary" sx={{ 
          fontSize: '0.8rem',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          display: '-webkit-box',
          WebkitLineClamp: 2,
          WebkitBoxOrient: 'vertical'
        }}>
          {slide.description.substring(0, 100)}...
        </Typography>
      </CardContent>
    </Card>
  );

  const currentSlideData = slides[currentSlide];

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
        <Button onClick={() => navigate(`/project/${companyId}`)}>
          Back to Project Dashboard
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
          onClick={() => navigate(`/project/${companyId}`)}
          sx={{ mr: 2 }}
        >
          Back to Project
        </Button>
        <Typography variant="h4">
          Deck Viewer
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
              onClick={() => navigate(crumb.path)}
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
              {slides.length} slides • Company: {companyId}
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
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" sx={{ mb: 2 }}>
              Slides
            </Typography>
            
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
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
                      Slide {currentSlideData.page_number}
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
                    <IconButton onClick={handleZoomOut} size="small">
                      <ZoomOutIcon />
                    </IconButton>
                    <Typography variant="body2" sx={{ minWidth: '50px', textAlign: 'center' }}>
                      {Math.round(imageZoom * 100)}%
                    </Typography>
                    <IconButton onClick={handleZoomIn} size="small">
                      <ZoomInIcon />
                    </IconButton>
                  </Box>
                </Box>

                <Divider sx={{ mb: 3 }} />

                {/* Slide Image */}
                <Box sx={{ 
                  display: 'flex', 
                  justifyContent: 'center', 
                  mb: 3,
                  overflow: 'auto',
                  maxHeight: '500px'
                }}>
                  {imageUrls[currentSlideData.page_number] ? (
                    <img
                      src={imageUrls[currentSlideData.page_number]}
                      alt={`Slide ${currentSlideData.page_number}`}
                      style={{
                        maxWidth: '100%',
                        height: 'auto',
                        transform: `scale(${imageZoom})`,
                        transition: 'transform 0.2s ease-in-out'
                      }}
                    />
                  ) : (
                    <Skeleton variant="rectangular" width={400} height={300} />
                  )}
                </Box>

                <Divider sx={{ mb: 3 }} />

                {/* AI Analysis */}
                <Box>
                  <Typography variant="h6" sx={{ mb: 2 }}>
                    AI Analysis
                  </Typography>
                  
                  <Paper sx={{ p: 2, backgroundColor: 'grey.50' }}>
                    <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
                      {currentSlideData.description}
                    </Typography>
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