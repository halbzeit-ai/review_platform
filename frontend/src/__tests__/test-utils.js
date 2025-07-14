/**
 * Test utilities for React Testing Library
 * Provides common testing setup and helper functions
 */

import React from 'react';
import { render } from '@testing-library/react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { MemoryRouter } from 'react-router-dom';

// Create a simple theme for testing
const theme = createTheme({
  palette: {
    mode: 'light',
  },
});

/**
 * Custom render function that includes common providers
 * @param {React.ReactElement} ui - Component to render
 * @param {Object} options - Render options
 * @param {Array} options.initialEntries - Initial router entries
 * @param {string} options.route - Initial route
 * @param {Object} options.providerProps - Props for providers
 * @returns {Object} Render result with additional utilities
 */
export const renderWithProviders = (
  ui,
  {
    initialEntries = ['/'],
    route = '/',
    providerProps = {},
    ...renderOptions
  } = {}
) => {
  // Set up router with initial entries
  const routerProps = {
    initialEntries: [route, ...initialEntries],
    ...providerProps.router,
  };

  const Wrapper = ({ children }) => (
    <MemoryRouter {...routerProps}>
      <ThemeProvider theme={theme}>
        {children}
      </ThemeProvider>
    </MemoryRouter>
  );

  return {
    ...render(ui, { wrapper: Wrapper, ...renderOptions }),
    // Additional utilities can be added here
  };
};

/**
 * Mock user data for testing
 */
export const mockUsers = {
  startup: {
    email: 'startup@example.com',
    company_name: 'Test Startup',
    role: 'startup',
    preferred_language: 'en',
    is_verified: true,
  },
  gp: {
    email: 'gp@example.com',
    company_name: 'VC Fund',
    role: 'gp',
    preferred_language: 'de',
    is_verified: true,
  },
  unverified: {
    email: 'unverified@example.com',
    company_name: 'Pending Startup',
    role: 'startup',
    preferred_language: 'en',
    is_verified: false,
  },
};

/**
 * Mock API responses for testing
 */
export const mockApiResponses = {
  login: {
    success: {
      message: 'Login successful',
      email: 'test@example.com',
      role: 'startup',
      company_name: 'Test Company',
      preferred_language: 'en',
      access_token: 'mock-jwt-token',
      token_type: 'Bearer',
    },
    failure: {
      detail: 'Invalid email or password',
    },
  },
  register: {
    success: {
      message: 'Registration successful! Please check your email to verify your account.',
      email: 'test@example.com',
      company_name: 'Test Company',
      role: 'startup',
      email_sent: true,
    },
    failure: {
      detail: 'Email already registered',
    },
  },
  pitchDecks: {
    success: {
      decks: [
        {
          id: 1,
          file_name: 'test-deck.pdf',
          processing_status: 'completed',
          created_at: '2024-01-15T10:30:00Z',
        },
        {
          id: 2,
          file_name: 'another-deck.pdf',
          processing_status: 'processing',
          created_at: '2024-01-16T14:20:00Z',
        },
      ],
    },
    empty: {
      decks: [],
    },
  },
};

/**
 * Mock file objects for upload testing
 */
export const mockFiles = {
  validPdf: new File(['PDF content'], 'test.pdf', { type: 'application/pdf' }),
  invalidType: new File(['Text content'], 'test.txt', { type: 'text/plain' }),
  oversized: new File([new ArrayBuffer(51 * 1024 * 1024)], 'large.pdf', { type: 'application/pdf' }),
};

/**
 * Helper function to mock localStorage
 */
export const mockLocalStorage = {
  setItem: (key, value) => {
    localStorage.setItem(key, JSON.stringify(value));
  },
  getItem: (key) => {
    const item = localStorage.getItem(key);
    return item ? JSON.parse(item) : null;
  },
  removeItem: (key) => {
    localStorage.removeItem(key);
  },
  clear: () => {
    localStorage.clear();
  },
};

// Re-export everything from RTL
export * from '@testing-library/react';
export { renderWithProviders as render };