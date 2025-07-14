/**
 * MSW (Mock Service Worker) handlers for API mocking
 * These handlers intercept HTTP requests during testing
 */

import { rest } from 'msw';
import { mockApiResponses } from '../test-utils';

const API_BASE_URL = process.env.REACT_APP_API_URL || '/api';

export const handlers = [
  // Authentication endpoints
  rest.post(`${API_BASE_URL}/auth/register`, async (req, res, ctx) => {
    const body = await req.json();
    
    if (body.email === 'existing@example.com') {
      return res(ctx.status(400), ctx.json(mockApiResponses.register.failure));
    }
    
    return res(ctx.json(mockApiResponses.register.success));
  }),

  rest.post(`${API_BASE_URL}/auth/login`, async (req, res, ctx) => {
    const body = await req.json();
    
    if (body.email === 'invalid@example.com' || body.password === 'wrongpassword') {
      return res(ctx.status(400), ctx.json(mockApiResponses.login.failure));
    }
    
    if (!body.email || !body.password) {
      return res(ctx.status(400), ctx.json({ detail: 'Email and password required' }));
    }
    
    return res(ctx.json(mockApiResponses.login.success));
  }),

  rest.get(`${API_BASE_URL}/auth/verify-email`, (req, res, ctx) => {
    const token = req.url.searchParams.get('token');
    
    if (!token || token === 'invalid') {
      return res(ctx.status(400), ctx.json({ detail: 'Invalid or expired verification token' }));
    }
    
    return res(ctx.json({
      message: 'Email verified successfully! You can now log in to your account.',
      email: 'test@example.com',
      verified: true,
    }));
  }),

  rest.get(`${API_BASE_URL}/auth/language-preference`, (req, res, ctx) => {
    return res(ctx.json({
      preferred_language: 'en',
      email: 'test@example.com',
    }));
  }),

  rest.post(`${API_BASE_URL}/auth/language-preference`, async (req, res, ctx) => {
    const body = await req.json();
    
    if (!['en', 'de'].includes(body.preferred_language)) {
      return res(ctx.status(400), ctx.json({ detail: "Invalid language. Must be 'de' or 'en'" }));
    }
    
    return res(ctx.json({
      message: 'Language preference updated successfully',
      preferred_language: body.preferred_language,
      email: 'test@example.com',
    }));
  }),

  // Pitch deck endpoints
  rest.get(`${API_BASE_URL}/decks/`, (req, res, ctx) => {
    return res(ctx.json(mockApiResponses.pitchDecks.success));
  }),

  rest.post(`${API_BASE_URL}/decks/upload`, async (req, res, ctx) => {
    const formData = await req.formData?.();
    const file = formData?.get('file');
    
    if (!file) {
      return res(ctx.status(400), ctx.json({ detail: 'No file provided' }));
    }
    
    // For testing purposes, we'll simulate the file validation
    return res(ctx.json({
      message: 'Pitch deck uploaded successfully',
      file_name: 'test.pdf',
      file_size: 1024,
      processing_status: 'uploaded',
    }));
  }),

  // Default catch-all handler
  rest.get('*', (req, res, ctx) => {
    return res(ctx.status(404), ctx.json({ detail: 'Not found' }));
  }),
];

// Export individual handlers for specific test scenarios
export const authHandlers = handlers.filter(handler => 
  handler.info?.path?.includes('/auth/') || false
);

export const deckHandlers = handlers.filter(handler => 
  handler.info?.path?.includes('/decks/') || false
);