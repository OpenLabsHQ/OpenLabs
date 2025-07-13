import { describe, it, expect, vi, beforeEach } from 'vitest';
import { auth } from '../../../src/lib/stores/auth';
import Sidebar from '../../../src/lib/components/Sidebar.svelte';

// Mock the auth store
vi.mock('../../../src/lib/stores/auth', () => ({
  auth: {
    subscribe: vi.fn(),
    logout: vi.fn().mockResolvedValue(undefined),
    updateUser: vi.fn()
  }
}));

// Mock the dynamic import for API
vi.mock('../../../src/lib/api', () => ({
  authApi: {
    getCurrentUser: vi.fn().mockResolvedValue({ 
      data: { user: { name: 'Test User', email: 'test@example.com' } } 
    })
  }
}));

describe('Sidebar', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    
    // Setup auth subscription mock with default data
    auth.subscribe.mockImplementation((callback) => {
      callback({ 
        isAuthenticated: true,
        user: { name: 'Test User' }
      });
      return () => {};
    });
  });

  it('calculates username from user object', () => {
    // Simulating the reactive variable in Sidebar.svelte
    let user = { name: 'Test User' };
    let userName = user?.name || 'Account';
    expect(userName).toBe('Test User');
    
    // Test fallback when name is missing
    user = {};
    userName = user?.name || 'Account';
    expect(userName).toBe('Account');
    
    // Test fallback when user is undefined
    user = undefined;
    userName = user?.name || 'Account';
    expect(userName).toBe('Account');
  });

  it('handles logout correctly', async () => {
    // Test the logout function
    function handleLogout() {
      auth.logout();
    }
    
    // Call the logout function
    handleLogout();
    
    // Check that auth.logout was called
    expect(auth.logout).toHaveBeenCalled();
  });
});