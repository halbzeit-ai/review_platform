
import React from 'react';
import { Container, Typography, Paper, Button, TextField } from '@mui/material';
import { useParams } from 'react-router-dom';

function Review() {
  const { id } = useParams();

  return (
    <Container maxWidth="lg" sx={{ mt: 4 }}>
      <Typography variant="h4" gutterBottom>Review #{id}</Typography>
      <Paper sx={{ p: 3 }}>
        <Typography variant="h6">Review Content</Typography>
        <TextField
          fullWidth
          multiline
          rows={4}
          margin="normal"
          label="Add Question"
        />
        <Button variant="contained" color="primary" sx={{ mt: 2 }}>
          Submit Question
        </Button>
      </Paper>
    </Container>
  );
}

export default Review;
