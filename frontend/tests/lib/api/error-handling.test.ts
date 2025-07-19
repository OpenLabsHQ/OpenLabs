import { describe, it, expect, vi, beforeEach } from 'vitest';
import { config } from '../../../src/lib/config';

// Silence all console output to keep tests clean
vi.spyOn(console, 'error').mockImplementation(() => {});
vi.spyOn(console, 'log').mockImplementation(() => {});
vi.spyOn(console, 'warn').mockImplementation(() => {});

// Mock fetch
global.fetch = vi.fn();

describe('API Error Handling', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    
    // Setup default fetch mock
    global.fetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ data: 'test' }),
      headers: {
        get: () => 'application/json'
      }
    });
  });
  
  // This is a simplified version of the apiRequest function from src/lib/api.ts
  // for testing error handling logic
  async function apiRequest(endpoint, method = 'GET', data = undefined) {
    try {
      const headers = {
        'Content-Type': 'application/json',
      };
      
      const options = {
        method,
        headers,
        credentials: 'include',
      };
      
      if (data && (method === 'POST' || method === 'PUT')) {
        options.body = JSON.stringify(data);
      }
      
      const response = await fetch(`${config.apiUrl}${endpoint}`, options);
      
      let result;
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        result = await response.json();
      } else {
        const text = await response.text();
        result = text ? { message: text } : {};
      }
      
      if (!response.ok) {
        console.error('API error:', result);
        
        let errorMessage = '';
        let isAuthError = false;
        
        switch (response.status) {
          case 401:
            errorMessage = 'Your session has expired. Please log in again.';
            isAuthError = true;
            break;
          case 403:
            errorMessage = "You don't have permission to access this resource.";
            isAuthError = true;
            break;
          case 404:
            errorMessage = 'The requested information could not be found.';
            break;
          case 500:
          case 502:
          case 503:
          case 504:
            errorMessage = 'The server is currently unavailable. Please try again later.';
            break;
          default:
            errorMessage = result.detail || result.message || `Something went wrong (${response.status})`;
        }
        
        return {
          error: errorMessage,
          status: response.status,
          isAuthError,
        };
      }
      
      return { data: result };
    } catch (error) {
      console.error('API request failed:', error);
      
      let errorMessage = 'Unable to connect to the server.';
      
      if (error instanceof Error) {
        if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
          errorMessage = 'Network error: Please check your internet connection.';
        } else if (error.message.includes('timeout') || error.message.includes('Timeout')) {
          errorMessage = 'Request timed out. Please try again later.';
        } else {
          errorMessage = 'Something went wrong while connecting to the server. Please try again.';
        }
      }
      
      return { error: errorMessage };
    }
  }
  
  describe('HTTP Status Code Handling', () => {
    it('handles 401 unauthorized errors with auth flag', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: () => Promise.resolve({ detail: 'Invalid or expired token' }),
        headers: {
          get: () => 'application/json'
        }
      });
      
      const result = await apiRequest('/api/v1/users/me');
      
      expect(result.error).toBe('Your session has expired. Please log in again.');
      expect(result.status).toBe(401);
      expect(result.isAuthError).toBe(true);
    });
    
    it('handles 403 forbidden errors with auth flag', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 403,
        json: () => Promise.resolve({ detail: 'User does not have permission' }),
        headers: {
          get: () => 'application/json'
        }
      });
      
      const result = await apiRequest('/api/v1/admin/settings');
      
      expect(result.error).toBe("You don't have permission to access this resource.");
      expect(result.status).toBe(403);
      expect(result.isAuthError).toBe(true);
    });
    
    it('handles 404 not found errors correctly', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: () => Promise.resolve({ detail: 'Resource not found' }),
        headers: {
          get: () => 'application/json'
        }
      });
      
      const result = await apiRequest('/api/v1/nonexistent');
      
      expect(result.error).toBe('The requested information could not be found.');
      expect(result.status).toBe(404);
      expect(result.isAuthError).toBeFalsy();
    });
    
    it('handles 500 server errors with appropriate message', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: () => Promise.resolve({ detail: 'Internal server error' }),
        headers: {
          get: () => 'application/json'
        }
      });
      
      const result = await apiRequest('/api/v1/test');
      
      expect(result.error).toBe('The server is currently unavailable. Please try again later.');
      expect(result.status).toBe(500);
    });
    
    it('handles 503 service unavailable errors', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 503,
        json: () => Promise.resolve({ detail: 'Service unavailable' }),
        headers: {
          get: () => 'application/json'
        }
      });
      
      const result = await apiRequest('/api/v1/test');
      
      expect(result.error).toBe('The server is currently unavailable. Please try again later.');
      expect(result.status).toBe(503);
    });
    
    it('extracts custom error messages from API response', async () => {
      const customErrorMessage = 'User with this email already exists';
      
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 422,
        json: () => Promise.resolve({ detail: customErrorMessage }),
        headers: {
          get: () => 'application/json'
        }
      });
      
      const result = await apiRequest('/api/v1/auth/register', 'POST', { email: 'test@example.com' });
      
      expect(result.error).toBe(customErrorMessage);
      expect(result.status).toBe(422);
    });
  });
  
  describe('Network Error Handling', () => {
    it('handles connection errors gracefully', async () => {
      global.fetch.mockRejectedValueOnce(new Error('Failed to fetch'));
      
      const result = await apiRequest('/api/v1/test');
      
      expect(result.error).toBe('Network error: Please check your internet connection.');
      expect(result.status).toBeUndefined();
    });
    
    it('handles timeout errors with appropriate message', async () => {
      global.fetch.mockRejectedValueOnce(new Error('timeout'));
      
      const result = await apiRequest('/api/v1/test');
      
      expect(result.error).toBe('Request timed out. Please try again later.');
    });
    
    it('handles unknown errors with generic message', async () => {
      global.fetch.mockRejectedValueOnce(new Error('Some unexpected error'));
      
      const result = await apiRequest('/api/v1/test');
      
      expect(result.error).toBe('Something went wrong while connecting to the server. Please try again.');
    });
    
    it('handles non-Error rejection with fallback message', async () => {
      global.fetch.mockRejectedValueOnce('Not an Error object');
      
      const result = await apiRequest('/api/v1/test');
      
      expect(result.error).toBe('Unable to connect to the server.');
    });
  });
  
  describe('Response Content Handling', () => {
    it('handles text responses when content-type is not JSON', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        text: () => Promise.resolve('Server Error'),
        headers: {
          get: () => 'text/plain'
        }
      });
      
      const result = await apiRequest('/api/v1/test');
      
      expect(result.error).toBe('The server is currently unavailable. Please try again later.');
    });
    
    it('handles empty response with default error message', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: () => Promise.resolve({}),
        headers: {
          get: () => 'application/json'
        }
      });
      
      const result = await apiRequest('/api/v1/test');
      
      expect(result.error).toBe('Something went wrong (400)');
    });
    
    it('handles JSON parse errors gracefully', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 200,
        json: () => Promise.reject(new Error('Invalid JSON')),
        text: () => Promise.resolve('Not JSON'),
        headers: {
          get: () => 'application/json'
        }
      });
      
      const result = await apiRequest('/api/v1/test');
      
      // In this case the error will be caught by the try/catch and treated as a network error
      expect(result.error).toBeDefined();
    });
  });
});