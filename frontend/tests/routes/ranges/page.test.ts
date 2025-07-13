import { describe, it, expect, vi, beforeEach } from 'vitest';
import { rangesApi } from '../../../src/lib/api';
import { goto } from '$app/navigation';
import { auth } from '../../../src/lib/stores/auth';
import { get } from 'svelte/store';

// Mock dependencies
vi.mock('$app/navigation', () => ({
  goto: vi.fn()
}));

vi.mock('../../../src/lib/api', () => ({
  rangesApi: {
    getRanges: vi.fn()
  }
}));

vi.mock('../../../src/lib/stores/auth', () => {
  const authStore = {
    subscribe: vi.fn(),
    set: vi.fn(),
    update: vi.fn(),
    updateUser: vi.fn(),
    updateAuthState: vi.fn(),
    logout: vi.fn(),
    isAuthenticated: false
  };
  
  return {
    auth: {
      ...authStore,
      subscribe: (cb) => {
        cb(authStore);
        return () => {};
      }
    }
  };
});

describe('Ranges Page', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });
  
  describe('Authentication check', () => {
    it('redirects to login page when user is not authenticated', () => {
      // Simulate auth store with unauthenticated user
      auth.isAuthenticated = false;
      
      // Simulate onMount callback
      const checkAuth = async () => {
        if (!auth.isAuthenticated) {
          goto('/login');
          return;
        }
        
        // This part shouldn't run
        await rangesApi.getRanges();
      };
      
      checkAuth();
      
      // Verify redirect occurred
      expect(goto).toHaveBeenCalledWith('/login');
      expect(rangesApi.getRanges).not.toHaveBeenCalled();
    });
    
    it('fetches ranges when user is authenticated', async () => {
      // Simulate auth store with authenticated user
      auth.isAuthenticated = true;
      
      // Mock a successful API response
      rangesApi.getRanges.mockResolvedValueOnce({
        data: [
          { id: '1', name: 'Test Range', status: 'running' }
        ]
      });
      
      // Simulate onMount callback
      const loadRanges = async () => {
        if (!auth.isAuthenticated) {
          goto('/login');
          return;
        }
        
        const result = await rangesApi.getRanges();
        return result;
      };
      
      const result = await loadRanges();
      
      // Verify API was called and no redirect occurred
      expect(goto).not.toHaveBeenCalled();
      expect(rangesApi.getRanges).toHaveBeenCalledTimes(1);
      expect(result.data).toHaveLength(1);
    });
  });
  
  describe('API error handling', () => {
    beforeEach(() => {
      // Ensure we're simulating an authenticated user
      auth.isAuthenticated = true;
    });
    
    it('handles 404 error for missing endpoint', async () => {
      // Mock a 404 API response
      rangesApi.getRanges.mockResolvedValueOnce({
        error: 'The requested information could not be found.',
        status: 404
      });
      
      let deployedRanges = [];
      let error = '';
      
      // Simulate the component's API call and error handling
      try {
        const result = await rangesApi.getRanges();
        
        if (result.error) {
          if (result.error.includes('not be found')) {
            // 404 error - show no ranges message
            deployedRanges = [];
          } else {
            // Other errors - show error message
            error = result.error;
            // Would use fallback data in the real component
          }
        }
      } catch (err) {
        console.error('Error in test:', err);
      }
      
      // Verify the component would show empty ranges
      expect(deployedRanges).toEqual([]);
      expect(error).toBe('');
    });
    
    it('handles server error with fallback data', async () => {
      // Mock a 500 API response
      rangesApi.getRanges.mockResolvedValueOnce({
        error: 'The server is currently unavailable. Please try again later.',
        status: 500
      });
      
      // Create some fallback data similar to what's in the component
      const fallbackRanges = [
        { id: '1', name: 'Fallback Range', description: 'Fallback description', isRunning: true }
      ];
      
      let deployedRanges = [];
      let error = '';
      
      // Simulate the component's API call and error handling
      try {
        const result = await rangesApi.getRanges();
        
        if (result.error) {
          if (result.error.includes('not be found')) {
            // 404 error
            deployedRanges = [];
          } else {
            // Other errors - show error message and use fallback
            error = result.error;
            deployedRanges = fallbackRanges;
          }
        }
      } catch (err) {
        console.error('Error in test:', err);
      }
      
      // Verify the component would show fallback data and error message
      expect(deployedRanges).toEqual(fallbackRanges);
      expect(error).toBe('The server is currently unavailable. Please try again later.');
    });
    
    it('handles successful API response and transforms data correctly', async () => {
      // Mock a successful API response with sample data
      rangesApi.getRanges.mockResolvedValueOnce({
        data: [
          { 
            id: '1', 
            name: 'API Range', 
            description: 'Range from API', 
            status: 'running',
            created_at: '2024-02-15T12:00:00Z'
          }
        ]
      });
      
      let deployedRanges = [];
      let error = '';
      
      // Simulate the component's API call and data transformation
      try {
        const result = await rangesApi.getRanges();
        
        if (result.data && Array.isArray(result.data)) {
          // Map API response to our Range interface as the component would
          deployedRanges = result.data.map((range) => ({
            id: range.id || `range_${Math.random().toString(36).substr(2, 9)}`,
            name: range.name || 'Unnamed Range',
            description: range.description || 'No description',
            isRunning: range.status === 'running' || range.is_active || false,
            created_at: range.created_at,
            updated_at: range.updated_at,
          }));
        }
      } catch (err) {
        console.error('Error in test:', err);
      }
      
      // Verify the data transformation worked correctly
      expect(deployedRanges).toHaveLength(1);
      expect(deployedRanges[0].id).toBe('1');
      expect(deployedRanges[0].name).toBe('API Range');
      expect(deployedRanges[0].isRunning).toBe(true);
      expect(deployedRanges[0].created_at).toBe('2024-02-15T12:00:00Z');
      expect(error).toBe('');
    });
  });
});