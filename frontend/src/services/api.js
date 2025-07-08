
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://0.0.0.0:5001/api',
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
  return api.post('/decks', formData);
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

export default api;
