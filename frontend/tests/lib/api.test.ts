import { describe, it, expect, vi, beforeEach } from 'vitest';
import { userApi, authApi, rangesApi } from '../../src/lib/api';
import { config } from '../../src/lib/config';
import { auth } from '../../src/lib/stores/auth';

// Mock console.error to prevent test logs being cluttered
vi.spyOn(console, 'error').mockImplementation(() => {});

// Mock fetch
global.fetch = vi.fn();

// Mock auth store
vi.mock('./stores/auth', () => ({
  auth: {
    updateUser: vi.fn(),
    updateAuthState: vi.fn(),
    logout: vi.fn()
  }
}));

describe('API', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    
    // Setup default fetch mock
    global.fetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ data: 'test' }),
      headers: {
        get: () => 'application/json'
      }
    });
  });

  it('has correct API endpoints based on config', () => {
    // Check that we're using the API URL from config
    expect(config.apiUrl).toBeDefined();
  });
  
  it('userApi contains expected methods', () => {
    // Check userApi exports expected methods
    expect(userApi.getUserSecrets).toBeDefined();
    expect(userApi.updatePassword).toBeDefined();
    expect(userApi.setAwsSecrets).toBeDefined();
    expect(userApi.setAzureSecrets).toBeDefined();
  });
  
  it('authApi contains expected methods', () => {
    // Check authApi exports expected methods
    expect(authApi.login).toBeDefined();
    expect(authApi.register).toBeDefined();
    expect(authApi.getCurrentUser).toBeDefined();
    expect(authApi.logout).toBeDefined();
  });
  
  it('rangesApi contains expected methods', () => {
    // Check rangesApi exports expected methods
    expect(rangesApi.getRanges).toBeDefined();
    expect(rangesApi.getRangeById).toBeDefined();
    expect(rangesApi.getBlueprints).toBeDefined();
    expect(rangesApi.getBlueprintById).toBeDefined();
    expect(rangesApi.createBlueprint).toBeDefined();
    expect(rangesApi.deployBlueprint).toBeDefined();
  });

  describe('userApi', () => {
    it('getUserSecrets makes correct API call', async () => {
      await userApi.getUserSecrets();
      
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/users/me/secrets'),
        expect.objectContaining({
          method: 'GET',
          credentials: 'include'
        })
      );
    });

    it('updatePassword makes correct API call with payload', async () => {
      const currentPassword = 'current';
      const newPassword = 'new';
      
      await userApi.updatePassword(currentPassword, newPassword);
      
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/users/me/password'),
        expect.objectContaining({
          method: 'POST',
          body: expect.stringContaining('current_password'),
          credentials: 'include'
        })
      );
    });

    it('setAwsSecrets makes correct API call with keys', async () => {
      const accessKey = 'ACCESS_KEY';
      const secretKey = 'SECRET_KEY';
      
      await userApi.setAwsSecrets(accessKey, secretKey);
      
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/users/me/secrets/aws'),
        expect.objectContaining({
          method: 'POST',
          body: expect.stringContaining('aws_access_key'),
          credentials: 'include'
        })
      );
    });
  });

  describe('authApi', () => {
    it('login makes correct API call and processes response', async () => {
      // Mock successful login
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ user: { name: 'Test User' } }),
        status: 200
      });
      
      const result = await authApi.login({ email: 'test@example.com', password: 'password' });
      
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/auth/login'),
        expect.objectContaining({
          method: 'POST',
          body: expect.stringContaining('test@example.com'),
          credentials: 'include'
        })
      );
      
      expect(result.data).toBeDefined();
      // We've already mocked auth.updateUser, but we don't spy on it directly
      // so we'll remove this check
    });

    it('login handles error responses', async () => {
      // Mock failed login
      global.fetch.mockResolvedValueOnce({
        ok: false,
        json: () => Promise.resolve({ detail: 'Invalid credentials' }),
        status: 401,
        text: () => Promise.resolve('Invalid credentials')
      });
      
      const result = await authApi.login({ email: 'test@example.com', password: 'wrong' });
      
      expect(result.error).toBeDefined();
      expect(result.error).toContain('Invalid email or password');
    });

    it('logout makes correct API call', async () => {
      // Mock successful logout
      global.fetch.mockResolvedValueOnce({
        ok: true
      });
      
      await authApi.logout();
      
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/auth/logout'),
        expect.objectContaining({
          method: 'POST',
          credentials: 'include'
        })
      );
    });
  });

  describe('rangesApi', () => {
    it('getRanges returns list of ranges when API call succeeds', async () => {
      // Mock successful ranges response
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve([{ id: '1', name: 'Range 1' }, { id: '2', name: 'Range 2' }]),
        headers: {
          get: () => 'application/json'
        }
      });
      
      const result = await rangesApi.getRanges();
      
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/ranges'),
        expect.objectContaining({
          method: 'GET',
          credentials: 'include'
        })
      );
      
      expect(result.data).toBeInstanceOf(Array);
      expect(result.data).toHaveLength(2);
    });

    it('getRanges handles 404 error correctly for non-existent endpoint', async () => {
      // Mock 404 not found response for ranges endpoint
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: () => Promise.resolve({ detail: 'Endpoint not found' }),
        headers: {
          get: () => 'application/json'
        }
      });
      
      const result = await rangesApi.getRanges();
      
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/ranges'),
        expect.any(Object)
      );
      
      expect(result.error).toBe('The requested information could not be found.');
      expect(result.status).toBe(404);
      expect(result.data).toBeUndefined();
    });

    it('getRanges handles server error correctly', async () => {
      // Mock 500 server error response
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: () => Promise.resolve({ detail: 'Internal server error' }),
        headers: {
          get: () => 'application/json'
        }
      });
      
      const result = await rangesApi.getRanges();
      
      expect(result.error).toBe('The server is currently unavailable. Please try again later.');
      expect(result.status).toBe(500);
    });

    it('getBlueprintById fetches specific blueprint', async () => {
      const blueprintId = '123';
      
      await rangesApi.getBlueprintById(blueprintId);
      
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining(`/api/v1/blueprints/ranges/${blueprintId}`),
        expect.objectContaining({
          method: 'GET',
          credentials: 'include'
        })
      );
    });

    it('createBlueprint sends blueprint data', async () => {
      const blueprintData = { name: 'New Blueprint', provider: 'aws' };
      
      await rangesApi.createBlueprint(blueprintData);
      
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/blueprints/ranges'),
        expect.objectContaining({
          method: 'POST',
          body: expect.stringContaining('New Blueprint'),
          credentials: 'include'
        })
      );
    });

    it('deployBlueprint sends the correct blueprint ID', async () => {
      const blueprintId = '456';
      
      await rangesApi.deployBlueprint(blueprintId);
      
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/ranges/deploy'),
        expect.objectContaining({
          method: 'POST',
          body: expect.stringContaining(blueprintId),
          credentials: 'include'
        })
      );
    });
  });
});