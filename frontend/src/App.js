
import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ThemeProvider, CssBaseline } from '@mui/material';
import theme from './utils/theme';
import Navigation from './components/Navigation';
import Login from './pages/Login';
import Register from './pages/Register';
import StartupDashboard from './pages/StartupDashboard';
import GPDashboard from './pages/GPDashboard';
import Review from './pages/Review';

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <BrowserRouter>
        <Navigation />
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/dashboard/startup" element={<StartupDashboard />} />
          <Route path="/dashboard/gp" element={<GPDashboard />} />
          <Route path="/review/:id" element={<Review />} />
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  );
}

export default App;
