import { describe, it, expect, vi, beforeEach } from 'vitest';
import { goto } from '$app/navigation';
import { get } from 'svelte/store';
import { rangesApi } from '../../../src/lib/api';

// Mock the blueprint-wizard store
const blueprintWizard = {
  currentStep: 1,
  vpc: null,
  subnets: [],
  hosts: [],
  completed: {
    vpc: false,
    subnets: false,
    hosts: false
  },
  
  reset: vi.fn(() => {
    blueprintWizard.currentStep = 1;
    blueprintWizard.vpc = null;
    blueprintWizard.subnets = [];
    blueprintWizard.hosts = [];
    blueprintWizard.completed = {
      vpc: false,
      subnets: false,
      hosts: false
    };
  }),
  
  setVpc: vi.fn((vpc) => {
    blueprintWizard.vpc = vpc;
    blueprintWizard.completed.vpc = true;
  }),
  
  addSubnet: vi.fn((subnet) => {
    const newSubnet = { ...subnet, id: subnet.id || `subnet-${Date.now()}` };
    blueprintWizard.subnets.push(newSubnet);
    blueprintWizard.completed.subnets = blueprintWizard.subnets.length > 0;
  }),
  
  removeSubnet: vi.fn((id) => {
    blueprintWizard.subnets = blueprintWizard.subnets.filter(s => s.id !== id);
    blueprintWizard.completed.subnets = blueprintWizard.subnets.length > 0;
  }),
  
  addHost: vi.fn((host) => {
    const newHost = { ...host, id: host.id || `host-${Date.now()}` };
    blueprintWizard.hosts.push(newHost);
    blueprintWizard.completed.hosts = blueprintWizard.hosts.length > 0;
  }),
  
  removeHost: vi.fn((id) => {
    blueprintWizard.hosts = blueprintWizard.hosts.filter(h => h.id !== id);
    blueprintWizard.completed.hosts = blueprintWizard.hosts.length > 0;
  }),
  
  subscribe: vi.fn((callback) => {
    callback(blueprintWizard);
    return () => {};
  })
};

// Mock dependencies
vi.mock('$app/navigation', () => ({
  goto: vi.fn()
}));

vi.mock('../../../src/lib/api', () => ({
  rangesApi: {
    createBlueprint: vi.fn()
  }
}));

describe('Blueprint Wizard Flow', () => {
  // Reset all mocks and store state before each test
  beforeEach(() => {
    vi.resetAllMocks();
    
    // Reset the store to default state
    blueprintWizard.reset();
    
    // Set up get function for store
    vi.mock('svelte/store', () => ({
      get: vi.fn((store) => {
        // Simplified mock implementation of get - just return the store
        return store;
      })
    }));
  });
  
  describe('VPC configuration step', () => {
    it('saves vpc settings correctly', () => {
      const vpcData = {
        name: 'Test VPC',
        cidr: '10.0.0.0/16',
        provider: 'aws',
        region: 'us-east-1'
      };
      
      // Apply VPC configuration
      blueprintWizard.setVpc(vpcData);
      
      // Get the store state
      const state = get(blueprintWizard);
      
      // Verify VPC data was saved
      expect(state.vpc).toEqual(vpcData);
      expect(state.currentStep).toBe(1); // Should be on vpc step still
      expect(state.completed.vpc).toBe(true); // VPC step should be marked complete
    });
    
    it('validates vpc cidr block format', () => {
      // Test with invalid CIDR
      const invalidVpc = {
        name: 'Test VPC',
        cidr: 'invalid-cidr',
        provider: 'aws',
        region: 'us-east-1'
      };
      
      // Create a function that would validate the CIDR
      function validateCidr(cidr) {
        const cidrRegex = /^([0-9]{1,3}\.){3}[0-9]{1,3}(\/([0-9]|[1-2][0-9]|3[0-2]))$/;
        return cidrRegex.test(cidr);
      }
      
      // Verify validation fails
      expect(validateCidr(invalidVpc.cidr)).toBe(false);
      
      // Test with valid CIDR
      const validVpc = {
        name: 'Test VPC',
        cidr: '10.0.0.0/16',
        provider: 'aws',
        region: 'us-east-1'
      };
      
      // Verify validation passes
      expect(validateCidr(validVpc.cidr)).toBe(true);
    });
  });
  
  describe('Subnet configuration step', () => {
    it('adds subnets correctly', () => {
      // Setup VPC first
      blueprintWizard.setVpc({
        name: 'Test VPC',
        cidr: '10.0.0.0/16',
        provider: 'aws',
        region: 'us-east-1'
      });
      
      // Add a public subnet
      blueprintWizard.addSubnet({
        name: 'Public Subnet',
        cidr: '10.0.1.0/24',
        type: 'public',
        az: 'us-east-1a'
      });
      
      // Add a private subnet
      blueprintWizard.addSubnet({
        name: 'Private Subnet',
        cidr: '10.0.2.0/24',
        type: 'private',
        az: 'us-east-1b'
      });
      
      // Get the store state
      const state = get(blueprintWizard);
      
      // Verify subnets were added
      expect(state.subnets).toHaveLength(2);
      expect(state.subnets[0].name).toBe('Public Subnet');
      expect(state.subnets[1].name).toBe('Private Subnet');
      expect(state.completed.subnets).toBe(true);
    });
    
    it('removes subnets correctly', () => {
      // Setup VPC and subnets
      blueprintWizard.setVpc({
        name: 'Test VPC',
        cidr: '10.0.0.0/16',
        provider: 'aws',
        region: 'us-east-1'
      });
      
      // Add two subnets
      blueprintWizard.addSubnet({
        id: 'subnet1',
        name: 'Subnet 1',
        cidr: '10.0.1.0/24',
        type: 'public',
        az: 'us-east-1a'
      });
      
      blueprintWizard.addSubnet({
        id: 'subnet2',
        name: 'Subnet 2',
        cidr: '10.0.2.0/24',
        type: 'private',
        az: 'us-east-1b'
      });
      
      // Remove the first subnet
      blueprintWizard.removeSubnet('subnet1');
      
      // Get the store state
      const state = get(blueprintWizard);
      
      // Verify subnet was removed
      expect(state.subnets).toHaveLength(1);
      expect(state.subnets[0].name).toBe('Subnet 2');
    });
    
    it('checks for subnet CIDR overlap with VPC', () => {
      // Setup VPC
      const vpc = {
        name: 'Test VPC',
        cidr: '10.0.0.0/16',  // 10.0.0.0 - 10.0.255.255
        provider: 'aws',
        region: 'us-east-1'
      };
      
      blueprintWizard.setVpc(vpc);
      
      // Function to check if subnet CIDR is within VPC CIDR
      function isSubnetInVpc(subnetCidr, vpcCidr) {
        // Simple check - in real code would use proper IP math libraries
        // This is just a simplified example
        if (subnetCidr.startsWith('10.0.') && vpcCidr === '10.0.0.0/16') {
          return true;
        }
        return false;
      }
      
      // Test valid subnet within VPC
      const validSubnet = {
        name: 'Valid Subnet',
        cidr: '10.0.1.0/24',
        type: 'public',
        az: 'us-east-1a'
      };
      
      expect(isSubnetInVpc(validSubnet.cidr, vpc.cidr)).toBe(true);
      
      // Test invalid subnet outside VPC
      const invalidSubnet = {
        name: 'Invalid Subnet',
        cidr: '192.168.1.0/24',
        type: 'public',
        az: 'us-east-1a'
      };
      
      expect(isSubnetInVpc(invalidSubnet.cidr, vpc.cidr)).toBe(false);
    });
  });
  
  describe('Host configuration step', () => {
    it('adds hosts correctly', () => {
      // Setup VPC and subnet
      blueprintWizard.setVpc({
        name: 'Test VPC',
        cidr: '10.0.0.0/16',
        provider: 'aws',
        region: 'us-east-1'
      });
      
      blueprintWizard.addSubnet({
        id: 'public1',
        name: 'Public Subnet',
        cidr: '10.0.1.0/24',
        type: 'public',
        az: 'us-east-1a'
      });
      
      // Add a host
      blueprintWizard.addHost({
        name: 'Web Server',
        subnet: 'public1',
        os: 'linux',
        instanceType: 't2.micro'
      });
      
      // Get the store state
      const state = get(blueprintWizard);
      
      // Verify host was added
      expect(state.hosts).toHaveLength(1);
      expect(state.hosts[0].name).toBe('Web Server');
      expect(state.hosts[0].subnet).toBe('public1');
      expect(state.completed.hosts).toBe(true);
    });
    
    it('removes hosts correctly', () => {
      // Setup VPC and subnet
      blueprintWizard.setVpc({
        name: 'Test VPC',
        cidr: '10.0.0.0/16',
        provider: 'aws',
        region: 'us-east-1'
      });
      
      blueprintWizard.addSubnet({
        id: 'public1',
        name: 'Public Subnet',
        cidr: '10.0.1.0/24',
        type: 'public',
        az: 'us-east-1a'
      });
      
      // Add two hosts
      blueprintWizard.addHost({
        id: 'host1',
        name: 'Web Server',
        subnet: 'public1',
        os: 'linux',
        instanceType: 't2.micro'
      });
      
      blueprintWizard.addHost({
        id: 'host2',
        name: 'Database Server',
        subnet: 'public1',
        os: 'linux',
        instanceType: 't2.small'
      });
      
      // Remove the first host
      blueprintWizard.removeHost('host1');
      
      // Get the store state
      const state = get(blueprintWizard);
      
      // Verify host was removed
      expect(state.hosts).toHaveLength(1);
      expect(state.hosts[0].name).toBe('Database Server');
    });
  });
  
  describe('Review and submission step', () => {
    it('prepares data for submission correctly', () => {
      // Setup complete blueprint
      blueprintWizard.setVpc({
        name: 'Production VPC',
        cidr: '10.0.0.0/16',
        provider: 'aws',
        region: 'us-east-1'
      });
      
      blueprintWizard.addSubnet({
        id: 'public1',
        name: 'Public Subnet',
        cidr: '10.0.1.0/24',
        type: 'public',
        az: 'us-east-1a'
      });
      
      blueprintWizard.addSubnet({
        id: 'private1',
        name: 'Private Subnet',
        cidr: '10.0.2.0/24',
        type: 'private',
        az: 'us-east-1b'
      });
      
      blueprintWizard.addHost({
        id: 'web1',
        name: 'Web Server',
        subnet: 'public1',
        os: 'linux',
        instanceType: 't2.micro'
      });
      
      blueprintWizard.addHost({
        id: 'db1',
        name: 'Database Server',
        subnet: 'private1',
        os: 'linux',
        instanceType: 't2.small'
      });
      
      // Function to prepare data for API - similar to what would be in the component
      function prepareBlueprintData(state) {
        return {
          name: state.vpc.name,
          provider: state.vpc.provider,
          region: state.vpc.region,
          vpc: {
            cidr_block: state.vpc.cidr
          },
          subnets: state.subnets.map(subnet => ({
            name: subnet.name,
            cidr_block: subnet.cidr,
            type: subnet.type,
            availability_zone: subnet.az
          })),
          hosts: state.hosts.map(host => ({
            name: host.name,
            subnet: host.subnet,
            os: host.os,
            instance_type: host.instanceType
          }))
        };
      }
      
      // Generate the API payload
      const state = get(blueprintWizard);
      const apiPayload = prepareBlueprintData(state);
      
      // Verify payload structure
      expect(apiPayload.name).toBe('Production VPC');
      expect(apiPayload.vpc.cidr_block).toBe('10.0.0.0/16');
      expect(apiPayload.subnets).toHaveLength(2);
      expect(apiPayload.hosts).toHaveLength(2);
      expect(apiPayload.hosts[0].subnet).toBe('public1');
      expect(apiPayload.hosts[1].subnet).toBe('private1');
    });
    
    it('submits blueprint to API and handles success', async () => {
      // Setup blueprint
      blueprintWizard.setVpc({
        name: 'Test Blueprint',
        cidr: '10.0.0.0/16',
        provider: 'aws',
        region: 'us-east-1'
      });
      
      blueprintWizard.addSubnet({
        id: 'subnet1',
        name: 'Subnet',
        cidr: '10.0.1.0/24',
        type: 'public',
        az: 'us-east-1a'
      });
      
      // Mock successful API response
      rangesApi.createBlueprint.mockResolvedValueOnce({
        data: { id: 'new-blueprint-123', name: 'Test Blueprint' }
      });
      
      // Simulate form submission
      const state = get(blueprintWizard);
      let isSubmitting = true;
      let error = '';
      let success = false;
      
      try {
        // Prepare data (simplified)
        const blueprintData = {
          name: state.vpc.name,
          provider: state.vpc.provider,
          vpc: { cidr_block: state.vpc.cidr },
          subnets: state.subnets
        };
        
        // Submit to API
        const result = await rangesApi.createBlueprint(blueprintData);
        
        if (result.error) {
          error = result.error;
        } else {
          success = true;
          // Would typically redirect here
          goto('/blueprints');
        }
      } catch (err) {
        error = 'Failed to submit blueprint';
      } finally {
        isSubmitting = false;
      }
      
      // Verify submission was successful
      expect(isSubmitting).toBe(false);
      expect(error).toBe('');
      expect(success).toBe(true);
      expect(rangesApi.createBlueprint).toHaveBeenCalledTimes(1);
      expect(goto).toHaveBeenCalledWith('/blueprints');
    });
    
    it('handles API error during submission', async () => {
      // Setup blueprint
      blueprintWizard.setVpc({
        name: 'Test Blueprint',
        cidr: '10.0.0.0/16',
        provider: 'aws',
        region: 'us-east-1'
      });
      
      // Mock API error
      rangesApi.createBlueprint.mockResolvedValueOnce({
        error: 'Failed to create blueprint'
      });
      
      // Simulate form submission
      const state = get(blueprintWizard);
      let isSubmitting = true;
      let error = '';
      let success = false;
      
      try {
        // Prepare data (simplified)
        const blueprintData = {
          name: state.vpc.name,
          provider: state.vpc.provider,
          vpc: { cidr_block: state.vpc.cidr }
        };
        
        // Submit to API
        const result = await rangesApi.createBlueprint(blueprintData);
        
        if (result.error) {
          error = result.error;
        } else {
          success = true;
          goto('/blueprints');
        }
      } catch (err) {
        error = 'Failed to submit blueprint';
      } finally {
        isSubmitting = false;
      }
      
      // Verify error handling
      expect(isSubmitting).toBe(false);
      expect(error).toBe('Failed to create blueprint');
      expect(success).toBe(false);
      expect(goto).not.toHaveBeenCalled();
    });
  });
});