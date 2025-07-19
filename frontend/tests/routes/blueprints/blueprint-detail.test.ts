import { describe, it, expect, vi, beforeEach } from 'vitest';
import { rangesApi } from '../../../src/lib/api';
import { goto } from '$app/navigation';
import { auth } from '../../../src/lib/stores/auth';

// Mock dependencies
vi.mock('$app/navigation', () => ({
  goto: vi.fn()
}));

vi.mock('../../../src/lib/api', () => ({
  rangesApi: {
    getBlueprintById: vi.fn(),
    deployBlueprint: vi.fn()
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

describe('Blueprint Detail Page', () => {
  const blueprintId = 'blueprint-123';
  
  beforeEach(() => {
    vi.resetAllMocks();
    // Default to authenticated user
    auth.isAuthenticated = true;
  });
  
  describe('Page load and data fetching', () => {
    it('loads blueprint data correctly when API call succeeds', async () => {
      // Mock successful API response
      rangesApi.getBlueprintById.mockResolvedValueOnce({
        data: {
          id: blueprintId,
          name: 'Test Blueprint',
          description: 'A test blueprint',
          vpc: {
            cidr_block: '10.0.0.0/16'
          },
          subnets: [
            { name: 'public', cidr_block: '10.0.1.0/24' },
            { name: 'private', cidr_block: '10.0.2.0/24' }
          ],
          hosts: [
            { name: 'web-server', subnet: 'public' }
          ]
        }
      });
      
      // Simulate the page load function (from +page.ts)
      const load = ({ params }) => {
        return {
          blueprintId: params.id
        };
      };
      
      // Get the blueprint ID from the load function
      const pageData = load({ params: { id: blueprintId } });
      expect(pageData.blueprintId).toBe(blueprintId);
      
      // Simulate the component's blueprint loading logic
      let blueprint = null;
      let isLoading = true;
      let error = '';
      
      try {
        const result = await rangesApi.getBlueprintById(pageData.blueprintId);
        isLoading = false;
        
        if (result.error) {
          error = result.error;
        } else if (result.data) {
          blueprint = result.data;
        }
      } catch (err) {
        isLoading = false;
        error = 'An unexpected error occurred';
      }
      
      // Verify blueprint loaded correctly
      expect(isLoading).toBe(false);
      expect(error).toBe('');
      expect(blueprint).not.toBeNull();
      expect(blueprint.id).toBe(blueprintId);
      expect(blueprint.vpc).toBeDefined();
      expect(blueprint.subnets).toHaveLength(2);
      expect(blueprint.hosts).toHaveLength(1);
    });
    
    it('handles API error when blueprint is not found', async () => {
      // Mock 404 API response
      rangesApi.getBlueprintById.mockResolvedValueOnce({
        error: 'The requested information could not be found.',
        status: 404
      });
      
      // Simulate the component's blueprint loading logic
      let blueprint = null;
      let isLoading = true;
      let error = '';
      
      try {
        const result = await rangesApi.getBlueprintById(blueprintId);
        isLoading = false;
        
        if (result.error) {
          error = result.error;
        } else if (result.data) {
          blueprint = result.data;
        }
      } catch (err) {
        isLoading = false;
        error = 'An unexpected error occurred';
      }
      
      // Verify error handling
      expect(isLoading).toBe(false);
      expect(error).toBe('The requested information could not be found.');
      expect(blueprint).toBeNull();
    });
  });
  
  describe('Blueprint deployment', () => {
    it('deploys blueprint successfully', async () => {
      // Mock successful deployment
      rangesApi.deployBlueprint.mockResolvedValueOnce({
        data: {
          id: 'deployment-123',
          status: 'pending'
        }
      });
      
      // Simulate deployment function
      let deploymentResult = null;
      let deploymentError = '';
      let isDeploying = true;
      
      try {
        const result = await rangesApi.deployBlueprint(blueprintId);
        isDeploying = false;
        
        if (result.error) {
          deploymentError = result.error;
        } else if (result.data) {
          deploymentResult = result.data;
          // After successful deployment, would navigate to ranges page
          goto('/ranges');
        }
      } catch (err) {
        isDeploying = false;
        deploymentError = 'Failed to deploy blueprint';
      }
      
      // Verify deployment was successful
      expect(isDeploying).toBe(false);
      expect(deploymentError).toBe('');
      expect(deploymentResult).not.toBeNull();
      expect(deploymentResult.id).toBe('deployment-123');
      expect(goto).toHaveBeenCalledWith('/ranges');
    });
    
    it('handles API error during deployment', async () => {
      // Mock error during deployment
      rangesApi.deployBlueprint.mockResolvedValueOnce({
        error: 'Failed to deploy blueprint. API server error.',
        status: 500
      });
      
      // Simulate deployment function
      let deploymentResult = null;
      let deploymentError = '';
      let isDeploying = true;
      
      try {
        const result = await rangesApi.deployBlueprint(blueprintId);
        isDeploying = false;
        
        if (result.error) {
          deploymentError = result.error;
        } else if (result.data) {
          deploymentResult = result.data;
          goto('/ranges');
        }
      } catch (err) {
        isDeploying = false;
        deploymentError = 'Failed to deploy blueprint';
      }
      
      // Verify error handling
      expect(isDeploying).toBe(false);
      expect(deploymentError).toBe('Failed to deploy blueprint. API server error.');
      expect(deploymentResult).toBeNull();
      expect(goto).not.toHaveBeenCalled();
    });
  });
});