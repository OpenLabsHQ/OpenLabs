import { describe, it, expect, beforeEach } from 'vitest';
import { blueprintWizard, type BlueprintHost, type BlueprintSubnet, type BlueprintVPC } from '../../../src/lib/stores/blueprint-wizard';

describe('Blueprint Wizard Store', () => {
  // Reset the store before each test
  beforeEach(() => {
    blueprintWizard.reset();
  });
  
  it('starts with initial state', () => {
    let value;
    const unsubscribe = blueprintWizard.subscribe(state => {
      value = state;
    });
    
    // Check initial state
    expect(value.name).toBe('');
    expect(value.provider).toBe('aws');
    expect(value.vnc).toBe(false);
    expect(value.vpn).toBe(false);
    expect(value.vpcs).toEqual([]);
    
    unsubscribe();
  });
  
  describe('setRangeDetails', () => {
    it('updates range details correctly', () => {
      let value;
      const unsubscribe = blueprintWizard.subscribe(state => {
        value = state;
      });
      
      // Set range details
      blueprintWizard.setRangeDetails('Test Range', 'azure', true, true);
      
      // Check values
      expect(value.name).toBe('Test Range');
      expect(value.provider).toBe('azure');
      expect(value.vnc).toBe(true);
      expect(value.vpn).toBe(true);
      
      unsubscribe();
    });
  });
  
  describe('VPC operations', () => {
    const testVpc: BlueprintVPC = {
      name: 'Test VPC',
      cidr: '10.0.0.0/16',
      subnets: []
    };
    
    it('adds a VPC', () => {
      let value;
      const unsubscribe = blueprintWizard.subscribe(state => {
        value = state;
      });
      
      blueprintWizard.addVPC(testVpc);
      
      expect(value.vpcs.length).toBe(1);
      expect(value.vpcs[0].name).toBe('Test VPC');
      
      unsubscribe();
    });
    
    it('updates an existing VPC', () => {
      let value;
      const unsubscribe = blueprintWizard.subscribe(state => {
        value = state;
      });
      
      // Add VPC first
      blueprintWizard.addVPC(testVpc);
      
      // Update it
      const updatedVpc = { ...testVpc, name: 'Updated VPC' };
      blueprintWizard.updateVPC(0, updatedVpc);
      
      expect(value.vpcs[0].name).toBe('Updated VPC');
      
      unsubscribe();
    });
    
    it('removes a VPC', () => {
      let value;
      const unsubscribe = blueprintWizard.subscribe(state => {
        value = state;
      });
      
      // Add VPCs
      blueprintWizard.addVPC({ ...testVpc, name: 'VPC 1' });
      blueprintWizard.addVPC({ ...testVpc, name: 'VPC 2' });
      
      // Remove first VPC
      blueprintWizard.removeVPC(0);
      
      expect(value.vpcs.length).toBe(1);
      expect(value.vpcs[0].name).toBe('VPC 2');
      
      unsubscribe();
    });
  });
  
  describe('Subnet operations', () => {
    const testVpc: BlueprintVPC = {
      name: 'Test VPC',
      cidr: '10.0.0.0/16',
      subnets: []
    };
    
    const testSubnet: BlueprintSubnet = {
      name: 'Test Subnet',
      cidr: '10.0.1.0/24',
      hosts: []
    };
    
    it('adds a subnet to a VPC', () => {
      let value;
      const unsubscribe = blueprintWizard.subscribe(state => {
        value = state;
      });
      
      // Add VPC first
      blueprintWizard.addVPC(testVpc);
      
      // Add subnet
      blueprintWizard.addSubnet(0, testSubnet);
      
      expect(value.vpcs[0].subnets.length).toBe(1);
      expect(value.vpcs[0].subnets[0].name).toBe('Test Subnet');
      
      unsubscribe();
    });
    
    it('updates an existing subnet', () => {
      let value;
      const unsubscribe = blueprintWizard.subscribe(state => {
        value = state;
      });
      
      // Add VPC and subnet
      blueprintWizard.addVPC(testVpc);
      blueprintWizard.addSubnet(0, testSubnet);
      
      // Update subnet
      const updatedSubnet = { ...testSubnet, name: 'Updated Subnet' };
      blueprintWizard.updateSubnet(0, 0, updatedSubnet);
      
      expect(value.vpcs[0].subnets[0].name).toBe('Updated Subnet');
      
      unsubscribe();
    });
    
    it('removes a subnet', () => {
      let value;
      const unsubscribe = blueprintWizard.subscribe(state => {
        value = state;
      });
      
      // Add VPC and subnets
      blueprintWizard.addVPC(testVpc);
      blueprintWizard.addSubnet(0, { ...testSubnet, name: 'Subnet 1' });
      blueprintWizard.addSubnet(0, { ...testSubnet, name: 'Subnet 2' });
      
      // Remove the first subnet
      blueprintWizard.removeSubnet(0, 0);
      
      expect(value.vpcs[0].subnets.length).toBe(1);
      expect(value.vpcs[0].subnets[0].name).toBe('Subnet 2');
      
      unsubscribe();
    });
  });
  
  describe('Host operations', () => {
    const testVpc: BlueprintVPC = {
      name: 'Test VPC',
      cidr: '10.0.0.0/16',
      subnets: []
    };
    
    const testSubnet: BlueprintSubnet = {
      name: 'Test Subnet',
      cidr: '10.0.1.0/24',
      hosts: []
    };
    
    const testHost: BlueprintHost = {
      hostname: 'test-host',
      os: 'linux',
      spec: 'small',
      size: 20,
      tags: ['test']
    };
    
    it('adds a host to a subnet', () => {
      let value;
      const unsubscribe = blueprintWizard.subscribe(state => {
        value = state;
      });
      
      // Add VPC and subnet
      blueprintWizard.addVPC(testVpc);
      blueprintWizard.addSubnet(0, testSubnet);
      
      // Add host
      blueprintWizard.addHost(0, 0, testHost);
      
      expect(value.vpcs[0].subnets[0].hosts.length).toBe(1);
      expect(value.vpcs[0].subnets[0].hosts[0].hostname).toBe('test-host');
      
      unsubscribe();
    });
    
    it('updates an existing host', () => {
      let value;
      const unsubscribe = blueprintWizard.subscribe(state => {
        value = state;
      });
      
      // Add VPC, subnet, and host
      blueprintWizard.addVPC(testVpc);
      blueprintWizard.addSubnet(0, testSubnet);
      blueprintWizard.addHost(0, 0, testHost);
      
      // Update host
      const updatedHost = { ...testHost, hostname: 'updated-host', os: 'windows' };
      blueprintWizard.updateHost(0, 0, 0, updatedHost);
      
      expect(value.vpcs[0].subnets[0].hosts[0].hostname).toBe('updated-host');
      expect(value.vpcs[0].subnets[0].hosts[0].os).toBe('windows');
      
      unsubscribe();
    });
    
    it('removes a host', () => {
      let value;
      const unsubscribe = blueprintWizard.subscribe(state => {
        value = state;
      });
      
      // Add VPC, subnet, and hosts
      blueprintWizard.addVPC(testVpc);
      blueprintWizard.addSubnet(0, testSubnet);
      blueprintWizard.addHost(0, 0, { ...testHost, hostname: 'host-1' });
      blueprintWizard.addHost(0, 0, { ...testHost, hostname: 'host-2' });
      
      // Remove the first host
      blueprintWizard.removeHost(0, 0, 0);
      
      expect(value.vpcs[0].subnets[0].hosts.length).toBe(1);
      expect(value.vpcs[0].subnets[0].hosts[0].hostname).toBe('host-2');
      
      unsubscribe();
    });
  });
  
  describe('duplicateHosts', () => {
    it('copies hosts from one subnet to another with unique hostnames', () => {
      let value;
      const unsubscribe = blueprintWizard.subscribe(state => {
        value = state;
      });
      
      // Add two VPCs with subnets
      blueprintWizard.addVPC({
        name: 'VPC 1',
        cidr: '10.0.0.0/16',
        subnets: []
      });
      
      blueprintWizard.addVPC({
        name: 'VPC 2',
        cidr: '10.1.0.0/16',
        subnets: []
      });
      
      // Add subnets
      blueprintWizard.addSubnet(0, {
        name: 'Source Subnet',
        cidr: '10.0.1.0/24',
        hosts: []
      });
      
      blueprintWizard.addSubnet(1, {
        name: 'Target Subnet',
        cidr: '10.1.1.0/24',
        hosts: []
      });
      
      // Add hosts to source subnet
      blueprintWizard.addHost(0, 0, {
        hostname: 'server-1',
        os: 'linux',
        spec: 'small',
        size: 20,
        tags: ['web']
      });
      
      blueprintWizard.addHost(0, 0, {
        hostname: 'server-2',
        os: 'windows',
        spec: 'medium',
        size: 40,
        tags: ['db']
      });
      
      // Add a host to target subnet with the same name
      blueprintWizard.addHost(1, 0, {
        hostname: 'server-1',
        os: 'linux',
        spec: 'large',
        size: 80,
        tags: ['existing']
      });
      
      // Duplicate hosts from source to target
      blueprintWizard.duplicateHosts(0, 0, 1, 0);
      
      // Check the target subnet
      const targetSubnet = value.vpcs[1].subnets[0];
      
      // Should have 3 hosts (1 original + 2 duplicated)
      expect(targetSubnet.hosts.length).toBe(3);
      
      // Check for renamed duplicated hosts
      const hostnames = targetSubnet.hosts.map(h => h.hostname);
      expect(hostnames).toContain('server-1');
      expect(hostnames).toContain('server-1-copy1');
      expect(hostnames).toContain('server-2');
      
      unsubscribe();
    });
  });
  
  it('reset() returns store to initial state', () => {
    let value;
    const unsubscribe = blueprintWizard.subscribe(state => {
      value = state;
    });
    
    // Set various values
    blueprintWizard.setRangeDetails('Test Range', 'azure', true, true);
    blueprintWizard.addVPC({
      name: 'Test VPC',
      cidr: '10.0.0.0/16',
      subnets: []
    });
    
    // Reset the store
    blueprintWizard.reset();
    
    // Check that values are back to defaults
    expect(value.name).toBe('');
    expect(value.provider).toBe('aws');
    expect(value.vnc).toBe(false);
    expect(value.vpn).toBe(false);
    expect(value.vpcs).toEqual([]);
    
    unsubscribe();
  });
});