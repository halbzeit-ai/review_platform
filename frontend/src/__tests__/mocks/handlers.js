/**
 * MSW (Mock Service Worker) handlers for API mocking
 * These handlers intercept HTTP requests during testing
 */

import { http, HttpResponse } from 'msw';
import { mockApiResponses } from '../test-utils';

const API_BASE_URL = process.env.REACT_APP_API_URL || '/api';

export const handlers = [
  // Authentication endpoints
  http.post(`${API_BASE_URL}/auth/register`, async ({ request }) => {
    const body = await request.json();
    
    if (body.email === 'existing@example.com') {
      return HttpResponse.json(mockApiResponses.register.failure, { status: 400 });
    }
    
    return HttpResponse.json(mockApiResponses.register.success);
  }),

  http.post(`${API_BASE_URL}/auth/login`, async ({ request }) => {
    const body = await request.json();
    
    if (body.email === 'invalid@example.com' || body.password === 'wrongpassword') {
      return HttpResponse.json(mockApiResponses.login.failure, { status: 400 });
    }
    
    if (!body.email || !body.password) {
      return HttpResponse.json({ detail: 'Email and password required' }, { status: 400 });
    }
    
    return HttpResponse.json(mockApiResponses.login.success);
  }),

  http.get(`${API_BASE_URL}/auth/verify-email`, ({ request }) => {
    const url = new URL(request.url);
    const token = url.searchParams.get('token');
    
    if (!token || token === 'invalid') {
      return HttpResponse.json(
        { detail: 'Invalid or expired verification token' },
        { status: 400 }
      );
    }
    
    return HttpResponse.json({
      message: 'Email verified successfully! You can now log in to your account.',
      email: 'test@example.com',
      verified: true,
    });
  }),

  http.get(`${API_BASE_URL}/auth/language-preference`, () => {
    return HttpResponse.json({
      preferred_language: 'en',
      email: 'test@example.com',
    });
  }),

  http.post(`${API_BASE_URL}/auth/language-preference`, async ({ request }) => {
    const body = await request.json();
    
    if (!['en', 'de'].includes(body.preferred_language)) {
      return HttpResponse.json(
        { detail: "Invalid language. Must be 'de' or 'en'" },
        { status: 400 }
      );
    }
    
    return HttpResponse.json({
      message: 'Language preference updated successfully',
      preferred_language: body.preferred_language,
      email: 'test@example.com',
    });
  }),

  // Pitch deck endpoints
  http.get(`${API_BASE_URL}/decks/`, () => {
    return HttpResponse.json(mockApiResponses.pitchDecks.success);
  }),

  http.post(`${API_BASE_URL}/decks/upload`, async ({ request }) => {
    const formData = await request.formData();
    const file = formData.get('file');
    
    if (!file) {
      return HttpResponse.json(
        { detail: 'No file provided' },
        { status: 400 }
      );
    }
    
    if (file.type !== 'application/pdf') {
      return HttpResponse.json(
        { detail: 'Invalid file format. Only PDF files are allowed.' },
        { status: 400 }
      );
    }
    
    if (file.size > 50 * 1024 * 1024) {
      return HttpResponse.json(
        { detail: 'File too large. Maximum size allowed is 50MB.' },
        { status: 413 }
      );
    }
    
    return HttpResponse.json({
      message: 'Pitch deck uploaded successfully',
      file_name: file.name,
      file_size: file.size,
      processing_status: 'uploaded',
    });
  }),

  // GP Dashboard endpoints
  http.get(`${API_BASE_URL}/users/`, () => {
    return HttpResponse.json({
      users: [
        {
          email: 'startup1@example.com',
          company_name: 'Startup One',
          role: 'startup',
          is_verified: true,
          last_login: '2024-01-15T10:30:00Z',
        },
        {
          email: 'startup2@example.com',
          company_name: 'Startup Two',
          role: 'startup',
          is_verified: false,
          last_login: null,
        },
      ],
    });
  }),

  http.post(`${API_BASE_URL}/auth/update-role`, async ({ request }) => {
    const body = await request.json();
    
    return HttpResponse.json({
      message: `Role updated successfully to ${body.new_role}`,
      email: body.user_email,
      new_role: body.new_role,
    });
  }),

  http.delete(`${API_BASE_URL}/auth/delete-user`, ({ request }) => {
    const url = new URL(request.url);
    const email = url.searchParams.get('user_email');
    
    if (!email) {
      return HttpResponse.json(
        { detail: 'User email required' },
        { status: 400 }
      );
    }
    
    if (email === 'notfound@example.com') {
      return HttpResponse.json(
        { detail: `User not found: ${email}` },
        { status: 404 }
      );
    }
    
    return HttpResponse.json({
      message: 'User deleted successfully',
      deleted_email: email,
    });
  }),

  // Error simulation endpoints
  http.get(`${API_BASE_URL}/error/500`, () => {
    return HttpResponse.json(
      { detail: 'Internal server error' },
      { status: 500 }
    );
  }),

  http.get(`${API_BASE_URL}/error/network`, () => {
    return HttpResponse.error();
  }),
];

// Export individual handlers for specific test scenarios
export const authHandlers = handlers.filter(handler => 
  handler.info.path.includes('/auth/')
);

export const deckHandlers = handlers.filter(handler => 
  handler.info.path.includes('/decks/')
);

export const userHandlers = handlers.filter(handler => 
  handler.info.path.includes('/users/')
);