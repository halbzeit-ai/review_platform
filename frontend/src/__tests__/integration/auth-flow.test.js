/**
 * Integration tests for authentication flow
 * Tests complete user journeys from registration to dashboard access
 */

import React from 'react';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders, mockUsers } from '../test-utils';
import App from '../../App';
import '../mocks/server';

describe('Authentication Flow Integration', () => {
  let user;

  beforeEach(() => {
    user = userEvent.setup();
    localStorage.clear();
    jest.clearAllMocks();
  });

  describe('User Registration Flow', () => {
    it('completes full registration process', async () => {
      renderWithProviders(<App />, { route: '/register' });

      // Fill out registration form
      await user.type(screen.getByLabelText(/email/i), 'newuser@example.com');
      await user.type(screen.getByLabelText(/password/i), 'password123');
      await user.type(screen.getByLabelText(/company/i), 'Test Company');
      
      // Select language
      const languageSelect = screen.getByLabelText(/language/i);
      await user.click(languageSelect);
      await user.click(screen.getByText(/english/i));

      // Submit form
      const submitButton = screen.getByRole('button', { name: /register/i });
      await user.click(submitButton);

      // Should show success message
      await waitFor(() => {
        expect(screen.getByText(/registration successful/i)).toBeInTheDocument();
      });

      // Should show email verification prompt
      expect(screen.getByText(/check your email/i)).toBeInTheDocument();
    });

    it('shows validation errors for invalid input', async () => {
      renderWithProviders(<App />, { route: '/register' });

      // Try to submit with empty form
      const submitButton = screen.getByRole('button', { name: /register/i });
      await user.click(submitButton);

      // Should show validation errors
      await waitFor(() => {
        expect(screen.getByText(/email.*required/i)).toBeInTheDocument();
      });
    });

    it('handles existing email error', async () => {
      renderWithProviders(<App />, { route: '/register' });

      // Fill form with existing email
      await user.type(screen.getByLabelText(/email/i), 'existing@example.com');
      await user.type(screen.getByLabelText(/password/i), 'password123');
      await user.type(screen.getByLabelText(/company/i), 'Test Company');

      const submitButton = screen.getByRole('button', { name: /register/i });
      await user.click(submitButton);

      // Should show error message
      await waitFor(() => {
        expect(screen.getByText(/email already registered/i)).toBeInTheDocument();
      });
    });
  });

  describe('Email Verification Flow', () => {
    it('successfully verifies email with valid token', async () => {
      renderWithProviders(<App />, { 
        route: '/verify-email?token=valid-token' 
      });

      // Should show verification success
      await waitFor(() => {
        expect(screen.getByText(/email verified successfully/i)).toBeInTheDocument();
      });

      // Should have login link
      expect(screen.getByText(/log in/i)).toBeInTheDocument();
    });

    it('shows error for invalid token', async () => {
      renderWithProviders(<App />, { 
        route: '/verify-email?token=invalid' 
      });

      // Should show error message
      await waitFor(() => {
        expect(screen.getByText(/invalid.*token/i)).toBeInTheDocument();
      });
    });

    it('shows error for missing token', async () => {
      renderWithProviders(<App />, { route: '/verify-email' });

      // Should show error message
      await waitFor(() => {
        expect(screen.getByText(/verification.*required/i)).toBeInTheDocument();
      });
    });
  });

  describe('Login Flow', () => {
    it('successfully logs in with valid credentials', async () => {
      renderWithProviders(<App />, { route: '/login' });

      // Fill login form
      await user.type(screen.getByLabelText(/email/i), 'test@example.com');
      await user.type(screen.getByLabelText(/password/i), 'password123');

      // Submit form
      const loginButton = screen.getByRole('button', { name: /login/i });
      await user.click(loginButton);

      // Should redirect to dashboard
      await waitFor(() => {
        expect(screen.getByText(/dashboard/i)).toBeInTheDocument();
      });

      // Navigation should show logout button
      expect(screen.getByText(/logout/i)).toBeInTheDocument();
    });

    it('shows error for invalid credentials', async () => {
      renderWithProviders(<App />, { route: '/login' });

      // Fill with invalid credentials
      await user.type(screen.getByLabelText(/email/i), 'invalid@example.com');
      await user.type(screen.getByLabelText(/password/i), 'wrongpassword');

      const loginButton = screen.getByRole('button', { name: /login/i });
      await user.click(loginButton);

      // Should show error message
      await waitFor(() => {
        expect(screen.getByText(/invalid.*password/i)).toBeInTheDocument();
      });

      // Should stay on login page
      expect(screen.getByText(/login/i)).toBeInTheDocument();
    });

    it('prevents access to dashboard when not verified', async () => {
      // Mock unverified user response
      renderWithProviders(<App />, { route: '/login' });

      await user.type(screen.getByLabelText(/email/i), 'unverified@example.com');
      await user.type(screen.getByLabelText(/password/i), 'password123');

      const loginButton = screen.getByRole('button', { name: /login/i });
      await user.click(loginButton);

      // Should show verification required message
      await waitFor(() => {
        expect(screen.getByText(/verify.*email/i)).toBeInTheDocument();
      });
    });
  });

  describe('Language Preference Flow', () => {
    beforeEach(() => {
      // Mock logged in user
      localStorage.setItem('user', JSON.stringify(mockUsers.startup));
    });

    it('updates language preference when changed', async () => {
      renderWithProviders(<App />, { route: '/dashboard/startup' });

      // Find and click language switcher
      const languageSwitcher = screen.getByTestId('language-switcher');
      await user.click(languageSwitcher);

      // Select German
      await user.click(screen.getByText(/deutsch/i));

      // Should update user preference
      await waitFor(() => {
        const updatedUser = JSON.parse(localStorage.getItem('user'));
        expect(updatedUser.preferred_language).toBe('de');
      });
    });

    it('persists language preference across sessions', async () => {
      // Set German preference
      const germanUser = { ...mockUsers.startup, preferred_language: 'de' };
      localStorage.setItem('user', JSON.stringify(germanUser));

      renderWithProviders(<App />, { route: '/dashboard/startup' });

      // Should load with German interface
      await waitFor(() => {
        expect(screen.getByText(/pitch deck hochladen/i)).toBeInTheDocument();
      });
    });
  });

  describe('Protected Routes', () => {
    it('redirects to login when accessing protected route without auth', async () => {
      renderWithProviders(<App />, { route: '/dashboard/startup' });

      // Should redirect to login
      await waitFor(() => {
        expect(screen.getByText(/login/i)).toBeInTheDocument();
      });
    });

    it('allows access to protected route with valid auth', async () => {
      localStorage.setItem('user', JSON.stringify(mockUsers.startup));

      renderWithProviders(<App />, { route: '/dashboard/startup' });

      // Should show dashboard
      await waitFor(() => {
        expect(screen.getByText(/dashboard/i)).toBeInTheDocument();
      });
    });

    it('redirects GP to correct dashboard', async () => {
      localStorage.setItem('user', JSON.stringify(mockUsers.gp));

      renderWithProviders(<App />, { route: '/dashboard' });

      // Should show GP dashboard
      await waitFor(() => {
        expect(screen.getByText(/manage.*reviews/i)).toBeInTheDocument();
      });
    });
  });

  describe('Logout Flow', () => {
    beforeEach(() => {
      localStorage.setItem('user', JSON.stringify(mockUsers.startup));
    });

    it('successfully logs out user', async () => {
      renderWithProviders(<App />, { route: '/dashboard/startup' });

      // Click logout button
      const logoutButton = screen.getByText(/logout/i);
      await user.click(logoutButton);

      // Should clear localStorage and redirect
      expect(localStorage.getItem('user')).toBeNull();
      
      // Should show login page
      await waitFor(() => {
        expect(screen.getByText(/login/i)).toBeInTheDocument();
      });
    });

    it('prevents access to protected routes after logout', async () => {
      renderWithProviders(<App />, { route: '/dashboard/startup' });

      // Logout
      const logoutButton = screen.getByText(/logout/i);
      await user.click(logoutButton);

      // Try to access protected route again
      renderWithProviders(<App />, { route: '/dashboard/startup' });

      // Should redirect to login
      await waitFor(() => {
        expect(screen.getByText(/login/i)).toBeInTheDocument();
      });
    });
  });

  describe('Error Recovery', () => {
    it('recovers from network errors gracefully', async () => {
      renderWithProviders(<App />, { route: '/login' });

      // Simulate network error by using invalid credentials
      await user.type(screen.getByLabelText(/email/i), 'network-error@example.com');
      await user.type(screen.getByLabelText(/password/i), 'password');

      const loginButton = screen.getByRole('button', { name: /login/i });
      await user.click(loginButton);

      // Should show error message but form should still be functional
      await waitFor(() => {
        expect(screen.getByText(/error/i)).toBeInTheDocument();
      });

      // User should be able to try again
      expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    });

    it('handles session expiration gracefully', async () => {
      // Start with logged in user
      localStorage.setItem('user', JSON.stringify(mockUsers.startup));

      renderWithProviders(<App />, { route: '/dashboard/startup' });

      // Simulate session expiration by clearing token
      const expiredUser = { ...mockUsers.startup, access_token: 'expired' };
      localStorage.setItem('user', JSON.stringify(expiredUser));

      // Try to perform authenticated action
      const uploadButton = screen.getByText(/upload/i);
      await user.click(uploadButton);

      // Should handle expired session appropriately
      // (Implementation depends on how session expiration is handled)
    });
  });
});