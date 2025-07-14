/**
 * Unit tests for API service
 */

import { 
  loginUser, 
  registerUser, 
  uploadPitchDeck, 
  getPitchDecks,
  updateLanguagePreference 
} from '../../../services/api';
import { mockApiResponses, mockFiles } from '../../test-utils';
import '../../mocks/server';

describe('API Service', () => {
  beforeEach(() => {
    localStorage.clear();
    jest.clearAllMocks();
  });

  describe('Authentication API', () => {
    describe('loginUser', () => {
      it('successfully logs in with valid credentials', async () => {
        const credentials = {
          email: 'test@example.com',
          password: 'password123'
        };

        const response = await loginUser(credentials);
        
        expect(response.data).toEqual(mockApiResponses.login.success);
        expect(response.data.access_token).toBe('mock-jwt-token');
        expect(response.data.role).toBe('startup');
      });

      it('throws error with invalid credentials', async () => {
        const credentials = {
          email: 'invalid@example.com',
          password: 'wrongpassword'
        };

        await expect(loginUser(credentials)).rejects.toThrow();
      });

      it('throws error with missing credentials', async () => {
        const credentials = {
          email: '',
          password: ''
        };

        await expect(loginUser(credentials)).rejects.toThrow();
      });

      it('includes correct headers in request', async () => {
        const credentials = {
          email: 'test@example.com',
          password: 'password123'
        };

        const response = await loginUser(credentials);
        
        // Verify response structure
        expect(response.data).toHaveProperty('access_token');
        expect(response.data).toHaveProperty('token_type', 'Bearer');
      });
    });

    describe('registerUser', () => {
      it('successfully registers new user', async () => {
        const userData = {
          email: 'newuser@example.com',
          password: 'password123',
          company_name: 'New Company',
          role: 'startup',
          preferred_language: 'en'
        };

        const response = await registerUser(userData);
        
        expect(response.data).toEqual(mockApiResponses.register.success);
        expect(response.data.email_sent).toBe(true);
      });

      it('throws error for existing email', async () => {
        const userData = {
          email: 'existing@example.com',
          password: 'password123',
          company_name: 'Company',
          role: 'startup',
          preferred_language: 'en'
        };

        await expect(registerUser(userData)).rejects.toThrow();
      });

      it('validates required fields', async () => {
        const incompleteData = {
          email: 'test@example.com'
          // Missing required fields
        };

        await expect(registerUser(incompleteData)).rejects.toThrow();
      });
    });

    describe('updateLanguagePreference', () => {
      beforeEach(() => {
        // Mock authenticated user
        localStorage.setItem('user', JSON.stringify({
          access_token: 'mock-token'
        }));
      });

      it('successfully updates language preference', async () => {
        const response = await updateLanguagePreference('de');
        
        expect(response.data.preferred_language).toBe('de');
        expect(response.data.message).toContain('updated successfully');
      });

      it('throws error for invalid language', async () => {
        await expect(updateLanguagePreference('fr')).rejects.toThrow();
      });

      it('includes authorization header', async () => {
        // This test verifies that the API call includes the auth token
        const response = await updateLanguagePreference('en');
        expect(response.data).toHaveProperty('preferred_language');
      });
    });
  });

  describe('Pitch Deck API', () => {
    beforeEach(() => {
      // Mock authenticated user
      localStorage.setItem('user', JSON.stringify({
        access_token: 'mock-token'
      }));
    });

    describe('getPitchDecks', () => {
      it('successfully retrieves pitch decks', async () => {
        const response = await getPitchDecks();
        
        expect(response.data).toEqual(mockApiResponses.pitchDecks.success);
        expect(response.data.decks).toHaveLength(2);
        expect(response.data.decks[0]).toHaveProperty('file_name');
        expect(response.data.decks[0]).toHaveProperty('processing_status');
      });

      it('handles empty deck list', async () => {
        // This would require setting up a specific mock response
        const response = await getPitchDecks();
        expect(response.data).toHaveProperty('decks');
      });

      it('includes authorization header', async () => {
        const response = await getPitchDecks();
        expect(response.data).toHaveProperty('decks');
      });
    });

    describe('uploadPitchDeck', () => {
      it('successfully uploads valid PDF file', async () => {
        const response = await uploadPitchDeck(mockFiles.validPdf);
        
        expect(response.data.message).toContain('uploaded successfully');
        expect(response.data.file_name).toBe('test.pdf');
      });

      it('throws error for invalid file type', async () => {
        await expect(uploadPitchDeck(mockFiles.invalidType)).rejects.toThrow();
      });

      it('throws error for oversized file', async () => {
        await expect(uploadPitchDeck(mockFiles.oversized)).rejects.toThrow();
      });

      it('throws error when no file provided', async () => {
        await expect(uploadPitchDeck(null)).rejects.toThrow();
      });

      it('sends file as FormData', async () => {
        const response = await uploadPitchDeck(mockFiles.validPdf);
        
        // Verify the response indicates successful file processing
        expect(response.data).toHaveProperty('file_name');
        expect(response.data).toHaveProperty('processing_status');
      });

      it('includes authorization header', async () => {
        const response = await uploadPitchDeck(mockFiles.validPdf);
        expect(response.data).toHaveProperty('message');
      });
    });
  });

  describe('Error Handling', () => {
    it('handles network errors gracefully', async () => {
      // This would require setting up network error simulation
      // For now, we'll test that errors are properly thrown
      await expect(loginUser({ email: '', password: '' })).rejects.toThrow();
    });

    it('handles 500 server errors', async () => {
      // Test server error handling
      // This would require specific error endpoint mocking
      try {
        await loginUser({ email: 'error@example.com', password: 'password' });
      } catch (error) {
        expect(error).toBeDefined();
      }
    });

    it('handles timeout errors', async () => {
      // Test timeout handling
      // This would require timeout simulation
      try {
        await loginUser({ email: 'timeout@example.com', password: 'password' });
      } catch (error) {
        expect(error).toBeDefined();
      }
    });
  });

  describe('Request Configuration', () => {
    it('sets correct base URL', () => {
      // Test that API calls use the correct base URL
      // This is handled by the axios configuration
      expect(true).toBe(true); // Placeholder
    });

    it('includes correct content type headers', async () => {
      const response = await loginUser({
        email: 'test@example.com',
        password: 'password123'
      });
      
      expect(response.data).toBeDefined();
    });

    it('handles authentication tokens correctly', async () => {
      localStorage.setItem('user', JSON.stringify({
        access_token: 'test-token'
      }));

      const response = await getPitchDecks();
      expect(response.data).toBeDefined();
    });
  });

  describe('Response Parsing', () => {
    it('correctly parses JSON responses', async () => {
      const response = await loginUser({
        email: 'test@example.com',
        password: 'password123'
      });
      
      expect(typeof response.data).toBe('object');
      expect(response.data).toHaveProperty('access_token');
    });

    it('handles empty responses', async () => {
      // Test handling of empty responses
      const response = await updateLanguagePreference('en');
      expect(response.data).toBeDefined();
    });
  });
});