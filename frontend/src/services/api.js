
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

export const getAllUsers = () => {
  const user = JSON.parse(localStorage.getItem('user'));
  return api.get('/auth/users', {
    headers: {
      'Authorization': `Bearer ${user?.access_token}`
    }
  });
};

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

export default api;
