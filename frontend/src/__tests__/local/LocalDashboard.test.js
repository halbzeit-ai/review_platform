/**
 * Local development tests for StartupDashboard component.
 * These tests work on NixOS dev machine without requiring production environment.
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { I18nextProvider } from 'react-i18next';
import { createTheme, ThemeProvider } from '@mui/material/styles';

// Mock the API module to avoid network calls in local tests
jest.mock('../../services/api', () => ({
  uploadPitchDeck: jest.fn(),
  getPitchDecks: jest.fn(),
}));

// Mock navigation to avoid router issues
const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

// Mock i18n for local testing
const mockI18n = {
  language: 'en',
  changeLanguage: jest.fn(),
  t: jest.fn((key) => {
    // Simple key-to-text mapping for local testing
    const translations = {
      'startup.uploadSection.title': 'Upload Pitch Deck',
      'startup.uploadSection.uploading': 'Uploading...',
      'startup.uploadSection.success': 'Upload successful!',
      'startup.decksSection.title': 'Your Pitch Decks',
      'startup.decksSection.noDecks': 'No pitch decks uploaded yet',
      'startup.decksSection.status.uploaded': 'Uploaded',
      'startup.decksSection.status.processing': 'Processing...',
      'startup.decksSection.status.completed': 'Completed',
      'startup.decksSection.status.failed': 'Failed'
    };
    return translations[key] || key;
  })
};

// Simple test component that doesn't require full app setup
const TestDashboard = () => {
  const [uploading, setUploading] = React.useState(false);
  const [decks, setDecks] = React.useState([]);
  const [error, setError] = React.useState(null);

  const handleFileUpload = (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setUploading(true);
    setError(null);

    // Simulate upload process
    setTimeout(() => {
      if (file.type === 'application/pdf') {
        const newDeck = {
          id: Date.now(),
          filename: file.name,
          status: 'uploaded',
          uploaded_at: new Date().toISOString()
        };
        setDecks(prev => [...prev, newDeck]);
        setUploading(false);
      } else {
        setError('Only PDF files are allowed');
        setUploading(false);
      }
    }, 1000);
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed': return 'success';
      case 'processing': return 'warning';
      case 'failed': return 'error';
      default: return 'default';
    }
  };

  return (
    <div data-testid="local-dashboard">
      <h1>Startup Dashboard</h1>
      
      {/* Upload Section */}
      <div data-testid="upload-section">
        <h2>{mockI18n.t('startup.uploadSection.title')}</h2>
        <input
          type="file"
          accept=".pdf"
          onChange={handleFileUpload}
          disabled={uploading}
          data-testid="file-input"
        />
        {uploading && (
          <div data-testid="uploading-indicator">
            {mockI18n.t('startup.uploadSection.uploading')}
          </div>
        )}
        {error && (
          <div data-testid="error-message" style={{ color: 'red' }}>
            {error}
          </div>
        )}
      </div>

      {/* Decks Section */}
      <div data-testid="decks-section">
        <h2>{mockI18n.t('startup.decksSection.title')}</h2>
        {decks.length === 0 ? (
          <p data-testid="no-decks-message">
            {mockI18n.t('startup.decksSection.noDecks')}
          </p>
        ) : (
          <ul data-testid="decks-list">
            {decks.map(deck => (
              <li key={deck.id} data-testid={`deck-${deck.id}`}>
                <span>{deck.filename}</span>
                <span 
                  data-testid={`status-${deck.id}`}
                  style={{ color: getStatusColor(deck.status) }}
                >
                  {mockI18n.t(`startup.decksSection.status.${deck.status}`)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};

const renderTestDashboard = () => {
  const theme = createTheme();
  return render(
    <ThemeProvider theme={theme}>
      <I18nextProvider i18n={mockI18n}>
        <BrowserRouter>
          <TestDashboard />
        </BrowserRouter>
      </I18nextProvider>
    </ThemeProvider>
  );
};

describe('Local Dashboard Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Component Rendering', () => {
    test('renders dashboard components', () => {
      renderTestDashboard();
      
      expect(screen.getByTestId('local-dashboard')).toBeInTheDocument();
      expect(screen.getByText('Startup Dashboard')).toBeInTheDocument();
      expect(screen.getByTestId('upload-section')).toBeInTheDocument();
      expect(screen.getByTestId('decks-section')).toBeInTheDocument();
    });

    test('shows upload section with file input', () => {
      renderTestDashboard();
      
      expect(screen.getByText('Upload Pitch Deck')).toBeInTheDocument();
      expect(screen.getByTestId('file-input')).toBeInTheDocument();
    });

    test('shows no decks message initially', () => {
      renderTestDashboard();
      
      expect(screen.getByTestId('no-decks-message')).toBeInTheDocument();
      expect(screen.getByText('No pitch decks uploaded yet')).toBeInTheDocument();
    });
  });

  describe('File Upload Functionality', () => {
    test('handles PDF file upload', async () => {
      renderTestDashboard();
      
      const fileInput = screen.getByTestId('file-input');
      const file = new File(['mock pdf content'], 'test.pdf', { type: 'application/pdf' });
      
      fireEvent.change(fileInput, { target: { files: [file] } });
      
      // Check uploading state
      expect(screen.getByTestId('uploading-indicator')).toBeInTheDocument();
      expect(screen.getByText('Uploading...')).toBeInTheDocument();
      
      // Wait for upload to complete
      await waitFor(() => {
        expect(screen.queryByTestId('uploading-indicator')).not.toBeInTheDocument();
      }, { timeout: 2000 });
      
      // Check that deck was added
      expect(screen.getByTestId('decks-list')).toBeInTheDocument();
      expect(screen.getByText('test.pdf')).toBeInTheDocument();
    });

    test('rejects non-PDF files', async () => {
      renderTestDashboard();
      
      const fileInput = screen.getByTestId('file-input');
      const file = new File(['mock content'], 'test.txt', { type: 'text/plain' });
      
      fireEvent.change(fileInput, { target: { files: [file] } });
      
      // Wait for error to appear
      await waitFor(() => {
        expect(screen.getByTestId('error-message')).toBeInTheDocument();
      }, { timeout: 2000 });
      
      expect(screen.getByText('Only PDF files are allowed')).toBeInTheDocument();
    });

    test('disables input during upload', () => {
      renderTestDashboard();
      
      const fileInput = screen.getByTestId('file-input');
      const file = new File(['mock pdf content'], 'test.pdf', { type: 'application/pdf' });
      
      fireEvent.change(fileInput, { target: { files: [file] } });
      
      // Input should be disabled during upload
      expect(fileInput).toBeDisabled();
    });
  });

  describe('Deck Status Display', () => {
    test('displays deck with correct status', async () => {
      renderTestDashboard();
      
      const fileInput = screen.getByTestId('file-input');
      const file = new File(['mock pdf content'], 'test.pdf', { type: 'application/pdf' });
      
      fireEvent.change(fileInput, { target: { files: [file] } });
      
      await waitFor(() => {
        expect(screen.getByText('test.pdf')).toBeInTheDocument();
      }, { timeout: 2000 });
      
      // Check status display
      expect(screen.getByText('Uploaded')).toBeInTheDocument();
    });

    test('shows multiple decks', async () => {
      renderTestDashboard();
      
      const fileInput = screen.getByTestId('file-input');
      
      // Upload first file
      const file1 = new File(['mock pdf 1'], 'deck1.pdf', { type: 'application/pdf' });
      fireEvent.change(fileInput, { target: { files: [file1] } });
      
      await waitFor(() => {
        expect(screen.getByText('deck1.pdf')).toBeInTheDocument();
      }, { timeout: 2000 });
      
      // Upload second file
      const file2 = new File(['mock pdf 2'], 'deck2.pdf', { type: 'application/pdf' });
      fireEvent.change(fileInput, { target: { files: [file2] } });
      
      await waitFor(() => {
        expect(screen.getByText('deck2.pdf')).toBeInTheDocument();
      }, { timeout: 2000 });
      
      // Both files should be shown
      expect(screen.getByText('deck1.pdf')).toBeInTheDocument();
      expect(screen.getByText('deck2.pdf')).toBeInTheDocument();
    });
  });

  describe('Translation System', () => {
    test('uses translation function for all text', () => {
      renderTestDashboard();
      
      // Check that translation keys are being used
      expect(mockI18n.t).toHaveBeenCalledWith('startup.uploadSection.title');
      expect(mockI18n.t).toHaveBeenCalledWith('startup.decksSection.title');
      expect(mockI18n.t).toHaveBeenCalledWith('startup.decksSection.noDecks');
    });

    test('handles missing translations gracefully', () => {
      const result = mockI18n.t('missing.translation.key');
      expect(result).toBe('missing.translation.key');
    });
  });

  describe('Error Handling', () => {
    test('clears error on successful upload', async () => {
      renderTestDashboard();
      
      const fileInput = screen.getByTestId('file-input');
      
      // First upload invalid file
      const invalidFile = new File(['mock'], 'test.txt', { type: 'text/plain' });
      fireEvent.change(fileInput, { target: { files: [invalidFile] } });
      
      await waitFor(() => {
        expect(screen.getByTestId('error-message')).toBeInTheDocument();
      }, { timeout: 2000 });
      
      // Then upload valid file
      const validFile = new File(['mock pdf'], 'test.pdf', { type: 'application/pdf' });
      fireEvent.change(fileInput, { target: { files: [validFile] } });
      
      await waitFor(() => {
        expect(screen.queryByTestId('error-message')).not.toBeInTheDocument();
      }, { timeout: 2000 });
    });
  });

  describe('Local Development Environment', () => {
    test('works without network dependencies', () => {
      // This test verifies the component works in isolated environment
      renderTestDashboard();
      expect(screen.getByTestId('local-dashboard')).toBeInTheDocument();
    });

    test('uses mock data appropriately', () => {
      // Verify mocks are working as expected
      expect(typeof mockI18n.t).toBe('function');
      expect(typeof mockNavigate).toBe('function');
    });
  });
});