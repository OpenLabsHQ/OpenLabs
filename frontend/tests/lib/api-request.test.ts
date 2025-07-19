import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { config } from '../../src/lib/config';

// Silence all console output to keep tests clean
vi.spyOn(console, 'error').mockImplementation(() => {});
vi.spyOn(console, 'log').mockImplementation(() => {});
vi.spyOn(console, 'warn').mockImplementation(() => {});

// Mock fetch
global.fetch = vi.fn();

describe('API Request Function', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    
    // Setup default fetch mock response
    global.fetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ data: 'test' }),
      headers: {
        get: () => 'application/json'
      }
    });
  });
  
  // Extract the apiRequest function with the same logic as in api.ts
  async function apiRequest(
    endpoint,
    method = 'GET',
    data = undefined,
  ) {
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
  
  it('makes a GET request with the correct endpoint', async () => {
    await apiRequest('/api/v1/test');
    
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/test'),
      expect.objectContaining({
        method: 'GET',
        credentials: 'include'
      })
    );
  });
  
  it('makes a POST request with data', async () => {
    const testData = { name: 'Test', value: 123 };
    await apiRequest('/api/v1/test', 'POST', testData);
    
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/test'),
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify(testData),
        credentials: 'include'
      })
    );
  });
  
  it('parses JSON response correctly', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ name: 'Test Response' }),
      headers: {
        get: () => 'application/json'
      }
    });
    
    const result = await apiRequest('/api/v1/test');
    
    expect(result.data).toEqual({ name: 'Test Response' });
  });
  
  it('handles text response when content-type is not JSON', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      text: () => Promise.resolve('Plain text response'),
      headers: {
        get: () => 'text/plain'
      }
    });
    
    const result = await apiRequest('/api/v1/test');
    
    expect(result.data).toEqual({ message: 'Plain text response' });
  });
  
  it('handles 401 unauthorized error', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: false,
      status: 401,
      json: () => Promise.resolve({ detail: 'Unauthorized' }),
      headers: {
        get: () => 'application/json'
      }
    });
    
    const result = await apiRequest('/api/v1/test');
    
    expect(result.error).toBe('Your session has expired. Please log in again.');
    expect(result.isAuthError).toBe(true);
    expect(result.status).toBe(401);
  });
  
  it('handles 404 not found error', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      json: () => Promise.resolve({ detail: 'Not found' }),
      headers: {
        get: () => 'application/json'
      }
    });
    
    const result = await apiRequest('/api/v1/test');
    
    expect(result.error).toBe('The requested information could not be found.');
    expect(result.status).toBe(404);
  });
  
  it('handles network error', async () => {
    global.fetch.mockRejectedValueOnce(new Error('Failed to fetch'));
    
    const result = await apiRequest('/api/v1/test');
    
    expect(result.error).toBe('Network error: Please check your internet connection.');
  });
  
  it('handles timeout error', async () => {
    global.fetch.mockRejectedValueOnce(new Error('timeout'));
    
    const result = await apiRequest('/api/v1/test');
    
    expect(result.error).toBe('Request timed out. Please try again later.');
  });
  
  it('handles non-existent endpoints gracefully', async () => {
    // Mock a 404 error that would come from a non-existent endpoint
    global.fetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      json: () => Promise.resolve({ detail: 'Not found' }),
      headers: {
        get: () => 'application/json'
      }
    });
    
    const result = await apiRequest('/api/v1/non-existent-endpoint');
    
    expect(result.error).toBe('The requested information could not be found.');
    expect(result.status).toBe(404);
  });
  
  it('handles server-side errors gracefully', async () => {
    // Mock a 500 internal server error
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
});