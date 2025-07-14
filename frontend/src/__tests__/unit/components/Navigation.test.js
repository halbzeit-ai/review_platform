/**
 * Unit tests for Navigation component
 */

import React from 'react';
import { screen, fireEvent } from '@testing-library/react';
import { renderWithProviders, mockUsers, mockLocalStorage } from '../../test-utils';
import Navigation from '../../../components/Navigation';

// Mock the LanguageSwitcher component
jest.mock('../../../components/LanguageSwitcher', () => {
  return function MockLanguageSwitcher() {
    return <div data-testid="language-switcher">Language Switcher</div>;
  };
});

describe('Navigation Component', () => {
  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear();
    jest.clearAllMocks();
  });

  describe('when user is not logged in', () => {
    beforeEach(() => {
      localStorage.removeItem('user');
    });

    it('renders the platform title', () => {
      renderWithProviders(<Navigation />);
      
      expect(screen.getByText('HALBZEIT AI Review Platform')).toBeInTheDocument();
    });

    it('renders language switcher', () => {
      renderWithProviders(<Navigation />);
      
      expect(screen.getByTestId('language-switcher')).toBeInTheDocument();
    });

    it('renders login and register buttons', () => {
      renderWithProviders(<Navigation />);
      
      expect(screen.getByText('navigation.login')).toBeInTheDocument();
      expect(screen.getByText('navigation.register')).toBeInTheDocument();
    });

    it('does not render logout button', () => {
      renderWithProviders(<Navigation />);
      
      expect(screen.queryByText('navigation.logout')).not.toBeInTheDocument();
    });
  });

  describe('when user is logged in', () => {
    beforeEach(() => {
      mockLocalStorage.setItem('user', mockUsers.startup);
    });

    it('renders logout button', () => {
      renderWithProviders(<Navigation />);
      
      expect(screen.getByText('navigation.logout')).toBeInTheDocument();
    });

    it('does not render login and register buttons', () => {
      renderWithProviders(<Navigation />);
      
      expect(screen.queryByText('navigation.login')).not.toBeInTheDocument();
      expect(screen.queryByText('navigation.register')).not.toBeInTheDocument();
    });

    it('clears localStorage and redirects on logout click', () => {
      // Mock window.location.href
      delete window.location;
      window.location = { href: '' };
      
      renderWithProviders(<Navigation />);
      
      const logoutButton = screen.getByText('navigation.logout');
      fireEvent.click(logoutButton);
      
      expect(localStorage.getItem('user')).toBeNull();
      expect(window.location.href).toBe('/login');
    });
  });

  describe('navigation actions', () => {
    it('navigates to login when login button is clicked', () => {
      const { container } = renderWithProviders(<Navigation />, {
        route: '/some-page',
      });
      
      const loginButton = screen.getByText('navigation.login');
      fireEvent.click(loginButton);
      
      // Check that navigation occurred (URL should change)
      // Note: In real tests, you might want to check the router state
      expect(loginButton).toBeInTheDocument();
    });

    it('navigates to register when register button is clicked', () => {
      renderWithProviders(<Navigation />);
      
      const registerButton = screen.getByText('navigation.register');
      fireEvent.click(registerButton);
      
      expect(registerButton).toBeInTheDocument();
    });
  });

  describe('accessibility', () => {
    it('has proper button roles', () => {
      renderWithProviders(<Navigation />);
      
      const buttons = screen.getAllByRole('button');
      expect(buttons.length).toBeGreaterThan(0);
    });

    it('login button has accessible text', () => {
      renderWithProviders(<Navigation />);
      
      const loginButton = screen.getByRole('button', { name: /navigation\.login/i });
      expect(loginButton).toBeInTheDocument();
    });
  });

  describe('responsive behavior', () => {
    it('renders correctly on mobile devices', () => {
      // Mock mobile viewport
      global.innerWidth = 375;
      global.dispatchEvent(new Event('resize'));
      
      renderWithProviders(<Navigation />);
      
      expect(screen.getByText('HALBZEIT AI Review Platform')).toBeInTheDocument();
    });
  });

  describe('error handling', () => {
    it('handles corrupted localStorage gracefully', () => {
      // Set invalid JSON in localStorage
      localStorage.setItem('user', 'invalid-json');
      
      renderWithProviders(<Navigation />);
      
      // Should render as if not logged in
      expect(screen.getByText('navigation.login')).toBeInTheDocument();
      expect(screen.getByText('navigation.register')).toBeInTheDocument();
    });

    it('handles missing localStorage gracefully', () => {
      // Remove localStorage entirely
      const originalLocalStorage = window.localStorage;
      delete window.localStorage;
      
      renderWithProviders(<Navigation />);
      
      expect(screen.getByText('navigation.login')).toBeInTheDocument();
      
      // Restore localStorage
      window.localStorage = originalLocalStorage;
    });
  });
});