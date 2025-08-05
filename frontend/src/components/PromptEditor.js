import React, { useState, useEffect } from 'react';
import { Box, Typography, Button, Alert, CircularProgress } from '@mui/material';
import { useTranslation } from 'react-i18next';
import { updatePipelinePrompt, resetPipelinePrompt } from '../services/api';

const getPromptTitle = (stageName, t) => {
  const titleMap = {
    'image_analysis': t('labels.imageAnalysisPrompt'),
    'offering_extraction': t('labels.companyOfferingPrompt'),
    'startup_name_extraction': 'Startup Name Extraction Prompt',
    'scoring_analysis': 'Question Scoring & Rationale Prompt'
  };
  return titleMap[stageName] || stageName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()) + ' Prompt';
};

const PromptEditor = ({ initialPrompt, stageName, onSave }) => {
  const { t } = useTranslation('templates');
  const [text, setText] = useState(initialPrompt || '');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    setText(initialPrompt || '');
  }, [initialPrompt]);

  const handleSave = async () => {
    try {
      setLoading(true);
      setError(null);
      await updatePipelinePrompt(stageName, text);
      onSave?.(text);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save prompt');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await resetPipelinePrompt(stageName);
      const defaultPrompt = response.data?.default_prompt || '';
      setText(defaultPrompt);
      onSave?.(defaultPrompt);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to reset prompt');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box>
      <Typography variant="h6" sx={{ mb: 2 }}>
        {getPromptTitle(stageName, t)}
      </Typography>
      
      {stageName === 'scoring_analysis' && (
        <Alert severity="info" sx={{ mb: 2 }}>
          <Typography variant="subtitle2" sx={{ mb: 1 }}>
            Available Template Variables:
          </Typography>
          <Typography variant="body2" component="div" sx={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>
            • <strong>{`{question_text}`}</strong> - The specific question being scored<br/>
            • <strong>{`{scoring_criteria}`}</strong> - The scoring criteria for this question<br/>
            • <strong>{`{response}`}</strong> - The AI's analysis response to the question<br/>
            • <strong>{`{pitch_deck_text}`}</strong> - The full text content of the pitch deck
          </Typography>
          <Typography variant="body2" sx={{ mt: 1, fontStyle: 'italic' }}>
            These variables will be automatically replaced with actual content during processing.
          </Typography>
        </Alert>
      )}
      
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        disabled={loading}
        rows={8}
        style={{
          width: '100%',
          fontFamily: 'monospace',
          fontSize: '14px',
          padding: '12px',
          border: '1px solid #ccc',
          borderRadius: '4px',
          resize: 'vertical',
          outline: 'none',
          backgroundColor: loading ? '#f5f5f5' : 'white'
        }}
      />

      <Box sx={{ display: 'flex', gap: 2, mt: 2 }}>
        <Button
          variant="contained"
          onClick={handleSave}
          disabled={loading || !text.trim()}
          startIcon={loading ? <CircularProgress size={20} /> : null}
        >
          {loading ? t('pipeline.saving') : t('pipeline.savePrompt')}
        </Button>
        <Button
          variant="outlined"
          onClick={handleReset}
          disabled={loading}
          color="secondary"
        >
          {t('pipeline.resetPrompt')}
        </Button>
      </Box>
    </Box>
  );
};

export default PromptEditor;