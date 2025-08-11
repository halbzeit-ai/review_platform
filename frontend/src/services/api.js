
import axios from 'axios';
import { API_CONFIG } from '../config/environment';

const api = axios.create({
  baseURL: API_CONFIG.BASE_URL,
  timeout: API_CONFIG.TIMEOUT,
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  // Check for regular user token first
  let user = JSON.parse(localStorage.getItem('user'));
  
  // If no regular user, check for temporary user (password change flow)
  if (!user) {
    user = JSON.parse(localStorage.getItem('tempUser'));
  }
  
  if (user?.token) {
    config.headers.Authorization = `Bearer ${user.token}`;
  }
  return config;
});

// Add response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (API_CONFIG.IS_DEVELOPMENT) {
      console.error('API Error:', error.response?.status, error.response?.data || error.message);
    }
    
    // Handle common production errors
    if (error.response?.status === 401) {
      // Token expired or invalid
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    
    return Promise.reject(error);
  }
);

export const login = (email, password) => 
  api.post('/auth/login', { email, password });

export const register = (email, password, companyName, role) =>
  api.post('/auth/register', { email, password, company_name: companyName, role });

export const forgotPassword = (email) =>
  api.post('/auth/forgot-password', { email });

export const resetPassword = (token, newPassword) =>
  api.post('/auth/reset-password', { token, new_password: newPassword });

export const changePassword = (currentPassword, newPassword) =>
  api.post('/auth/change-password', { current_password: currentPassword, new_password: newPassword });

export const changeForcedPassword = (newPassword) =>
  api.post('/auth/change-password-forced', { new_password: newPassword });

export const uploadPitchDeck = (file) => {
  const formData = new FormData();
  formData.append('file', file);
  return api.post('/robust/documents/upload', formData);
};

export const getReview = (id) =>
  api.get(`/reviews/${id}`);

export const submitQuestion = (reviewId, question) =>
  api.post(`/reviews/${reviewId}/questions`, { question_text: question });

export const submitAnswer = (questionId, answer) =>
  api.post(`/questions/${questionId}/answer`, { answer_text: answer });

export const getAllUsers = () => 
  api.get('/auth/users');

export const getPendingInvitations = () =>
  api.get('/auth/pending-invitations');

export const getPitchDecks = () => api.get('/decks');

export const updateUserRole = (userEmail, newRole) => 
  api.post('/auth/update-role', { user_email: userEmail, new_role: newRole });

export const getLanguagePreference = () =>
  api.get('/auth/language-preference');

export const updateLanguagePreference = (language) =>
  api.post('/auth/language-preference', { preferred_language: language });

export const deleteUser = (userEmail) =>
  api.delete(`/auth/delete-user?user_email=${encodeURIComponent(userEmail)}`);

// Healthcare Templates API
export const getHealthcareSectors = () =>
  api.get('/healthcare-templates/sectors');

export const getSectorTemplates = (sectorId) =>
  api.get(`/healthcare-templates/sectors/${sectorId}/templates`);

export const getTemplateDetails = (templateId) =>
  api.get(`/healthcare-templates/templates/${templateId}`);

export const classifyStartup = (companyOffering, manualClassification = null) =>
  api.post('/healthcare-templates/classify', {
    company_offering: companyOffering,
    manual_classification: manualClassification
  });

export const customizeTemplate = (customizationData) =>
  api.post('/healthcare-templates/customize-template', customizationData);

export const getMyCustomizations = () =>
  api.get('/healthcare-templates/my-customizations');

export const getPerformanceMetrics = () =>
  api.get('/healthcare-templates/performance-metrics');

export const updateTemplate = (templateId, templateData) =>
  api.put(`/healthcare-templates/templates/${templateId}`, templateData);
export const updateTemplateComplete = (templateId, completeTemplateData) =>
  api.put(`/healthcare-templates/templates/${templateId}/complete`, completeTemplateData);

export const addChapterToTemplate = (templateId, chapterData) =>
  api.post(`/healthcare-templates/templates/${templateId}/chapters`, chapterData);

export const deleteTemplate = (templateId) =>
  api.delete(`/healthcare-templates/templates/${templateId}`);

export const deleteCustomization = (customizationId) =>
  api.delete(`/healthcare-templates/customizations/${customizationId}`);

// Pipeline Configuration API
export const getPipelinePrompts = () =>
  api.get('/pipeline/prompts');

export const getPipelinePromptByStage = (stageName) =>
  api.get(`/pipeline/prompts/${stageName}`);

export const updatePipelinePrompt = (stageName, promptText) =>
  api.put(`/pipeline/prompts/${stageName}`, { prompt_text: promptText });

export const resetPipelinePrompt = (stageName) =>
  api.post(`/pipeline/prompts/${stageName}/reset`);

export const getPipelineStages = () =>
  api.get('/pipeline/stages');

// Project-based API
export const getProjectDeckAnalysis = (projectId, deckId) =>
  api.get(`/projects/${projectId}/deck-analysis/${deckId}`);

export const getProjectResults = (projectId, deckId) =>
  api.get(`/projects/${projectId}/results/${deckId}`);

export const getProjectUploads = (projectId) =>
  api.get(`/projects/${projectId}/uploads`);

export const getSlideImage = (projectId, deckName, slideFilename) =>
  api.get(`/projects/${projectId}/slide-image/${deckName}/${slideFilename}`, {
    responseType: 'blob'
  });

export const deleteDeck = (projectId, deckId) =>
  api.delete(`/projects/${projectId}/deck/${deckId}`);

export const cleanupOrphanedDecks = () =>
  api.delete('/decks/cleanup-orphaned');

export const getCompanyInfo = () =>
  api.get('/auth/company-info');

export const getDashboardInfo = () =>
  api.get('/auth/dashboard-info');

export const getUserProjects = () =>
  api.get('/auth/user-projects');

// Project Management API
export const getAllProjects = (includeTestData = false, limit = 100, offset = 0) =>
  api.get(`/project-management/all-projects?include_test_data=${includeTestData}&limit=${limit}&offset=${offset}`);

export const getMyProjects = (limit = 100, offset = 0) =>
  api.get(`/project-management/my-projects?limit=${limit}&offset=${offset}`);

// GP Admin: Get project decks by project ID (for any project)
export const getProjectDecks = (projectId) =>
  api.get(`/project-management/projects/${projectId}/decks`);

// Funding Stages API
export const getStageTemplates = () =>
  api.get('/funding-stages/templates');

export const createStageTemplate = (templateData) =>
  api.post('/funding-stages/templates', templateData);

export const getProjectJourney = (projectId) =>
  api.get(`/funding-stages/projects/${projectId}/journey`);

export const updateStageStatus = (projectId, stageId, statusData) =>
  api.put(`/funding-stages/projects/${projectId}/stages/${stageId}/status`, statusData);

export const reinitializeProjectStages = (projectId) =>
  api.post(`/funding-stages/projects/${projectId}/reinitialize-stages`);

// Invitation API
export const sendProjectInvitations = (projectId, invitationData) =>
  api.post(`/projects/${projectId}/invite`, invitationData);

export const getInvitationDetails = (token) =>
  api.get(`/invitation/${token}`);

export const acceptInvitation = (token, acceptData) =>
  api.post(`/invitation/${token}/accept`, acceptData);

export const getProjectInvitations = (projectId) =>
  api.get(`/projects/${projectId}/invitations`);

export const cancelInvitation = (invitationId) =>
  api.delete(`/invitation/${invitationId}`);

// Project Creation API
export const createProject = (projectData) =>
  api.post('/projects/create', projectData);

// Processing Progress API
export const getProcessingProgress = (pitchDeckId) =>
  api.get(`/robust/documents/processing-progress/${pitchDeckId}`);

// GP Invitation API
export const inviteGP = (inviteData) =>
  api.post('/auth/invite-gp', inviteData);

// Slide Feedback API
export const getSlideFeedback = (companyId, deckId) =>
  api.get(`/feedback/projects/${companyId}/decks/${deckId}/slide-feedback`);

export const getSlideSpecificFeedback = (companyId, deckId, slideNumber) =>
  api.get(`/feedback/projects/${companyId}/decks/${deckId}/slides/${slideNumber}/feedback`);

export const getDeckFeedbackSummary = (companyId, deckId) =>
  api.get(`/feedback/projects/${companyId}/decks/${deckId}/feedback-summary`);

export const addManualFeedback = (companyId, deckId, slideNumber, feedbackData) =>
  api.post(`/feedback/projects/${companyId}/decks/${deckId}/slides/${slideNumber}/feedback`, feedbackData);

// Template Configuration API
export const getTemplateConfig = () =>
  api.get('/healthcare-templates/template-config');

export const saveTemplateConfig = (config) =>
  api.post('/healthcare-templates/template-config', config);

// Extraction Results API
export const getExtractionResults = () =>
  api.get('/projects/extraction-results');

// Orphaned Projects API
export const getOrphanedProjects = () =>
  api.get('/project-management/orphaned-projects');

// Project Deletion API
export const deleteProject = (projectId) =>
  api.delete(`/project-management/projects/${projectId}`);

export default api;
