import { describe, it, expect, vi, beforeEach } from 'vitest';
import { auth } from '../../../src/lib/stores/auth';

// Mock the API
vi.mock('../../../src/lib/api', () => ({
  authApi: {
    logout: vi.fn().mockResolvedValue({ success: true })
  }
}));

// Mock navigation
vi.mock('$app/navigation', () => ({
  goto: vi.fn()
}));

// Mock localStorage
const localStorageMock = (() => {
  let store = {};
  return {
    getItem: vi.fn((key) => store[key] || null),
    setItem: vi.fn((key, value) => {
      store[key] = value.toString();
    }),
    removeItem: vi.fn((key) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      store = {};
    })
  };
})();

// Mock window.localStorage
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock
});

describe('Auth Store', () => {
  beforeEach(() => {
    // Reset mocks and localStorage before each test
    vi.resetAllMocks();
    localStorageMock.clear();
  });
  
  it('initial state has isAuthenticated set to false', () => {
    let value;
    const unsubscribe = auth.subscribe(state => {
      value = state;
    });
    
    expect(value.isAuthenticated).toBe(false);
    unsubscribe();
  });
  
  it('setAuth updates isAuthenticated to true', () => {
    let value;
    const unsubscribe = auth.subscribe(state => {
      value = state;
    });
    
    auth.setAuth();
    
    expect(value.isAuthenticated).toBe(true);
    unsubscribe();
  });
  
  it('updateUser sets the user property', () => {
    let value;
    const unsubscribe = auth.subscribe(state => {
      value = state;
    });
    
    const testUser = { id: '123', name: 'Test User' };
    auth.updateUser(testUser);
    
    expect(value.user).toEqual(testUser);
    unsubscribe();
  });
  
  it('logout resets the state', async () => {
    let value;
    const unsubscribe = auth.subscribe(state => {
      value = state;
    });
    
    // First set some state
    auth.setAuth();
    auth.updateUser({ id: '123', name: 'Test User' });
    
    // Then logout - this is an async function
    await auth.logout();
    
    // Verify state is reset
    expect(value.isAuthenticated).toBe(false);
    // The user property may be undefined rather than empty object
    expect(value.user).toBeFalsy();
    unsubscribe();
  });
});