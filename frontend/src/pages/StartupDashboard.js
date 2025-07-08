
import React from 'react';
import { Container, Paper, Typography, Button, Grid } from '@mui/material';
import { Upload } from '@mui/icons-material';

function StartupDashboard() {
  const handleFileUpload = (event) => {
    const file = event.target.files[0];
    // Implement file upload logic
  };

  return (
    <Container maxWidth="lg" sx={{ mt: 4 }}>
      <Typography variant="h4" gutterBottom>Dashboard</Typography>
      <Grid container spacing={3}>
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <input
              accept="application/pdf"
              style={{ display: 'none' }}
              id="pitch-deck-upload"
              type="file"
              onChange={handleFileUpload}
            />
            <label htmlFor="pitch-deck-upload">
              <Button
                variant="contained"
                component="span"
                startIcon={<Upload />}
              >
                Upload Pitch Deck
              </Button>
            </label>
          </Paper>
        </Grid>
      </Grid>
    </Container>
  );
}

export default StartupDashboard;
