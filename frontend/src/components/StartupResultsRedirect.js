import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Box, CircularProgress, Typography, Alert } from '@mui/material';
import api from '../services/api';

/**
 * Redirect component that maps old startup results URLs to new project-based URLs
 * 
 * Old: /results/{pitchDeckId}
 * New: /project/{companyId}/results/{deckId}
 * 
 * This component looks up the project that was auto-created from the pitch deck
 * and redirects to the modern ProjectResults viewer.
 */
const StartupResultsRedirect = () => {
  const { pitchDeckId } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const findProjectForPitchDeck = async () => {
      try {
        setLoading(true);
        setError(null);

        // First, get the pitch deck info to find the company_id
        const deckResponse = await api.get(`/documents/processing-status/${pitchDeckId}`);
        const deckData = deckResponse.data;
        
        if (!deckData.company_id) {
          throw new Error('Company ID not found for this pitch deck');
        }

        const companyId = deckData.company_id;

        // Now find the project that was auto-created for this company
        const projectsResponse = await api.get(`/companies/${companyId}/projects`);
        const projects = projectsResponse.data || [];

        // Look for a project that was created from this pitch deck
        let targetProject = projects.find(project => {
          try {
            const metadata = typeof project.project_metadata === 'string' 
              ? JSON.parse(project.project_metadata) 
              : project.project_metadata;
            return metadata?.pitch_deck_id === parseInt(pitchDeckId);
          } catch {
            return false;
          }
        });

        // If no specific project found, use the first active project for this company
        if (!targetProject) {
          targetProject = projects.find(project => project.is_active);
        }

        if (!targetProject) {
          throw new Error('No project found for this pitch deck. The project may not have been created yet.');
        }

        // Redirect to the modern project results page
        // Use pitchDeckId as deckId since they should be the same in most cases
        navigate(`/project/${companyId}/results/${pitchDeckId}`, { replace: true });

      } catch (err) {
        console.error('Error finding project for pitch deck:', err);
        setError(err.response?.data?.detail || err.message || 'Failed to find project for this pitch deck');
        setLoading(false);
      }
    };

    if (pitchDeckId) {
      findProjectForPitchDeck();
    }
  }, [pitchDeckId, navigate]);

  if (loading) {
    return (
      <Box sx={{ 
        display: 'flex', 
        flexDirection: 'column', 
        alignItems: 'center', 
        justifyContent: 'center', 
        minHeight: '60vh',
        gap: 2 
      }}>
        <CircularProgress size={60} />
        <Typography variant="h6">
          Loading your analysis results...
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Redirecting to the modern results viewer
        </Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 3, maxWidth: 600, mx: 'auto', mt: 4 }}>
        <Alert severity="error" sx={{ mb: 2 }}>
          <Typography variant="h6" gutterBottom>
            Unable to Load Results
          </Typography>
          <Typography variant="body2">
            {error}
          </Typography>
        </Alert>
        <Typography variant="body2" color="text.secondary">
          Please try accessing your results from the dashboard, or contact support if the problem persists.
        </Typography>
      </Box>
    );
  }

  return null; // Should not reach here due to redirect
};

export default StartupResultsRedirect;