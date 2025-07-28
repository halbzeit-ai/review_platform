
import axios from 'axios';

const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || '/api',
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const user = JSON.parse(localStorage.getItem('user'));
  if (user?.token) {
    config.headers.Authorization = `Bearer ${user.token}`;
  }
  return config;
});

export const login = (email, password) => 
  api.post('/auth/login', { email, password });

export const register = (email, password, companyName, role) =>
  api.post('/auth/register', { email, password, company_name: companyName, role });

export const forgotPassword = (email) =>
  api.post('/auth/forgot-password', { email });

export const resetPassword = (token, newPassword) =>
  api.post('/auth/reset-password', { token, new_password: newPassword });

export const uploadPitchDeck = (file) => {
  const formData = new FormData();
  formData.append('file', file);
  return api.post('/documents/upload', formData);
};

export const getReview = (id) =>
  api.get(`/reviews/${id}`);

export const submitQuestion = (reviewId, question) =>
  api.post(`/reviews/${reviewId}/questions`, { question_text: question });

export const submitAnswer = (questionId, answer) =>
  api.post(`/questions/${questionId}/answer`, { answer_text: answer });

export const getAllUsers = () => 
  api.get('/auth/users');

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
export const getProjectDeckAnalysis = (companyId, deckId) =>
  api.get(`/projects/${companyId}/deck-analysis/${deckId}`);

export const getProjectResults = (companyId, deckId) =>
  api.get(`/projects/${companyId}/results/${deckId}`);

export const getProjectUploads = (companyId) =>
  api.get(`/projects/${companyId}/uploads`);

export const getSlideImage = (companyId, deckName, slideFilename) =>
  api.get(`/projects/${companyId}/slide-image/${deckName}/${slideFilename}`, {
    responseType: 'blob'
  });

export const deleteDeck = (companyId, deckId) =>
  api.delete(`/projects/${companyId}/deck/${deckId}`);

export const cleanupOrphanedDecks = () =>
  api.delete('/decks/cleanup-orphaned');

export const getCompanyInfo = () =>
  api.get('/auth/company-info');

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

export default api;
