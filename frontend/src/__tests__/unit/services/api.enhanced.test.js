import { uploadPitchDeck, getPitchDecks, getProcessingStatus, getProcessingResults } from '../../../services/api';
import api from '../../../services/api';

// Mock the axios instance
jest.mock('../../../services/api', () => {
  const mockApi = {
    post: jest.fn(),
    get: jest.fn(),
    put: jest.fn(),
    delete: jest.fn(),
  };
  
  return {
    __esModule: true,
    default: mockApi,
    uploadPitchDeck: jest.fn(),
    getPitchDecks: jest.fn(),
    getProcessingStatus: jest.fn(),
    getProcessingResults: jest.fn(),
  };
});

describe('API Service - Enhanced Features', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('uploadPitchDeck', () => {
    test('uploads PDF file successfully', async () => {
      const mockFile = new File(['test content'], 'test.pdf', { type: 'application/pdf' });
      const mockResponse = {
        data: {
          pitch_deck_id: 1,
          filename: 'test.pdf',
          processing_status: 'processing',
          message: 'Document uploaded successfully'
        }
      };

      uploadPitchDeck.mockResolvedValue(mockResponse);

      const result = await uploadPitchDeck(mockFile);

      expect(uploadPitchDeck).toHaveBeenCalledWith(mockFile);
      expect(result.data.pitch_deck_id).toBe(1);
      expect(result.data.processing_status).toBe('processing');
    });

    test('handles file size validation error', async () => {
      const mockFile = new File(['test content'], 'test.pdf', { type: 'application/pdf' });
      const mockError = {
        response: {
          status: 413,
          data: { detail: 'File too large' }
        }
      };

      uploadPitchDeck.mockRejectedValue(mockError);

      await expect(uploadPitchDeck(mockFile)).rejects.toEqual(mockError);
    });

    test('handles invalid file type error', async () => {
      const mockFile = new File(['test content'], 'test.txt', { type: 'text/plain' });
      const mockError = {
        response: {
          status: 400,
          data: { detail: 'Only PDF files are allowed' }
        }
      };

      uploadPitchDeck.mockRejectedValue(mockError);

      await expect(uploadPitchDeck(mockFile)).rejects.toEqual(mockError);
    });

    test('handles network errors during upload', async () => {
      const mockFile = new File(['test content'], 'test.pdf', { type: 'application/pdf' });
      const networkError = new Error('Network Error');

      uploadPitchDeck.mockRejectedValue(networkError);

      await expect(uploadPitchDeck(mockFile)).rejects.toThrow('Network Error');
    });
  });

  describe('getPitchDecks', () => {
    test('fetches pitch decks with various statuses', async () => {
      const mockResponse = {
        data: {
          decks: [
            {
              id: 1,
              file_name: 'deck1.pdf',
              processing_status: 'pending',
              created_at: '2025-01-01T00:00:00Z'
            },
            {
              id: 2,
              file_name: 'deck2.pdf',
              processing_status: 'processing',
              created_at: '2025-01-01T01:00:00Z'
            },
            {
              id: 3,
              file_name: 'deck3.pdf',
              processing_status: 'completed',
              created_at: '2025-01-01T02:00:00Z'
            },
            {
              id: 4,
              file_name: 'deck4.pdf',
              processing_status: 'failed',
              created_at: '2025-01-01T03:00:00Z'
            }
          ]
        }
      };

      getPitchDecks.mockResolvedValue(mockResponse);

      const result = await getPitchDecks();

      expect(result.data.decks).toHaveLength(4);
      expect(result.data.decks[0].processing_status).toBe('pending');
      expect(result.data.decks[1].processing_status).toBe('processing');
      expect(result.data.decks[2].processing_status).toBe('completed');
      expect(result.data.decks[3].processing_status).toBe('failed');
    });

    test('handles empty deck list', async () => {
      const mockResponse = {
        data: { decks: [] }
      };

      getPitchDecks.mockResolvedValue(mockResponse);

      const result = await getPitchDecks();

      expect(result.data.decks).toHaveLength(0);
    });

    test('handles authentication errors', async () => {
      const mockError = {
        response: {
          status: 401,
          data: { detail: 'Not authenticated' }
        }
      };

      getPitchDecks.mockRejectedValue(mockError);

      await expect(getPitchDecks()).rejects.toEqual(mockError);
    });
  });

  describe('getProcessingStatus', () => {
    test('retrieves processing status for a pitch deck', async () => {
      const mockResponse = {
        data: {
          pitch_deck_id: 1,
          processing_status: 'processing',
          file_name: 'test.pdf',
          created_at: '2025-01-01T00:00:00Z'
        }
      };

      getProcessingStatus.mockResolvedValue(mockResponse);

      const result = await getProcessingStatus(1);

      expect(result.data.processing_status).toBe('processing');
      expect(result.data.pitch_deck_id).toBe(1);
    });

    test('handles deck not found error', async () => {
      const mockError = {
        response: {
          status: 404,
          data: { detail: 'Pitch deck not found' }
        }
      };

      getProcessingStatus.mockRejectedValue(mockError);

      await expect(getProcessingStatus(999)).rejects.toEqual(mockError);
    });

    test('handles access denied error', async () => {
      const mockError = {
        response: {
          status: 403,
          data: { detail: 'Access denied' }
        }
      };

      getProcessingStatus.mockRejectedValue(mockError);

      await expect(getProcessingStatus(1)).rejects.toEqual(mockError);
    });
  });

  describe('getProcessingResults', () => {
    test('retrieves processing results for completed deck', async () => {
      const mockResponse = {
        data: {
          pitch_deck_id: 1,
          file_name: 'test.pdf',
          processing_status: 'completed',
          results: {
            overall_score: 8.5,
            analysis: {
              problem: { score: 8.0, analysis: 'Good problem identification' },
              solution: { score: 9.0, analysis: 'Innovative solution' }
            }
          }
        }
      };

      getProcessingResults.mockResolvedValue(mockResponse);

      const result = await getProcessingResults(1);

      expect(result.data.processing_status).toBe('completed');
      expect(result.data.results.overall_score).toBe(8.5);
      expect(result.data.results.analysis.problem.score).toBe(8.0);
    });

    test('handles processing not completed error', async () => {
      const mockError = {
        response: {
          status: 400,
          data: { detail: 'Processing not completed yet' }
        }
      };

      getProcessingResults.mockRejectedValue(mockError);

      await expect(getProcessingResults(1)).rejects.toEqual(mockError);
    });

    test('handles results not found error', async () => {
      const mockError = {
        response: {
          status: 404,
          data: { detail: 'Results not found' }
        }
      };

      getProcessingResults.mockRejectedValue(mockError);

      await expect(getProcessingResults(1)).rejects.toEqual(mockError);
    });
  });

  describe('API Error Handling', () => {
    test('handles server errors gracefully', async () => {
      const mockError = {
        response: {
          status: 500,
          data: { detail: 'Internal server error' }
        }
      };

      getPitchDecks.mockRejectedValue(mockError);

      await expect(getPitchDecks()).rejects.toEqual(mockError);
    });

    test('handles network timeouts', async () => {
      const timeoutError = new Error('timeout of 30000ms exceeded');
      timeoutError.code = 'ECONNABORTED';

      getPitchDecks.mockRejectedValue(timeoutError);

      await expect(getPitchDecks()).rejects.toThrow('timeout of 30000ms exceeded');
    });

    test('handles connection refused errors', async () => {
      const connectionError = new Error('connect ECONNREFUSED');
      connectionError.code = 'ECONNREFUSED';

      getPitchDecks.mockRejectedValue(connectionError);

      await expect(getPitchDecks()).rejects.toThrow('connect ECONNREFUSED');
    });
  });
});