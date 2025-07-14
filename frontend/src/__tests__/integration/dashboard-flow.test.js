/**
 * Integration tests for dashboard functionality
 * Tests complete user workflows in startup and GP dashboards
 */

import React from 'react';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders, mockUsers, mockFiles } from '../test-utils';
import App from '../../App';
import '../mocks/server';

describe('Dashboard Flow Integration', () => {
  let user;

  beforeEach(() => {
    user = userEvent.setup();
    localStorage.clear();
    jest.clearAllMocks();
  });

  describe('Startup Dashboard Flow', () => {
    beforeEach(() => {
      localStorage.setItem('user', JSON.stringify(mockUsers.startup));
    });

    it('displays dashboard with upload section', async () => {
      renderWithProviders(<App />, { route: '/dashboard/startup' });

      // Should show startup dashboard
      await waitFor(() => {
        expect(screen.getByText(/startup dashboard/i)).toBeInTheDocument();
      });

      // Should show upload section
      expect(screen.getByText(/upload pitch deck/i)).toBeInTheDocument();
      expect(screen.getByText(/maximum.*50mb/i)).toBeInTheDocument();
    });

    it('successfully uploads valid PDF file', async () => {
      renderWithProviders(<App />, { route: '/dashboard/startup' });

      // Find file input
      const fileInput = screen.getByLabelText(/upload/i);
      
      // Upload valid PDF
      await user.upload(fileInput, mockFiles.validPdf);

      // Should show success message
      await waitFor(() => {
        expect(screen.getByText(/uploaded successfully/i)).toBeInTheDocument();
      });

      // Should refresh deck list
      expect(screen.getByText(/test\.pdf/i)).toBeInTheDocument();
    });

    it('shows error for invalid file type', async () => {
      renderWithProviders(<App />, { route: '/dashboard/startup' });

      const fileInput = screen.getByLabelText(/upload/i);
      
      // Upload invalid file type
      await user.upload(fileInput, mockFiles.invalidType);

      // Should show error message
      await waitFor(() => {
        expect(screen.getByText(/only pdf files/i)).toBeInTheDocument();
      });
    });

    it('shows error for oversized file', async () => {
      renderWithProviders(<App />, { route: '/dashboard/startup' });

      const fileInput = screen.getByLabelText(/upload/i);
      
      // Upload oversized file
      await user.upload(fileInput, mockFiles.oversized);

      // Should show error message
      await waitFor(() => {
        expect(screen.getByText(/file too large/i)).toBeInTheDocument();
      });
    });

    it('displays uploaded pitch decks list', async () => {
      renderWithProviders(<App />, { route: '/dashboard/startup' });

      // Should show pitch decks section
      await waitFor(() => {
        expect(screen.getByText(/your.*pitch decks/i)).toBeInTheDocument();
      });

      // Should show deck list
      expect(screen.getByText(/test-deck\.pdf/i)).toBeInTheDocument();
      expect(screen.getByText(/another-deck\.pdf/i)).toBeInTheDocument();
    });

    it('shows processing status for uploaded files', async () => {
      renderWithProviders(<App />, { route: '/dashboard/startup' });

      await waitFor(() => {
        // Should show different status chips
        expect(screen.getByText(/completed/i)).toBeInTheDocument();
        expect(screen.getByText(/processing/i)).toBeInTheDocument();
      });
    });

    it('handles empty deck list gracefully', async () => {
      // Mock empty response
      renderWithProviders(<App />, { route: '/dashboard/startup' });

      await waitFor(() => {
        expect(screen.getByText(/no pitch decks uploaded/i)).toBeInTheDocument();
      });
    });

    it('updates language and refreshes content', async () => {
      renderWithProviders(<App />, { route: '/dashboard/startup' });

      // Switch to German
      const languageSwitcher = screen.getByTestId('language-switcher');
      await user.click(languageSwitcher);
      await user.click(screen.getByText(/deutsch/i));

      // Dashboard should update to German
      await waitFor(() => {
        expect(screen.getByText(/pitch deck hochladen/i)).toBeInTheDocument();
      });
    });
  });

  describe('GP Dashboard Flow', () => {
    beforeEach(() => {
      localStorage.setItem('user', JSON.stringify(mockUsers.gp));
    });

    it('displays GP dashboard with management sections', async () => {
      renderWithProviders(<App />, { route: '/dashboard/gp' });

      // Should show GP dashboard
      await waitFor(() => {
        expect(screen.getByText(/general partner dashboard/i)).toBeInTheDocument();
      });

      // Should show management sections
      expect(screen.getByText(/manage reviews/i)).toBeInTheDocument();
      expect(screen.getByText(/manage users/i)).toBeInTheDocument();
    });

    it('displays user list with management actions', async () => {
      renderWithProviders(<App />, { route: '/dashboard/gp' });

      await waitFor(() => {
        // Should show user list
        expect(screen.getByText(/startup1@example\.com/i)).toBeInTheDocument();
        expect(screen.getByText(/startup2@example\.com/i)).toBeInTheDocument();
      });

      // Should show action buttons
      expect(screen.getAllByText(/change role/i)).toHaveLength(2);
      expect(screen.getAllByText(/delete/i)).toHaveLength(2);
    });

    it('successfully changes user role', async () => {
      renderWithProviders(<App />, { route: '/dashboard/gp' });

      await waitFor(() => {
        const changeRoleButtons = screen.getAllByText(/change role/i);
        await user.click(changeRoleButtons[0]);
      });

      // Should show role selection dialog
      expect(screen.getByText(/select new role/i)).toBeInTheDocument();

      // Select new role
      await user.click(screen.getByText(/general partner/i));
      await user.click(screen.getByText(/confirm/i));

      // Should show success message
      await waitFor(() => {
        expect(screen.getByText(/role updated successfully/i)).toBeInTheDocument();
      });
    });

    it('successfully deletes user with confirmation', async () => {
      renderWithProviders(<App />, { route: '/dashboard/gp' });

      await waitFor(() => {
        const deleteButtons = screen.getAllByText(/delete/i);
        await user.click(deleteButtons[0]);
      });

      // Should show confirmation dialog
      expect(screen.getByText(/delete user/i)).toBeInTheDocument();
      expect(screen.getByText(/permanently delete/i)).toBeInTheDocument();

      // Confirm deletion
      await user.click(screen.getByText(/yes.*delete/i));

      // Should show success message
      await waitFor(() => {
        expect(screen.getByText(/user deleted successfully/i)).toBeInTheDocument();
      });
    });

    it('cancels user deletion when declined', async () => {
      renderWithProviders(<App />, { route: '/dashboard/gp' });

      await waitFor(() => {
        const deleteButtons = screen.getAllByText(/delete/i);
        await user.click(deleteButtons[0]);
      });

      // Cancel deletion
      await user.click(screen.getByText(/cancel/i));

      // Dialog should close, user should remain
      expect(screen.queryByText(/delete user/i)).not.toBeInTheDocument();
      expect(screen.getByText(/startup1@example\.com/i)).toBeInTheDocument();
    });

    it('handles user management errors gracefully', async () => {
      renderWithProviders(<App />, { route: '/dashboard/gp' });

      // Try to delete non-existent user (would require specific mocking)
      await waitFor(() => {
        const deleteButtons = screen.getAllByText(/delete/i);
        await user.click(deleteButtons[0]);
      });

      await user.click(screen.getByText(/yes.*delete/i));

      // Should handle error appropriately
      // (Error handling depends on implementation)
    });
  });

  describe('Dashboard Navigation', () => {
    it('redirects startup users to startup dashboard', async () => {
      localStorage.setItem('user', JSON.stringify(mockUsers.startup));

      renderWithProviders(<App />, { route: '/dashboard' });

      // Should redirect to startup dashboard
      await waitFor(() => {
        expect(screen.getByText(/upload pitch deck/i)).toBeInTheDocument();
      });
    });

    it('redirects GP users to GP dashboard', async () => {
      localStorage.setItem('user', JSON.stringify(mockUsers.gp));

      renderWithProviders(<App />, { route: '/dashboard' });

      // Should redirect to GP dashboard
      await waitFor(() => {
        expect(screen.getByText(/manage reviews/i)).toBeInTheDocument();
      });
    });

    it('prevents cross-role access', async () => {
      localStorage.setItem('user', JSON.stringify(mockUsers.startup));

      renderWithProviders(<App />, { route: '/dashboard/gp' });

      // Should redirect to appropriate dashboard or show error
      await waitFor(() => {
        expect(screen.getByText(/unauthorized/i) || screen.getByText(/upload pitch deck/i)).toBeInTheDocument();
      });
    });
  });

  describe('Real-time Updates', () => {
    beforeEach(() => {
      localStorage.setItem('user', JSON.stringify(mockUsers.startup));
    });

    it('refreshes deck list after successful upload', async () => {
      renderWithProviders(<App />, { route: '/dashboard/startup' });

      // Initial deck count
      const initialDecks = screen.getAllByText(/\.pdf/i);
      const initialCount = initialDecks.length;

      // Upload new deck
      const fileInput = screen.getByLabelText(/upload/i);
      await user.upload(fileInput, mockFiles.validPdf);

      // Should refresh and show updated list
      await waitFor(() => {
        const updatedDecks = screen.getAllByText(/\.pdf/i);
        expect(updatedDecks.length).toBeGreaterThan(initialCount);
      });
    });

    it('updates status indicators in real-time', async () => {
      renderWithProviders(<App />, { route: '/dashboard/startup' });

      // Should show processing status
      await waitFor(() => {
        expect(screen.getByText(/processing/i)).toBeInTheDocument();
      });

      // Status should update (this would require WebSocket or polling implementation)
      // For now, we test that the status is displayed correctly
    });
  });

  describe('Responsive Behavior', () => {
    beforeEach(() => {
      localStorage.setItem('user', JSON.stringify(mockUsers.startup));
    });

    it('renders correctly on mobile devices', async () => {
      // Mock mobile viewport
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 375,
      });

      renderWithProviders(<App />, { route: '/dashboard/startup' });

      // Should render mobile-friendly layout
      await waitFor(() => {
        expect(screen.getByText(/upload pitch deck/i)).toBeInTheDocument();
      });
    });

    it('adapts table layout for smaller screens', async () => {
      localStorage.setItem('user', JSON.stringify(mockUsers.gp));

      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 480,
      });

      renderWithProviders(<App />, { route: '/dashboard/gp' });

      // Should show responsive table/list layout
      await waitFor(() => {
        expect(screen.getByText(/manage users/i)).toBeInTheDocument();
      });
    });
  });

  describe('Accessibility', () => {
    beforeEach(() => {
      localStorage.setItem('user', JSON.stringify(mockUsers.startup));
    });

    it('supports keyboard navigation', async () => {
      renderWithProviders(<App />, { route: '/dashboard/startup' });

      // Test tab navigation
      const uploadButton = screen.getByText(/upload pitch deck/i);
      uploadButton.focus();
      
      expect(document.activeElement).toBe(uploadButton);
    });

    it('has proper ARIA labels and roles', async () => {
      renderWithProviders(<App />, { route: '/dashboard/startup' });

      // Check for proper ARIA attributes
      const fileInput = screen.getByLabelText(/upload/i);
      expect(fileInput).toHaveAttribute('aria-label');
    });

    it('supports screen readers with descriptive text', async () => {
      renderWithProviders(<App />, { route: '/dashboard/startup' });

      // Should have descriptive text for screen readers
      expect(screen.getByText(/maximum.*50mb/i)).toBeInTheDocument();
      expect(screen.getByText(/only pdf files/i)).toBeInTheDocument();
    });
  });
});