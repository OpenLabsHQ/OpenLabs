import { writable } from 'svelte/store'
import type { OpenLabsProvider } from '$lib/types/providers'
import type { OpenLabsOS } from '$lib/types/os'
import type { OpenLabsSpec } from '$lib/types/specs'

// Define the blueprint structure interfaces
export interface BlueprintHost {
  hostname: string
  os: OpenLabsOS
  spec: OpenLabsSpec
  size: number
  tags: string[]
  count?: number // Number of identical machines to create
}

export interface BlueprintSubnet {
  name: string
  cidr: string
  hosts: BlueprintHost[]
}

export interface BlueprintVPC {
  name: string
  cidr: string
  subnets: BlueprintSubnet[]
}

export interface BlueprintRange {
  name: string
  provider: OpenLabsProvider
  vnc: boolean
  vpn: boolean
  vpcs: BlueprintVPC[]
}

// Initial empty blueprint
const initialBlueprint: BlueprintRange = {
  name: '',
  provider: 'aws', // Default provider
  vnc: false,
  vpn: false,
  vpcs: [],
}

// Create the writable store
function createBlueprintWizardStore() {
  const { subscribe, set, update } = writable<BlueprintRange>(initialBlueprint)

  return {
    subscribe,
    // Reset to initial state
    reset: () => set({ ...initialBlueprint }),

    // Update range details (step 1)
    setRangeDetails: (
      name: string,
      provider: OpenLabsProvider,
      vnc: boolean,
      vpn: boolean
    ) => update((blueprint) => ({ ...blueprint, name, provider, vnc, vpn })),

    // Add a VPC (step 2)
    addVPC: (vpc: BlueprintVPC) =>
      update((blueprint) => ({
        ...blueprint,
        vpcs: [...blueprint.vpcs, vpc],
      })),

    // Update an existing VPC
    updateVPC: (index: number, vpc: BlueprintVPC) =>
      update((blueprint) => {
        const vpcs = [...blueprint.vpcs]
        vpcs[index] = vpc
        return { ...blueprint, vpcs }
      }),

    // Add a subnet to a VPC
    addSubnet: (vpcIndex: number, subnet: BlueprintSubnet) =>
      update((blueprint) => {
        const vpcs = [...blueprint.vpcs]
        if (vpcs[vpcIndex]) {
          vpcs[vpcIndex] = {
            ...vpcs[vpcIndex],
            subnets: [...vpcs[vpcIndex].subnets, subnet],
          }
        }
        return { ...blueprint, vpcs }
      }),

    // Update an existing subnet
    updateSubnet: (
      vpcIndex: number,
      subnetIndex: number,
      subnet: BlueprintSubnet
    ) =>
      update((blueprint) => {
        const vpcs = [...blueprint.vpcs]
        if (vpcs[vpcIndex] && vpcs[vpcIndex].subnets[subnetIndex]) {
          const subnets = [...vpcs[vpcIndex].subnets]
          subnets[subnetIndex] = subnet
          vpcs[vpcIndex] = { ...vpcs[vpcIndex], subnets }
        }
        return { ...blueprint, vpcs }
      }),

    // Add a host to a subnet
    addHost: (vpcIndex: number, subnetIndex: number, host: BlueprintHost) =>
      update((blueprint) => {
        const vpcs = [...blueprint.vpcs]
        if (vpcs[vpcIndex] && vpcs[vpcIndex].subnets[subnetIndex]) {
          const subnets = [...vpcs[vpcIndex].subnets]
          subnets[subnetIndex] = {
            ...subnets[subnetIndex],
            hosts: [...subnets[subnetIndex].hosts, host],
          }
          vpcs[vpcIndex] = { ...vpcs[vpcIndex], subnets }
        }
        return { ...blueprint, vpcs }
      }),

    // Update an existing host
    updateHost: (
      vpcIndex: number,
      subnetIndex: number,
      hostIndex: number,
      host: BlueprintHost
    ) =>
      update((blueprint) => {
        const vpcs = [...blueprint.vpcs]
        if (vpcs[vpcIndex] && vpcs[vpcIndex].subnets[subnetIndex]) {
          const subnets = [...vpcs[vpcIndex].subnets]
          const hosts = [...subnets[subnetIndex].hosts]
          hosts[hostIndex] = host
          subnets[subnetIndex] = { ...subnets[subnetIndex], hosts }
          vpcs[vpcIndex] = { ...vpcs[vpcIndex], subnets }
        }
        return { ...blueprint, vpcs }
      }),

    // Remove a VPC
    removeVPC: (index: number) =>
      update((blueprint) => ({
        ...blueprint,
        vpcs: blueprint.vpcs.filter((_, i) => i !== index),
      })),

    // Remove a subnet
    removeSubnet: (vpcIndex: number, subnetIndex: number) =>
      update((blueprint) => {
        const vpcs = [...blueprint.vpcs]
        if (vpcs[vpcIndex]) {
          vpcs[vpcIndex] = {
            ...vpcs[vpcIndex],
            subnets: vpcs[vpcIndex].subnets.filter((_, i) => i !== subnetIndex),
          }
        }
        return { ...blueprint, vpcs }
      }),

    // Remove a host
    removeHost: (vpcIndex: number, subnetIndex: number, hostIndex: number) =>
      update((blueprint) => {
        const vpcs = [...blueprint.vpcs]
        if (vpcs[vpcIndex] && vpcs[vpcIndex].subnets[subnetIndex]) {
          const subnets = [...vpcs[vpcIndex].subnets]
          subnets[subnetIndex] = {
            ...subnets[subnetIndex],
            hosts: subnets[subnetIndex].hosts.filter((_, i) => i !== hostIndex),
          }
          vpcs[vpcIndex] = { ...vpcs[vpcIndex], subnets }
        }
        return { ...blueprint, vpcs }
      }),

    // Duplicate hosts from one subnet to another
    duplicateHosts: (
      sourceVpcIndex: number,
      sourceSubnetIndex: number,
      targetVpcIndex: number,
      targetSubnetIndex: number
    ) =>
      update((blueprint) => {
        const vpcs = [...blueprint.vpcs]

        // Ensure source and target exist
        if (
          !vpcs[sourceVpcIndex] ||
          !vpcs[sourceVpcIndex].subnets[sourceSubnetIndex] ||
          !vpcs[targetVpcIndex] ||
          !vpcs[targetVpcIndex].subnets[targetSubnetIndex]
        ) {
          return blueprint
        }

        // Get hosts to duplicate
        const sourceHosts =
          vpcs[sourceVpcIndex].subnets[sourceSubnetIndex].hosts

        // Get existing target hosts for hostname conflict checking
        const targetSubnet = vpcs[targetVpcIndex].subnets[targetSubnetIndex]
        const existingHostnames = new Set(
          targetSubnet.hosts.map((host) => host.hostname)
        )

        // Clone hosts with unique hostnames
        const hostsToAdd = sourceHosts.map((host) => {
          let newHostname = host.hostname
          let counter = 1

          // Ensure hostname is unique in target subnet
          while (existingHostnames.has(newHostname)) {
            newHostname = `${host.hostname}-copy${counter}`
            counter++
          }

          existingHostnames.add(newHostname)

          // Return a new host object with the updated hostname
          return {
            ...JSON.parse(JSON.stringify(host)), // Deep clone
            hostname: newHostname,
          }
        })

        // Add hosts to target subnet
        const subnets = [...vpcs[targetVpcIndex].subnets]
        subnets[targetSubnetIndex] = {
          ...subnets[targetSubnetIndex],
          hosts: [...subnets[targetSubnetIndex].hosts, ...hostsToAdd],
        }
        vpcs[targetVpcIndex] = { ...vpcs[targetVpcIndex], subnets }

        return { ...blueprint, vpcs }
      }),
  }
}

// Export the store instance
export const blueprintWizard = createBlueprintWizardStore()