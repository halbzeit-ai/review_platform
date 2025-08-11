
import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, CssBaseline } from '@mui/material';
import theme from './utils/theme';
import Navigation from './components/Navigation';
import Login from './pages/Login';
import Register from './pages/Register';
import VerifyEmail from './pages/VerifyEmail';
import ResetPassword from './pages/ResetPassword';
import ChangePassword from './pages/ChangePassword';
import GPDashboard from './pages/GPDashboard';
import UserManagement from './pages/UserManagement';
import Review from './pages/Review';
import StartupResultsRedirect from './components/StartupResultsRedirect';
import ConfigPage from './pages/ConfigPage';
import TemplateManagement from './pages/TemplateManagement';
import DojoManagement from './pages/DojoManagement';
import ProjectDashboard from './pages/ProjectDashboard';
import DeckViewer from './pages/DeckViewer';
import ProjectResultsPage from './pages/ProjectResultsPage';
import Profile from './pages/Profile';
// Removed: StartupDashboard - legacy component archived
import DashboardRedirect from './components/DashboardRedirect';
import StartupJourney from './pages/StartupJourney';
import InvitationAcceptance from './pages/InvitationAcceptance';

function App() {
  const [user, setUser] = React.useState(null);
  
  React.useEffect(() => {
    try {
      const userData = JSON.parse(localStorage.getItem('user') || 'null');
      setUser(userData);
    } catch (error) {
      localStorage.removeItem('user');
    }
  }, []);

  const isAuthPage = ['/login', '/register', '/verify-email', '/reset-password', '/change-password', '/invitation'].some(path => 
    window.location.pathname.startsWith(path)
  );

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <BrowserRouter>
        {!isAuthPage && <Navigation />}
        <Routes>
          <Route path="/" element={<Navigate to="/login" replace />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/verify-email" element={<VerifyEmail />} />
          <Route path="/reset-password" element={<ResetPassword />} />
          <Route path="/change-password" element={<ChangePassword />} />
          <Route path="/dashboard" element={<DashboardRedirect />} />
          {/* Removed: /dashboard/startup route - legacy component archived */}
          <Route path="/dashboard/gp" element={<GPDashboard />} />
          <Route path="/gp-dashboard" element={<GPDashboard />} />
          <Route path="/users" element={<UserManagement />} />
          <Route path="/review/:id" element={<Review />} />
          <Route path="/results/:pitchDeckId" element={<StartupResultsRedirect />} />
          <Route path="/config" element={<ConfigPage />} />
          <Route path="/templates" element={<TemplateManagement />} />
          <Route path="/dojo" element={<DojoManagement />} />
          <Route path="/project/:projectId" element={<ProjectDashboard />} />
          <Route path="/project/:projectId/deck-viewer/:deckId" element={<DeckViewer />} />
          <Route path="/project/:projectId/results/:deckId" element={<ProjectResultsPage />} />
          <Route path="/funding-journey" element={<StartupJourney />} />
          <Route path="/funding-journey/:projectId" element={<StartupJourney />} />
          <Route path="/admin/project/:projectId/startup-view" element={<ProjectDashboard />} />
          <Route path="/invitation/:token" element={<InvitationAcceptance />} />
          <Route path="/profile" element={<Profile />} />
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  );
}

export default App;
