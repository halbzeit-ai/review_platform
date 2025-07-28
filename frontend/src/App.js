
import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ThemeProvider, CssBaseline } from '@mui/material';
import theme from './utils/theme';
import Navigation from './components/Navigation';
import Login from './pages/Login';
import Register from './pages/Register';
import VerifyEmail from './pages/VerifyEmail';
import ResetPassword from './pages/ResetPassword';
import GPDashboard from './pages/GPDashboard';
import UserManagement from './pages/UserManagement';
import Review from './pages/Review';
import ResultsPage from './pages/ResultsPage';
import ConfigPage from './pages/ConfigPage';
import TemplateManagement from './pages/TemplateManagement';
import DojoManagement from './pages/DojoManagement';
import ProjectDashboard from './pages/ProjectDashboard';
import DeckViewer from './pages/DeckViewer';
import ProjectResultsPage from './pages/ProjectResultsPage';
import Profile from './pages/Profile';
import StartupDashboardRedirect from './components/StartupDashboardRedirect';
import DashboardRedirect from './components/DashboardRedirect';
import StartupJourney from './pages/StartupJourney';

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <BrowserRouter>
        <Navigation />
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/verify-email" element={<VerifyEmail />} />
          <Route path="/reset-password" element={<ResetPassword />} />
          <Route path="/dashboard" element={<DashboardRedirect />} />
          <Route path="/dashboard/startup" element={<StartupDashboardRedirect />} />
          <Route path="/dashboard/gp" element={<GPDashboard />} />
          <Route path="/gp-dashboard" element={<GPDashboard />} />
          <Route path="/users" element={<UserManagement />} />
          <Route path="/review/:id" element={<Review />} />
          <Route path="/results/:pitchDeckId" element={<ResultsPage />} />
          <Route path="/config" element={<ConfigPage />} />
          <Route path="/templates" element={<TemplateManagement />} />
          <Route path="/dojo" element={<DojoManagement />} />
          <Route path="/project/:companyId" element={<ProjectDashboard />} />
          <Route path="/project/:companyId/deck-viewer/:deckId" element={<DeckViewer />} />
          <Route path="/project/:companyId/results/:deckId" element={<ProjectResultsPage />} />
          <Route path="/funding-journey" element={<StartupJourney />} />
          <Route path="/funding-journey/:projectId" element={<StartupJourney />} />
          <Route path="/admin/project/:projectId/startup-view" element={<ProjectDashboard />} />
          <Route path="/profile" element={<Profile />} />
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  );
}

export default App;
