<script lang="ts">
  import { goto } from '$app/navigation'
  import {
    blueprintWizard,
    type BlueprintSubnet,
    type BlueprintVPC,
  } from '$lib/stores/blueprint-wizard'
  import { onMount } from 'svelte'

  // Selected VPC
  let selectedVpcIndex = 0
  let vpcs: BlueprintVPC[] = []

  // Subnet form data
  let name = ''
  let cidr = ''

  // Form validation
  let errors = {
    name: '',
    cidr: '',
    vpc: '',
  }

  // Helper function to generate a subnet CIDR from VPC CIDR
  function suggestSubnetCidr(
    vpcCidr: string,
    existingSubnets: BlueprintSubnet[] = []
  ): string {
    try {
      // Parse the VPC CIDR (e.g., "192.168.0.0/16")
      const [baseIp, maskStr] = vpcCidr.split('/')
      const mask = parseInt(maskStr)

      if (mask >= 24) {
        // If the VPC mask is already /24 or smaller, we can't create smaller subnets
        return vpcCidr
      }

      // For a VPC like 192.168.0.0/16, we want to suggest sequential subnets
      // starting from 192.168.1.0/24 (not 192.168.0.0/24)
      const ipParts = baseIp.split('.').map((p) => parseInt(p))

      // If there are existing subnets, find the next available subnet number
      let nextSubnetNum = 1 // Start from 1 instead of 0

      if (existingSubnets.length > 0 && mask === 16) {
        // For /16 VPCs, find the next available third octet
        // (e.g., for 192.168.0.0/16, look at 192.168.X.0/24)
        const usedThirdOctets = existingSubnets
          .map((subnet) => {
            const parts = subnet.cidr.split('.')
            return parts.length >= 3 ? parseInt(parts[2]) : -1
          })
          .filter((num) => num >= 0)

        // Find the smallest unused number starting from 1
        for (let i = 1; i <= 255; i++) {
          if (!usedThirdOctets.includes(i)) {
            nextSubnetNum = i
            break
          }
        }
      }

      // Check if we're out of available subnets
      if (nextSubnetNum > 255) {
        // If we've used all possible subnets, return a default
        return '192.168.1.0/24'
      }

      if (mask === 16) {
        // For a /16 VPC like 192.168.0.0/16, suggest 192.168.X.0/24
        return `${ipParts[0]}.${ipParts[1]}.${nextSubnetNum}.0/24`
      }

      // For other masks, use the base IP with a /24 mask but increment the third octet
      const thirdOctet = ipParts.length > 2 ? Math.min(ipParts[2] + 1, 255) : 1
      return `${ipParts[0]}.${ipParts[1]}.${thirdOctet}.0/24`
    } catch {
      // If there's any parsing error, return a safe default
      return '192.168.1.0/24'
    }
  }

  // Function to check if a subnet CIDR is valid within a VPC CIDR
  function isSubnetCidrValid(subnetCidr: string, vpcCidr: string): boolean {
    try {
      // Parse CIDRs
      const [subnetIp, subnetMaskStr] = subnetCidr.split('/')
      const [vpcIp, vpcMaskStr] = vpcCidr.split('/')

      const subnetMask = parseInt(subnetMaskStr)
      const vpcMask = parseInt(vpcMaskStr)

      // Subnet mask must be larger (more specific) than VPC mask
      if (subnetMask <= vpcMask) {
        return false
      }

      // Convert IPs to binary representation for comparison
      const subnetIpParts = subnetIp.split('.').map((p) => parseInt(p))
      const vpcIpParts = vpcIp.split('.').map((p) => parseInt(p))

      // Check if the subnet is within the VPC range
      // For the common network bits (determined by VPC mask),
      // the subnet IP must match the VPC IP
      const commonOctets = Math.floor(vpcMask / 8)

      // Check full octets
      for (let i = 0; i < commonOctets; i++) {
        if (subnetIpParts[i] !== vpcIpParts[i]) {
          return false
        }
      }

      // Check partial octet if needed
      const remainingBits = vpcMask % 8
      if (remainingBits > 0) {
        const octetIndex = commonOctets

        // Create a mask for the remaining bits
        const mask = 256 - (1 << (8 - remainingBits))

        // Apply the mask and compare
        if (
          (subnetIpParts[octetIndex] & mask) !==
          (vpcIpParts[octetIndex] & mask)
        ) {
          return false
        }
      }

      return true
    } catch {
      return false
    }
  }

  // Initialize from store
  onMount(() => {
    // Check if we have VPCs before proceeding
    if (!$blueprintWizard.vpcs.length) {
      goto('/blueprints/create/vpc')
      return
    }

    vpcs = [...$blueprintWizard.vpcs]

    // Set initial CIDR based on first VPC
    if (vpcs.length > 0) {
      cidr = suggestSubnetCidr(vpcs[0].cidr, vpcs[0].subnets)
    }
  })

  // Get the currently selected VPC
  $: selectedVpc = vpcs[selectedVpcIndex] || null
  $: subnets = selectedVpc ? [...selectedVpc.subnets] : []

  // Update suggested CIDR when VPC changes
  $: if (selectedVpc) {
    // Update with next available subnet in the VPC
    cidr = suggestSubnetCidr(selectedVpc.cidr, selectedVpc.subnets)
  }

  function validateForm() {
    let isValid = true

    // Reset errors
    errors.name = ''
    errors.cidr = ''
    errors.vpc = ''

    // Validate VPC selection
    if (!selectedVpc) {
      errors.vpc = 'Please select a VPC'
      isValid = false
    }

    // Validate name
    if (!name.trim()) {
      errors.name = 'Subnet name is required'
      isValid = false
    }

    // Validate CIDR
    const cidrPattern = /^(\d{1,3}\.){3}\d{1,3}\/\d{1,2}$/
    if (!cidr.trim()) {
      errors.cidr = 'CIDR range is required'
      isValid = false
    } else if (!cidrPattern.test(cidr)) {
      errors.cidr = 'CIDR must be in format like 192.168.1.0/24'
      isValid = false
    } else if (selectedVpc && !isSubnetCidrValid(cidr, selectedVpc.cidr)) {
      errors.cidr = `Subnet CIDR must be within the VPC CIDR (${selectedVpc.cidr})`
      isValid = false
    }

    // Check for duplicate subnet names within the VPC
    if (
      name &&
      selectedVpc &&
      selectedVpc.subnets.some((subnet) => subnet.name === name)
    ) {
      errors.name = 'Subnet with this name already exists in this VPC'
      isValid = false
    }

    return isValid
  }

  function addSubnet() {
    if (validateForm()) {
      // Create new subnet
      const newSubnet: BlueprintSubnet = {
        name,
        cidr,
        hosts: [],
      }

      // Add to store
      blueprintWizard.addSubnet(selectedVpcIndex, newSubnet)

      // Update local state
      vpcs = [...$blueprintWizard.vpcs]

      // Reset form
      name = ''
      cidr = selectedVpc
        ? suggestSubnetCidr(selectedVpc.cidr, selectedVpc.subnets)
        : ''
    }
  }

  function removeSubnet(subnetIndex: number) {
    blueprintWizard.removeSubnet(selectedVpcIndex, subnetIndex)
    vpcs = [...$blueprintWizard.vpcs]
  }

  let validationError = ''

  function handleNext() {
    // Check if at least one subnet exists in any VPC
    const hasSubnets = vpcs.some((vpc) => vpc.subnets.length > 0)

    if (!hasSubnets) {
      validationError = 'Please add at least one subnet before proceeding'
      return
    }

    validationError = ''
    goto('/blueprints/create/host')
  }
</script>

<svelte:head>
  <title>Subnet Configuration | Create Blueprint</title>
</svelte:head>

<div class="mx-auto max-w-4xl rounded-lg bg-white p-6 shadow-sm">
  <h2 class="mb-6 text-xl font-semibold">Subnet Configuration</h2>

  <!-- VPC Selection -->
  <div class="mb-6">
    <label for="vpc-select" class="mb-1 block text-sm font-medium text-gray-700"
      >Select VPC</label
    >
    <select
      id="vpc-select"
      bind:value={selectedVpcIndex}
      class="w-full rounded border border-gray-300 p-2 focus:border-blue-500 focus:ring-blue-500"
    >
      {#each vpcs as vpc, index}
        <option value={index}>{vpc.name} ({vpc.cidr})</option>
      {/each}
    </select>
    {#if errors.vpc}
      <p class="mt-1 text-sm text-red-600">{errors.vpc}</p>
    {/if}
  </div>

  <!-- Current Subnets for the selected VPC -->
  {#if selectedVpc && subnets.length > 0}
    <div class="mb-8">
      <h3 class="mb-3 text-base font-medium">Subnets in {selectedVpc.name}</h3>
      <div class="rounded-md bg-gray-50 p-2">
        {#each subnets as subnet, index}
          <div
            class="flex items-center justify-between px-3 py-2 {index !==
            subnets.length - 1
              ? 'border-b border-gray-200'
              : ''}"
          >
            <div>
              <span class="font-medium">{subnet.name}</span>
              <span class="ml-2 text-sm text-gray-500">{subnet.cidr}</span>
              <span class="ml-2 text-xs text-gray-400"
                >{subnet.hosts.length} host(s)</span
              >
            </div>
            <div class="flex space-x-2">
              <button
                type="button"
                class="text-sm text-red-600 hover:text-red-800"
                on:click={() => removeSubnet(index)}
              >
                Remove
              </button>
            </div>
          </div>
        {/each}
      </div>
    </div>
  {/if}

  <!-- Add Subnet Form -->
  <div class="border-t border-gray-200 pt-6">
    <h3 class="mb-4 text-base font-medium">
      Add New Subnet to {selectedVpc?.name || 'VPC'}
    </h3>

    <div class="grid gap-4 md:grid-cols-2">
      <!-- Subnet Name -->
      <div>
        <label
          for="subnet-name"
          class="mb-1 block text-sm font-medium text-gray-700"
          >Subnet Name</label
        >
        <input
          type="text"
          id="subnet-name"
          bind:value={name}
          class="w-full rounded border border-gray-300 p-2 focus:border-blue-500 focus:ring-blue-500"
          placeholder="e.g., public-subnet-1"
        />
        {#if errors.name}
          <p class="mt-1 text-sm text-red-600">{errors.name}</p>
        {/if}
      </div>

      <!-- CIDR Range -->
      <div>
        <label
          for="subnet-cidr"
          class="mb-1 block text-sm font-medium text-gray-700">CIDR Range</label
        >
        <input
          type="text"
          id="subnet-cidr"
          bind:value={cidr}
          class="w-full rounded border border-gray-300 p-2 focus:border-blue-500 focus:ring-blue-500"
          placeholder="e.g., 192.168.1.0/24"
        />
        {#if errors.cidr}
          <p class="mt-1 text-sm text-red-600">{errors.cidr}</p>
        {/if}
        <p class="mt-1 text-xs text-gray-500">
          Must be contained within the VPC CIDR ({selectedVpc?.cidr || 'N/A'})
        </p>
      </div>
    </div>

    <div class="mt-4">
      <button
        type="button"
        class="rounded-md border border-transparent bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        on:click={addSubnet}
      >
        Add Subnet
      </button>
    </div>
  </div>

  <!-- Validation error message -->
  {#if validationError}
    <div class="mt-6 rounded-md border-l-4 border-red-500 bg-red-50 p-4">
      <div class="flex">
        <div class="flex-shrink-0">
          <svg
            class="h-5 w-5 text-red-500"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path
              fill-rule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
              clip-rule="evenodd"
            />
          </svg>
        </div>
        <div class="ml-3">
          <p class="text-sm leading-5 text-red-700">
            {validationError}
          </p>
        </div>
      </div>
    </div>
  {/if}

  <!-- Navigation -->
  <div class="mt-6 flex justify-between border-t border-gray-200 pt-8">
    <button
      type="button"
      class="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50"
      on:click={() => goto('/blueprints/create/vpc')}
    >
      Back
    </button>
    <button
      type="button"
      class="rounded-md border border-transparent bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700"
      on:click={handleNext}
    >
      Next: Host Configuration
    </button>
  </div>
</div>
