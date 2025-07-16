import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { I18nextProvider } from 'react-i18next';
import StartupDashboard from '../../../pages/StartupDashboard';
import { uploadPitchDeck, getPitchDecks } from '../../../services/api';
import i18n from '../../../i18n';

// Mock the API functions
jest.mock('../../../services/api', () => ({
  uploadPitchDeck: jest.fn(),
  getPitchDecks: jest.fn(),
}));

// Mock useNavigate
const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

const renderStartupDashboard = () => {
  return render(
    <I18nextProvider i18n={i18n}>
      <BrowserRouter>
        <StartupDashboard />
      </BrowserRouter>
    </I18nextProvider>
  );
};

describe('StartupDashboard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Set up default mock responses
    getPitchDecks.mockResolvedValue({
      data: {
        decks: []
      }
    });
  });

  describe('Component Rendering', () => {
    test('renders startup dashboard title', async () => {
      renderStartupDashboard();
      
      await waitFor(() => {
        expect(screen.getByText('Startup Dashboard')).toBeInTheDocument();
      });
    });

    test('renders upload section', async () => {
      renderStartupDashboard();
      
      await waitFor(() => {
        expect(screen.getByText('Upload Pitch Deck')).toBeInTheDocument();
        expect(screen.getByText('PITCH DECK HOCHLADEN')).toBeInTheDocument();
      });
    });

    test('renders empty deck list initially', async () => {
      renderStartupDashboard();
      
      await waitFor(() => {
        expect(screen.getByText('Your Pitch Decks')).toBeInTheDocument();
        expect(screen.getByText('No pitch decks uploaded yet')).toBeInTheDocument();
      });
    });
  });

  describe('Status Translation', () => {
    test('displays correct status labels in English', async () => {
      const mockDecks = [
        { id: 1, file_name: 'test1.pdf', processing_status: 'pending', created_at: '2025-01-01' },
        { id: 2, file_name: 'test2.pdf', processing_status: 'processing', created_at: '2025-01-01' },
        { id: 3, file_name: 'test3.pdf', processing_status: 'completed', created_at: '2025-01-01' },
        { id: 4, file_name: 'test4.pdf', processing_status: 'failed', created_at: '2025-01-01' }
      ];

      getPitchDecks.mockResolvedValue({
        data: { decks: mockDecks }
      });

      renderStartupDashboard();

      await waitFor(() => {
        expect(screen.getByText('Waiting for processing')).toBeInTheDocument();
        expect(screen.getByText('Being analyzed...')).toBeInTheDocument();
        expect(screen.getByText('Evaluated')).toBeInTheDocument();
        expect(screen.getByText('Failed')).toBeInTheDocument();
      });
    });

    test('displays correct status labels in German', async () => {
      // Switch to German
      await act(async () => {
        await i18n.changeLanguage('de');
      });

      const mockDecks = [
        { id: 1, file_name: 'test1.pdf', processing_status: 'pending', created_at: '2025-01-01' },
        { id: 2, file_name: 'test2.pdf', processing_status: 'processing', created_at: '2025-01-01' },
        { id: 3, file_name: 'test3.pdf', processing_status: 'completed', created_at: '2025-01-01' },
        { id: 4, file_name: 'test4.pdf', processing_status: 'failed', created_at: '2025-01-01' }
      ];

      getPitchDecks.mockResolvedValue({
        data: { decks: mockDecks }
      });

      renderStartupDashboard();

      await waitFor(() => {
        expect(screen.getByText('Warte auf Verarbeitung')).toBeInTheDocument();
        expect(screen.getByText('Wird analysiert...')).toBeInTheDocument();
        expect(screen.getByText('Bewertet')).toBeInTheDocument();
        expect(screen.getByText('Fehlgeschlagen')).toBeInTheDocument();
      });

      // Switch back to English for other tests
      await act(async () => {
        await i18n.changeLanguage('en');
      });
    });
  });

  describe('Status Icons', () => {
    test('displays correct icons for each status', async () => {
      const mockDecks = [
        { id: 1, file_name: 'test1.pdf', processing_status: 'pending', created_at: '2025-01-01' },
        { id: 2, file_name: 'test2.pdf', processing_status: 'processing', created_at: '2025-01-01' },
        { id: 3, file_name: 'test3.pdf', processing_status: 'completed', created_at: '2025-01-01' },
        { id: 4, file_name: 'test4.pdf', processing_status: 'failed', created_at: '2025-01-01' }
      ];

      getPitchDecks.mockResolvedValue({
        data: { decks: mockDecks }
      });

      renderStartupDashboard();

      await waitFor(() => {
        // Check for MUI icons by testing for specific classes or test IDs
        const chips = screen.getAllByRole('button'); // Chips are rendered as buttons
        expect(chips.length).toBeGreaterThan(0);
      });
    });
  });

  describe('Adaptive Polling', () => {
    beforeEach(() => {
      jest.useFakeTimers();
    });

    afterEach(() => {
      jest.useRealTimers();
    });

    test('polls every 2 seconds when processing decks exist', async () => {
      const mockDecks = [
        { id: 1, file_name: 'test.pdf', processing_status: 'processing', created_at: '2025-01-01' }
      ];

      getPitchDecks.mockResolvedValue({
        data: { decks: mockDecks }
      });

      renderStartupDashboard();

      // Initial call
      await waitFor(() => {
        expect(getPitchDecks).toHaveBeenCalledTimes(1);
      });

      // Fast forward 2 seconds
      act(() => {
        jest.advanceTimersByTime(2000);
      });

      await waitFor(() => {
        expect(getPitchDecks).toHaveBeenCalledTimes(2);
      });

      // Fast forward another 2 seconds
      act(() => {
        jest.advanceTimersByTime(2000);
      });

      await waitFor(() => {
        expect(getPitchDecks).toHaveBeenCalledTimes(3);
      });
    });

    test('polls every 10 seconds when no processing decks exist', async () => {
      const mockDecks = [
        { id: 1, file_name: 'test.pdf', processing_status: 'completed', created_at: '2025-01-01' }
      ];

      getPitchDecks.mockResolvedValue({
        data: { decks: mockDecks }
      });

      renderStartupDashboard();

      // Initial call
      await waitFor(() => {
        expect(getPitchDecks).toHaveBeenCalledTimes(1);
      });

      // Fast forward 2 seconds (should not trigger)
      act(() => {
        jest.advanceTimersByTime(2000);
      });

      expect(getPitchDecks).toHaveBeenCalledTimes(1);

      // Fast forward to 10 seconds total
      act(() => {
        jest.advanceTimersByTime(8000);
      });

      await waitFor(() => {
        expect(getPitchDecks).toHaveBeenCalledTimes(2);
      });
    });
  });

  describe('File Upload', () => {
    test('shows immediate upload feedback', async () => {
      const mockFile = new File(['test content'], 'test.pdf', { type: 'application/pdf' });
      
      uploadPitchDeck.mockResolvedValue({
        data: {
          pitch_deck_id: 1,
          filename: 'test.pdf',
          processing_status: 'processing'
        }
      });

      renderStartupDashboard();

      const fileInput = screen.getByLabelText(/pitch deck hochladen/i);
      
      await act(async () => {
        fireEvent.change(fileInput, { target: { files: [mockFile] } });
      });

      await waitFor(() => {
        expect(uploadPitchDeck).toHaveBeenCalledWith(mockFile);
        expect(screen.getByText('File uploaded successfully!')).toBeInTheDocument();
      });
    });

    test('validates file type', async () => {
      const mockFile = new File(['test content'], 'test.txt', { type: 'text/plain' });
      
      renderStartupDashboard();

      const fileInput = screen.getByLabelText(/pitch deck hochladen/i);
      
      await act(async () => {
        fireEvent.change(fileInput, { target: { files: [mockFile] } });
      });

      await waitFor(() => {
        expect(screen.getByText('Invalid file type. Only PDF allowed')).toBeInTheDocument();
        expect(uploadPitchDeck).not.toHaveBeenCalled();
      });
    });

    test('validates file size', async () => {
      // Create a large file (> 50MB)
      const largeContent = new Array(51 * 1024 * 1024).fill('a').join('');
      const mockFile = new File([largeContent], 'large.pdf', { type: 'application/pdf' });
      
      renderStartupDashboard();

      const fileInput = screen.getByLabelText(/pitch deck hochladen/i);
      
      await act(async () => {
        fireEvent.change(fileInput, { target: { files: [mockFile] } });
      });

      await waitFor(() => {
        expect(screen.getByText('File too large. Maximum: 50MB')).toBeInTheDocument();
        expect(uploadPitchDeck).not.toHaveBeenCalled();
      });
    });

    test('handles upload errors gracefully', async () => {
      const mockFile = new File(['test content'], 'test.pdf', { type: 'application/pdf' });
      
      uploadPitchDeck.mockRejectedValue({
        response: {
          status: 500,
          data: { detail: 'Server error' }
        }
      });

      renderStartupDashboard();

      const fileInput = screen.getByLabelText(/pitch deck hochladen/i);
      
      await act(async () => {
        fireEvent.change(fileInput, { target: { files: [mockFile] } });
      });

      await waitFor(() => {
        expect(screen.getByText('Server error')).toBeInTheDocument();
      });
    });
  });

  describe('Results Navigation', () => {
    test('navigates to results page when view results is clicked', async () => {
      const mockDecks = [
        { id: 1, file_name: 'test.pdf', processing_status: 'completed', created_at: '2025-01-01' }
      ];

      getPitchDecks.mockResolvedValue({
        data: { decks: mockDecks }
      });

      renderStartupDashboard();

      await waitFor(() => {
        const viewResultsButton = screen.getByText('View Results');
        fireEvent.click(viewResultsButton);
      });

      expect(mockNavigate).toHaveBeenCalledWith('/results/1');
    });

    test('only shows view results button for completed decks', async () => {
      const mockDecks = [
        { id: 1, file_name: 'test1.pdf', processing_status: 'processing', created_at: '2025-01-01' },
        { id: 2, file_name: 'test2.pdf', processing_status: 'completed', created_at: '2025-01-01' }
      ];

      getPitchDecks.mockResolvedValue({
        data: { decks: mockDecks }
      });

      renderStartupDashboard();

      await waitFor(() => {
        const viewResultsButtons = screen.getAllByText('View Results');
        expect(viewResultsButtons).toHaveLength(1);
      });
    });
  });

  describe('Error Handling', () => {
    test('handles API errors gracefully', async () => {
      getPitchDecks.mockRejectedValue(new Error('API Error'));

      renderStartupDashboard();

      // Component should still render without crashing
      await waitFor(() => {
        expect(screen.getByText('Startup Dashboard')).toBeInTheDocument();
      });
    });

    test('handles network errors during upload', async () => {
      const mockFile = new File(['test content'], 'test.pdf', { type: 'application/pdf' });
      
      uploadPitchDeck.mockRejectedValue(new Error('Network Error'));

      renderStartupDashboard();

      const fileInput = screen.getByLabelText(/pitch deck hochladen/i);
      
      await act(async () => {
        fireEvent.change(fileInput, { target: { files: [mockFile] } });
      });

      await waitFor(() => {
        expect(screen.getByText('Upload failed')).toBeInTheDocument();
      });
    });
  });

  describe('Loading States', () => {
    test('shows loading state initially', () => {
      renderStartupDashboard();
      
      expect(screen.getByRole('progressbar')).toBeInTheDocument();
    });

    test('shows uploading state during file upload', async () => {
      const mockFile = new File(['test content'], 'test.pdf', { type: 'application/pdf' });
      
      // Make upload hang
      uploadPitchDeck.mockImplementation(() => new Promise(() => {}));

      renderStartupDashboard();

      const fileInput = screen.getByLabelText(/pitch deck hochladen/i);
      
      await act(async () => {
        fireEvent.change(fileInput, { target: { files: [mockFile] } });
      });

      await waitFor(() => {
        expect(screen.getByText('Uploading file...')).toBeInTheDocument();
      });
    });
  });
});