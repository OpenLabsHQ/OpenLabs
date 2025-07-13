import { vi } from 'vitest';

// Mock SvelteKit's $app modules
export const navigationMock = {
  goto: vi.fn(),
  invalidate: vi.fn()
};

export const environmentMock = {
  browser: true,
  dev: true
};

export const pagesMock = {
  error: vi.fn()
};

// Mock $lib/config
export const configMock = {
  apiUrl: 'http://localhost:8000'
};

// Mock $lib/stores with writable implementation
import { writable } from 'svelte/store';

// Create a real implementation of the auth store for testing
const createTestAuthStore = () => {
  const { subscribe, update, set } = writable({
    isAuthenticated: false, 
    user: {}
  });

  return {
    subscribe,
    updateUser: (userData = {}) => update(state => ({
      ...state,
      user: { ...state.user, ...userData }
    })),
    updateAuthState: (isAuthenticated) => update(state => ({
      ...state,
      isAuthenticated
    })),
    setAuth: (userData = {}) => set({
      isAuthenticated: true,
      user: userData
    }),
    logout: vi.fn(() => set({
      isAuthenticated: false,
      user: undefined
    }))
  };
};

// Create a real implementation of the blueprint wizard store for testing
const createTestBlueprintWizardStore = () => {
  const initialState = {
    name: '',
    provider: 'aws',
    vnc: false,
    vpn: false,
    vpcs: []
  };

  const { subscribe, update, set } = writable(initialState);

  return {
    subscribe,
    reset: () => set({ ...initialState }),
    setRangeDetails: (name, provider, vnc, vpn) => 
      update(state => ({ ...state, name, provider, vnc, vpn })),
    addVPC: (vpc) => update(state => ({
      ...state,
      vpcs: [...state.vpcs, vpc]
    })),
    updateVPC: (index, vpc) => update(state => {
      const vpcs = [...state.vpcs];
      vpcs[index] = vpc;
      return { ...state, vpcs };
    }),
    addSubnet: (vpcIndex, subnet) => update(state => {
      const vpcs = [...state.vpcs];
      if (vpcs[vpcIndex]) {
        vpcs[vpcIndex] = {
          ...vpcs[vpcIndex],
          subnets: [...vpcs[vpcIndex].subnets, subnet]
        };
      }
      return { ...state, vpcs };
    }),
    updateSubnet: (vpcIndex, subnetIndex, subnet) => update(state => {
      const vpcs = [...state.vpcs];
      if (vpcs[vpcIndex] && vpcs[vpcIndex].subnets[subnetIndex]) {
        const subnets = [...vpcs[vpcIndex].subnets];
        subnets[subnetIndex] = subnet;
        vpcs[vpcIndex] = { ...vpcs[vpcIndex], subnets };
      }
      return { ...state, vpcs };
    }),
    addHost: (vpcIndex, subnetIndex, host) => update(state => {
      const vpcs = [...state.vpcs];
      if (vpcs[vpcIndex] && vpcs[vpcIndex].subnets[subnetIndex]) {
        const subnets = [...vpcs[vpcIndex].subnets];
        subnets[subnetIndex] = {
          ...subnets[subnetIndex],
          hosts: [...subnets[subnetIndex].hosts, host]
        };
        vpcs[vpcIndex] = { ...vpcs[vpcIndex], subnets };
      }
      return { ...state, vpcs };
    }),
    updateHost: (vpcIndex, subnetIndex, hostIndex, host) => update(state => {
      const vpcs = [...state.vpcs];
      if (vpcs[vpcIndex] && vpcs[vpcIndex].subnets[subnetIndex]) {
        const subnets = [...vpcs[vpcIndex].subnets];
        const hosts = [...subnets[subnetIndex].hosts];
        hosts[hostIndex] = host;
        subnets[subnetIndex] = { ...subnets[subnetIndex], hosts };
        vpcs[vpcIndex] = { ...vpcs[vpcIndex], subnets };
      }
      return { ...state, vpcs };
    }),
    removeVPC: (index) => update(state => ({
      ...state,
      vpcs: state.vpcs.filter((_, i) => i !== index)
    })),
    removeSubnet: (vpcIndex, subnetIndex) => update(state => {
      const vpcs = [...state.vpcs];
      if (vpcs[vpcIndex]) {
        vpcs[vpcIndex] = {
          ...vpcs[vpcIndex],
          subnets: vpcs[vpcIndex].subnets.filter((_, i) => i !== subnetIndex)
        };
      }
      return { ...state, vpcs };
    }),
    removeHost: (vpcIndex, subnetIndex, hostIndex) => update(state => {
      const vpcs = [...state.vpcs];
      if (vpcs[vpcIndex] && vpcs[vpcIndex].subnets[subnetIndex]) {
        const subnets = [...vpcs[vpcIndex].subnets];
        subnets[subnetIndex] = {
          ...subnets[subnetIndex],
          hosts: subnets[subnetIndex].hosts.filter((_, i) => i !== hostIndex)
        };
        vpcs[vpcIndex] = { ...vpcs[vpcIndex], subnets };
      }
      return { ...state, vpcs };
    }),
    duplicateHosts: (sourceVpcIndex, sourceSubnetIndex, targetVpcIndex, targetSubnetIndex) => update(state => {
      const vpcs = [...state.vpcs];
      
      // Ensure source and target exist
      if (
        !vpcs[sourceVpcIndex] ||
        !vpcs[sourceVpcIndex].subnets[sourceSubnetIndex] ||
        !vpcs[targetVpcIndex] ||
        !vpcs[targetVpcIndex].subnets[targetSubnetIndex]
      ) {
        return state;
      }
      
      // Get hosts to duplicate
      const sourceHosts = vpcs[sourceVpcIndex].subnets[sourceSubnetIndex].hosts;
      
      // Get existing target hosts for hostname conflict checking
      const targetSubnet = vpcs[targetVpcIndex].subnets[targetSubnetIndex];
      const existingHostnames = new Set(targetSubnet.hosts.map((host) => host.hostname));
      
      // Clone hosts with unique hostnames
      const hostsToAdd = sourceHosts.map((host) => {
        let newHostname = host.hostname;
        let counter = 1;
        
        // Ensure hostname is unique in target subnet
        while (existingHostnames.has(newHostname)) {
          newHostname = `${host.hostname}-copy${counter}`;
          counter++;
        }
        
        existingHostnames.add(newHostname);
        
        // Return a new host object with the updated hostname
        return {
          ...JSON.parse(JSON.stringify(host)), // Deep clone
          hostname: newHostname
        };
      });
      
      // Add hosts to target subnet
      const subnets = [...vpcs[targetVpcIndex].subnets];
      subnets[targetSubnetIndex] = {
        ...subnets[targetSubnetIndex],
        hosts: [...subnets[targetSubnetIndex].hosts, ...hostsToAdd]
      };
      vpcs[targetVpcIndex] = { ...vpcs[targetVpcIndex], subnets };
      
      return { ...state, vpcs };
    })
  };
};

export const authStoreMock = createTestAuthStore();
export const blueprintWizardStoreMock = createTestBlueprintWizardStore();

// Setup module mocks that can be imported in tests
vi.mock('$app/navigation', () => navigationMock);
vi.mock('$app/environment', () => environmentMock);
vi.mock('$app/forms', () => ({ enhance: vi.fn() }));
vi.mock('$lib/config', () => ({ config: configMock }));
vi.mock('$lib/stores/auth', () => ({ auth: authStoreMock }));
vi.mock('$lib/stores/blueprint-wizard', () => ({ blueprintWizard: blueprintWizardStoreMock }));