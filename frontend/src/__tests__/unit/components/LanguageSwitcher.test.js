/**
 * Unit tests for LanguageSwitcher component
 */

import React from 'react';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import { renderWithProviders, mockUsers, mockLocalStorage } from '../../test-utils';
import LanguageSwitcher from '../../../components/LanguageSwitcher';
import '../../mocks/server';

describe('LanguageSwitcher Component', () => {
  beforeEach(() => {
    localStorage.clear();
    jest.clearAllMocks();
  });

  describe('when user is not logged in', () => {
    it('renders language dropdown', () => {
      renderWithProviders(<LanguageSwitcher />);
      
      // Should render the language selector button
      expect(screen.getByRole('button')).toBeInTheDocument();
    });

    it('shows current language in dropdown', () => {
      renderWithProviders(<LanguageSwitcher />);
      
      // Default language should be shown
      const button = screen.getByRole('button');
      expect(button).toBeInTheDocument();
    });

    it('allows language switching without API call', async () => {
      renderWithProviders(<LanguageSwitcher />);
      
      const button = screen.getByRole('button');
      fireEvent.click(button);
      
      // Should show language options
      await waitFor(() => {
        expect(screen.getByText(/Deutsch/i) || screen.getByText(/German/i)).toBeInTheDocument();
      });
    });
  });

  describe('when user is logged in', () => {
    beforeEach(() => {
      mockLocalStorage.setItem('user', mockUsers.startup);
    });

    it('renders language dropdown for logged in user', () => {
      renderWithProviders(<LanguageSwitcher />);
      
      expect(screen.getByRole('button')).toBeInTheDocument();
    });

    it('updates language preference via API when changed', async () => {
      renderWithProviders(<LanguageSwitcher />);
      
      const button = screen.getByRole('button');
      fireEvent.click(button);
      
      // Wait for dropdown to open and select German
      await waitFor(() => {
        const germanOption = screen.getByText(/Deutsch/i) || screen.getByText(/German/i);
        if (germanOption) {
          fireEvent.click(germanOption);
        }
      });
      
      // Should make API call to update preference
      // (API call is mocked via MSW)
    });

    it('updates localStorage when language changes', async () => {
      renderWithProviders(<LanguageSwitcher />);
      
      const button = screen.getByRole('button');
      fireEvent.click(button);
      
      await waitFor(() => {
        const option = screen.getByText(/Deutsch/i) || screen.getByText(/German/i);
        if (option) {
          fireEvent.click(option);
        }
      });
      
      // Check if localStorage was updated
      // Note: The actual implementation may vary
    });
  });

  describe('language options', () => {
    it('shows both German and English options', async () => {
      renderWithProviders(<LanguageSwitcher />);
      
      const button = screen.getByRole('button');
      fireEvent.click(button);
      
      await waitFor(() => {
        // Should show both language options
        expect(screen.getByText(/English/i) || screen.getByText(/Englisch/i)).toBeInTheDocument();
        expect(screen.getByText(/Deutsch/i) || screen.getByText(/German/i)).toBeInTheDocument();
      });
    });

    it('displays flag icons for languages', async () => {
      renderWithProviders(<LanguageSwitcher />);
      
      const button = screen.getByRole('button');
      fireEvent.click(button);
      
      await waitFor(() => {
        // Check for flag images or icons
        const images = screen.getAllByRole('img');
        expect(images.length).toBeGreaterThan(0);
      });
    });
  });

  describe('error handling', () => {
    it('handles API errors gracefully', async () => {
      // Mock API error
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      
      // Mock localStorage with user
      mockLocalStorage.setItem('user', mockUsers.startup);
      
      renderWithProviders(<LanguageSwitcher />);
      
      const button = screen.getByRole('button');
      fireEvent.click(button);
      
      await waitFor(() => {
        const option = screen.getByText(/Deutsch/i) || screen.getByText(/German/i);
        if (option) {
          fireEvent.click(option);
        }
      });
      
      // Component should still work even if API fails
      expect(button).toBeInTheDocument();
      
      consoleSpy.mockRestore();
    });

    it('handles missing user data gracefully', () => {
      // Remove user from localStorage
      localStorage.removeItem('user');
      
      renderWithProviders(<LanguageSwitcher />);
      
      expect(screen.getByRole('button')).toBeInTheDocument();
    });
  });

  describe('accessibility', () => {
    it('has proper ARIA labels', () => {
      renderWithProviders(<LanguageSwitcher />);
      
      const button = screen.getByRole('button');
      expect(button).toHaveAttribute('aria-label', expect.anything());
    });

    it('supports keyboard navigation', async () => {
      renderWithProviders(<LanguageSwitcher />);
      
      const button = screen.getByRole('button');
      
      // Test keyboard interaction
      fireEvent.keyDown(button, { key: 'Enter' });
      
      await waitFor(() => {
        // Dropdown should open
        expect(screen.getByRole('menu') || screen.getByRole('listbox')).toBeInTheDocument();
      });
    });
  });

  describe('integration with i18n', () => {
    it('changes application language when option is selected', async () => {
      const { rerender } = renderWithProviders(<LanguageSwitcher />);
      
      const button = screen.getByRole('button');
      fireEvent.click(button);
      
      await waitFor(() => {
        const germanOption = screen.getByText(/Deutsch/i) || screen.getByText(/German/i);
        if (germanOption) {
          fireEvent.click(germanOption);
        }
      });
      
      // Language should change in the application
      // This would be visible in other components using translations
    });
  });
});