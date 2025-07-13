<script lang="ts">
  import { goto } from '$app/navigation'
  import {
    blueprintWizard,
    type BlueprintHost,
    type BlueprintVPC,
  } from '$lib/stores/blueprint-wizard'
  import { onMount } from 'svelte'
  import { OSOptions, type OpenLabsOS, osSizeThresholds } from '$lib/types/os'
  import { SpecOptions, type OpenLabsSpec } from '$lib/types/specs'

  // VPC and subnet selection
  let selectedVpcIndex = 0
  let selectedSubnetIndex = 0
  let vpcs: BlueprintVPC[] = []

  // Host form data
  let hostname = ''
  let os: OpenLabsOS = 'debian_11'
  let prevOS: OpenLabsOS = 'debian_11'
  let spec: OpenLabsSpec = 'small'
  let size = 8
  let tagsInput = ''
  let count = 1
  let showAdvancedOptions = false
  let showDuplicateOptions = false

  // Duplication source selection
  let sourceVpcIndex = 0
  let sourceSubnetIndex = 0

  // Form validation
  let errors = {
    hostname: '',
    os: '',
    spec: '',
    size: '',
    vpc: '',
    subnet: '',
    count: '',
    duplication: '',
  }

  // Initialize from store
  onMount(() => {
    // Check if we have subnets before proceeding
    const hasSubnets = $blueprintWizard.vpcs.some(
      (vpc) => vpc.subnets.length > 0
    )
    if (!hasSubnets) {
      goto('/blueprints/create/subnet')
      return
    }

    vpcs = [...$blueprintWizard.vpcs]

    // Find first VPC with subnets
    const vpcWithSubnetsIndex = vpcs.findIndex((vpc) => vpc.subnets.length > 0)
    if (vpcWithSubnetsIndex >= 0) {
      selectedVpcIndex = vpcWithSubnetsIndex
    }

    // Set initial disk size based on default OS
    if (size === null || size === undefined) {
      size = osSizeThresholds[os] || 8
    }
  })

  // Reactive declarations for current selections
  $: selectedVpc = vpcs[selectedVpcIndex] || null
  $: subnets = selectedVpc ? selectedVpc.subnets : []
  $: selectedSubnet = subnets[selectedSubnetIndex] || null
  $: hosts = selectedSubnet ? selectedSubnet.hosts : []

  // Reactive declarations for source selections (duplication)
  $: sourceVpc = vpcs[sourceVpcIndex] || null
  $: sourceSubnets = sourceVpc ? sourceVpc.subnets : []
  $: sourceSubnet = sourceSubnets[sourceSubnetIndex] || null
  $: sourceHosts = sourceSubnet ? sourceSubnet.hosts : []

  // Update size when OS changes or size is changed
  $: {
    // Only enforce minimum on blur or form submission, not during typing
    // This allows users to type values below minimum temporarily
    const minSize = osSizeThresholds[os] || 8
    // We still update the size when OS changes (which could affect minimum requirements)
    if (size !== null && size !== undefined && os && prevOS !== os && size < minSize) {
      size = minSize
    }
    prevOS = os
  }

  // Clear count error when count changes
  $: {
    if (errors.count && count >= 1 && count <= 100) {
      errors.count = ''
    }
  }

  // Convert tags string to array
  function getTags(): string[] {
    return tagsInput
      .split(',')
      .map((tag) => tag.trim())
      .filter((tag) => tag.length > 0)
  }

  function validateForm() {
    let isValid = true

    // Reset errors
    errors.hostname = ''
    errors.os = ''
    errors.spec = ''
    errors.size = ''
    errors.vpc = ''
    errors.subnet = ''
    errors.count = ''

    // Validate VPC and subnet selections
    if (!selectedVpc) {
      errors.vpc = 'Please select a VPC'
      isValid = false
    }

    if (!selectedSubnet) {
      errors.subnet = 'Please select a subnet'
      isValid = false
    }

    // Validate hostname
    const hostnamePattern = /^[a-z0-9]([a-z0-9-]*[a-z0-9])?$/
    if (!hostname.trim()) {
      errors.hostname = 'Hostname is required'
      isValid = false
    } else if (!hostnamePattern.test(hostname)) {
      errors.hostname =
        'Hostname must contain only lowercase letters, numbers, and hyphens, and cannot start or end with a hyphen'
      isValid = false
    }

    // Validate count
    if (count < 1 || count > 100) {
      errors.count = 'Count must be between 1 and 100'
      isValid = false
    }

    // When creating multiple hosts, check for name conflicts with auto-generated names
    if (count > 1) {
      // Use the base hostname and append numbers automatically
      const baseHostname = hostname.endsWith('-') ? hostname : `${hostname}-`

      // Check if all potential hostnames are available
      for (let i = 1; i <= count; i++) {
        const newHostname = `${baseHostname}${i}`

        if (
          selectedSubnet &&
          selectedSubnet.hosts.some((host) => host.hostname === newHostname)
        ) {
          errors.hostname = `Host with hostname ${newHostname} already exists in this subnet`
          isValid = false
          break
        }
      }
    } else {
      // Check for duplicate hostnames when creating a single host
      if (
        hostname &&
        selectedSubnet &&
        selectedSubnet.hosts.some((host) => host.hostname === hostname)
      ) {
        errors.hostname =
          'Host with this hostname already exists in this subnet'
        isValid = false
      }
    }

    // Validate size
    const minSize = osSizeThresholds[os] || 8
    if (size === null || size === undefined) {
      errors.size = `Disk size is required`
      isValid = false
    } else if (size < minSize) {
      errors.size = `Minimum disk size for ${os} is ${minSize}GB`
      isValid = false
    }

    return isValid
  }

  function addHost() {
    if (validateForm()) {
      if (count === 1) {
        // Create a single host
        const newHost: BlueprintHost = {
          hostname,
          os,
          spec,
          size,
          tags: getTags(),
          count: 1,
        }

        // Add to store
        blueprintWizard.addHost(selectedVpcIndex, selectedSubnetIndex, newHost)
      } else {
        // Create multiple hosts with sequential hostnames
        const baseHostname = hostname.endsWith('-') ? hostname : `${hostname}-`

        // Add each host individually with the correct sequential hostname
        for (let i = 1; i <= count; i++) {
          const newHostname = `${baseHostname}${i}`

          const newHost: BlueprintHost = {
            hostname: newHostname,
            os,
            spec,
            size,
            tags: getTags(),
          }

          blueprintWizard.addHost(selectedVpcIndex, selectedSubnetIndex, newHost)
        }
      }

      // Update local state
      vpcs = [...$blueprintWizard.vpcs]

      // Reset form
      hostname = ''
      tagsInput = ''
      // Keep count, OS, spec, and size values for faster data entry
    }
  }

  function removeHost(hostIndex: number) {
    blueprintWizard.removeHost(selectedVpcIndex, selectedSubnetIndex, hostIndex)
    vpcs = [...$blueprintWizard.vpcs]
  }

  let validationError = ''

  function handleNext() {
    // Check if at least one host exists
    const hasHosts = vpcs.some((vpc) =>
      vpc.subnets.some((subnet) => subnet.hosts.length > 0)
    )

    if (!hasHosts) {
      validationError = 'Please add at least one host before proceeding'
      return
    }

    validationError = ''
    goto('/blueprints/create/review')
  }

  // Handle VPC change - reset subnet selection
  function handleVpcChange() {
    selectedSubnetIndex = 0
  }

  function handleSourceVpcChange() {
    sourceSubnetIndex = 0
  }

  function duplicateHosts() {
    // Reset error
    errors.duplication = ''

    // Validate that we're not duplicating to the same subnet
    if (
      selectedVpcIndex === sourceVpcIndex &&
      selectedSubnetIndex === sourceSubnetIndex
    ) {
      errors.duplication = 'Cannot duplicate hosts to the same subnet'
      return
    }

    // Validate that source has hosts
    if (!sourceHosts.length) {
      errors.duplication = 'Source subnet has no hosts to duplicate'
      return
    }

    // Call the store method to duplicate hosts
    blueprintWizard.duplicateHosts(
      sourceVpcIndex,
      sourceSubnetIndex,
      selectedVpcIndex,
      selectedSubnetIndex
    )

    // Update local state
    vpcs = [...$blueprintWizard.vpcs]

    // Hide duplication panel
    showDuplicateOptions = false
  }
</script>

<svelte:head>
  <title>Host Configuration | Create Blueprint</title>
</svelte:head>

<div class="mx-auto max-w-4xl rounded-lg bg-white p-6 shadow-sm">
  <h2 class="mb-6 text-xl font-semibold">Host Configuration</h2>

  <!-- VPC and Subnet Selection -->
  <div class="mb-6">
    <div class="grid gap-4 md:grid-cols-2">
      <!-- VPC Selection -->
      <div>
        <label
          for="vpc-select"
          class="mb-1 block text-sm font-medium text-gray-700">Select VPC</label
        >
        <select
          id="vpc-select"
          bind:value={selectedVpcIndex}
          on:change={handleVpcChange}
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

      <!-- Subnet Selection -->
      <div>
        <label
          for="subnet-select"
          class="mb-1 block text-sm font-medium text-gray-700"
          >Select Subnet</label
        >
        <select
          id="subnet-select"
          bind:value={selectedSubnetIndex}
          class="w-full rounded border border-gray-300 p-2 focus:border-blue-500 focus:ring-blue-500"
          disabled={!subnets.length}
        >
          {#each subnets as subnet, index}
            <option value={index}>{subnet.name} ({subnet.cidr})</option>
          {/each}
        </select>
        {#if errors.subnet}
          <p class="mt-1 text-sm text-red-600">{errors.subnet}</p>
        {/if}
        {#if !subnets.length}
          <p class="mt-1 text-sm text-amber-600">
            This VPC has no subnets. Please add subnets first.
          </p>
        {/if}
      </div>
    </div>

    {#if selectedSubnet}
      <div class="mt-3 flex justify-end">
        <button
          type="button"
          class="flex items-center rounded-md border border-gray-300 bg-white px-3 py-1 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50"
          on:click={() => (showDuplicateOptions = !showDuplicateOptions)}
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="mr-1 h-4 w-4 text-purple-600"
            viewBox="0 0 20 20"
            fill="currentColor"
          >
            <path
              d="M7 9a2 2 0 012-2h6a2 2 0 012 2v6a2 2 0 01-2 2H9a2 2 0 01-2-2V9z"
            />
            <path d="M5 3a2 2 0 00-2 2v6a2 2 0 002 2V5h8a2 2 0 00-2-2H5z" />
          </svg>
          {showDuplicateOptions ? 'Hide Duplicate Options' : 'Duplicate Hosts'}
        </button>
      </div>

      {#if showDuplicateOptions}
        <div
          class="mt-3 rounded-md border border-gray-200 bg-white p-4 shadow-sm"
        >
          <h4 class="mb-2 text-sm font-medium text-gray-700">
            Duplicate Hosts from Another Subnet
          </h4>

          <div class="mb-3">
            <div class="mb-2 flex items-center gap-2">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="h-5 w-5 text-blue-600"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fill-rule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zm.707-10.293a1 1 0 00-1.414-1.414l-3 3a1 1 0 000 1.414l3 3a1 1 0 001.414-1.414L9.414 11H13a1 1 0 100-2H9.414l1.293-1.293z"
                  clip-rule="evenodd"
                />
              </svg>
              <h5 class="text-sm font-medium text-blue-800">Copy From:</h5>
            </div>

            <div class="pl-7">
              <div
                class="mb-3 rounded-md border border-blue-100 bg-blue-50 p-3"
              >
                <div class="grid gap-4 md:grid-cols-2">
                  <!-- Source VPC Selection -->
                  <div>
                    <div class="mb-1 flex items-center">
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        class="mr-2 h-4 w-4 text-blue-700"
                        viewBox="0 0 20 20"
                        fill="currentColor"
                      >
                        <path
                          fill-rule="evenodd"
                          d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z"
                          clip-rule="evenodd"
                        />
                      </svg>
                      <label
                        for="source-vpc-select"
                        class="text-sm font-medium text-blue-800">VPC</label
                      >
                    </div>
                    <select
                      id="source-vpc-select"
                      bind:value={sourceVpcIndex}
                      on:change={handleSourceVpcChange}
                      class="w-full rounded border border-gray-300 p-2 focus:border-blue-500 focus:ring-blue-500"
                    >
                      {#each vpcs as vpc, index}
                        <option value={index}>{vpc.name} ({vpc.cidr})</option>
                      {/each}
                    </select>
                  </div>

                  <!-- Source Subnet Selection -->
                  <div>
                    <div class="mb-1 flex items-center">
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        class="mr-2 h-4 w-4 text-blue-700"
                        viewBox="0 0 20 20"
                        fill="currentColor"
                      >
                        <path
                          d="M5 3a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2V5a2 2 0 00-2-2H5zM5 11a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2v-2a2 2 0 00-2-2H5zM11 5a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V5zM11 13a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"
                        />
                      </svg>
                      <label
                        for="source-subnet-select"
                        class="text-sm font-medium text-blue-800">Subnet</label
                      >
                    </div>
                    <select
                      id="source-subnet-select"
                      bind:value={sourceSubnetIndex}
                      class="w-full rounded border border-gray-300 p-2 focus:border-blue-500 focus:ring-blue-500"
                      disabled={!sourceSubnets.length}
                    >
                      {#each sourceSubnets as subnet, index}
                        <option value={index}
                          >{subnet.name} ({subnet.hosts.length} host{subnet
                            .hosts.length !== 1
                            ? 's'
                            : ''})</option
                        >
                      {/each}
                    </select>
                    {#if !sourceSubnets.length}
                      <p class="mt-1 text-sm text-amber-600">
                        This VPC has no subnets.
                      </p>
                    {/if}
                  </div>
                </div>

                {#if sourceHosts.length > 0}
                  <div class="mt-2 border-t border-blue-100 pt-2">
                    <div class="flex items-start">
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        class="mt-0.5 mr-2 h-4 w-4 text-blue-700"
                        viewBox="0 0 20 20"
                        fill="currentColor"
                      >
                        <path
                          d="M13 6a3 3 0 11-6 0 3 3 0 016 0zM18 8a2 2 0 11-4 0 2 2 0 014 0zM14 15a4 4 0 00-8 0v3h8v-3zM6 8a2 2 0 11-4 0 2 2 0 014 0zM16 18v-3a5.972 5.972 0 00-.75-2.906A3.005 3.005 0 0119 15v3h-3zM4.75 12.094A5.973 5.973 0 004 15v3H1v-3a3 3 0 013.75-2.906z"
                        />
                      </svg>
                      <div>
                        <span class="text-sm font-medium text-blue-800"
                          >Hosts:</span
                        >
                        <span class="ml-1 text-gray-700"
                          >{sourceHosts.length} available</span
                        >
                      </div>
                    </div>
                  </div>
                {/if}
              </div>
            </div>
          </div>

          <div class="mb-3">
            <div class="mb-2 flex items-center gap-2">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="h-5 w-5 text-green-600"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fill-rule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-8.707l-3-3a1 1 0 00-1.414 1.414L10.586 9H7a1 1 0 100 2h3.586l-1.293 1.293a1 1 0 101.414 1.414l3-3a1 1 0 000-1.414z"
                  clip-rule="evenodd"
                />
              </svg>
              <h5 class="text-sm font-medium text-green-800">Copy To:</h5>
            </div>

            <div class="pl-7">
              <div class="rounded-md border border-green-100 bg-green-50 p-3">
                <div class="mb-1 flex items-center">
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    class="mr-2 h-4 w-4 text-green-700"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path
                      fill-rule="evenodd"
                      d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z"
                      clip-rule="evenodd"
                    />
                  </svg>
                  <span class="font-medium text-green-800">VPC:</span>
                  <span class="ml-2 text-gray-700"
                    >{selectedVpc?.name} ({selectedVpc?.cidr})</span
                  >
                </div>
                <div class="flex items-center">
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    class="mr-2 h-4 w-4 text-green-700"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path
                      d="M5 3a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2V5a2 2 0 00-2-2H5zM5 11a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2v-2a2 2 0 00-2-2H5zM11 5a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V5zM11 13a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"
                    />
                  </svg>
                  <span class="font-medium text-green-800">Subnet:</span>
                  <span class="ml-2 text-gray-700"
                    >{selectedSubnet?.name} ({selectedSubnet?.cidr})</span
                  >
                </div>
              </div>
            </div>
          </div>

          <div class="mt-4 border-t border-blue-200 pt-3">
            {#if sourceHosts.length > 0}
              <div class="flex flex-col items-center">
                <div class="mb-3 flex flex-col items-center">
                  <div class="flex items-center text-sm text-gray-600">
                    <span class="font-medium text-blue-700"
                      >{sourceSubnet?.name}</span
                    >
                    <span class="mx-2">→</span>
                    <span class="font-medium text-green-700"
                      >{selectedSubnet?.name}</span
                    >
                  </div>
                  <div class="mt-1 flex items-center">
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      class="mr-1 h-4 w-4 text-gray-500"
                      viewBox="0 0 20 20"
                      fill="currentColor"
                    >
                      <path
                        d="M13 6a3 3 0 11-6 0 3 3 0 016 0zM18 8a2 2 0 11-4 0 2 2 0 014 0zM14 15a4 4 0 00-8 0v3h8v-3zM6 8a2 2 0 11-4 0 2 2 0 014 0zM16 18v-3a5.972 5.972 0 00-.75-2.906A3.005 3.005 0 0119 15v3h-3zM4.75 12.094A5.973 5.973 0 004 15v3H1v-3a3 3 0 013.75-2.906z"
                      />
                    </svg>
                    <span class="text-sm text-gray-600">
                      <strong>{sourceHosts.length}</strong>
                      host{sourceHosts.length !== 1 ? 's' : ''} will be copied
                    </span>
                  </div>
                </div>

                <button
                  type="button"
                  class="flex items-center rounded-md border border-transparent bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-700"
                  on:click={duplicateHosts}
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    class="mr-2 h-4 w-4"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path
                      d="M7 9a2 2 0 012-2h6a2 2 0 012 2v6a2 2 0 01-2 2H9a2 2 0 01-2-2V9z"
                    />
                    <path
                      d="M5 3a2 2 0 00-2 2v6a2 2 0 002 2V5h8a2 2 0 00-2-2H5z"
                    />
                  </svg>
                  Duplicate Hosts
                </button>
              </div>
            {:else}
              <p class="text-center text-sm text-amber-600">
                The selected source subnet has no hosts to duplicate.
              </p>
            {/if}

            {#if errors.duplication}
              <p class="mt-2 text-center text-sm text-red-600">
                {errors.duplication}
              </p>
            {/if}
          </div>
        </div>
      {/if}
    {/if}
  </div>

  <!-- Current Hosts -->
  {#if selectedSubnet && hosts.length > 0}
    <div class="mb-8">
      <h3 class="mb-3 text-base font-medium">Hosts in {selectedSubnet.name}</h3>

      <div class="rounded-md bg-gray-50 p-2">
        {#each hosts as host, index}
          <div
            class="flex items-center justify-between px-3 py-2 {index !==
            hosts.length - 1
              ? 'border-b border-gray-200'
              : ''}"
          >
            <div>
              <span class="font-medium">{host.hostname}</span>
              <span class="ml-2 text-sm text-gray-500">{host.os}</span>
              <span class="ml-2 text-sm text-gray-500">{host.spec}</span>
              <span class="ml-2 text-xs text-gray-400">{host.size}GB</span>
              {#if host.tags.length > 0}
                <div class="mt-1">
                  {#each host.tags as tag}
                    <span
                      class="mr-1 inline-block rounded bg-blue-100 px-2 py-0.5 text-xs text-blue-800"
                      >{tag}</span
                    >
                  {/each}
                </div>
              {/if}
            </div>
            <div class="flex space-x-2">
              <button
                type="button"
                class="text-sm text-red-600 hover:text-red-800"
                on:click={() => removeHost(index)}
              >
                Remove
              </button>
            </div>
          </div>
        {/each}
      </div>
    </div>
  {/if}

  <!-- Add Host Form -->
  <div class="border-t border-gray-200 pt-6">
    <h3 class="mb-4 text-base font-medium">
      Add New Host to {selectedSubnet?.name || 'Subnet'}
    </h3>

    <div class="grid gap-4 md:grid-cols-2">
      <!-- Hostname -->
      <div>
        <label
          for="hostname"
          class="mb-1 block text-sm font-medium text-gray-700">Hostname</label
        >
        <input
          type="text"
          id="hostname"
          bind:value={hostname}
          class="w-full rounded border border-gray-300 p-2 focus:border-blue-500 focus:ring-blue-500"
          placeholder="e.g., web-server-1"
        />
        {#if errors.hostname}
          <p class="mt-1 text-sm text-red-600">{errors.hostname}</p>
        {/if}
      </div>

      <!-- Operating System -->
      <div>
        <label for="os" class="mb-1 block text-sm font-medium text-gray-700"
          >Operating System</label
        >
        <select
          id="os"
          bind:value={os}
          class="w-full rounded border border-gray-300 p-2 focus:border-blue-500 focus:ring-blue-500"
        >
          {#each OSOptions as option}
            <option value={option.value}>{option.label}</option>
          {/each}
        </select>
      </div>

      <!-- VM Spec -->
      <div>
        <label for="spec" class="mb-1 block text-sm font-medium text-gray-700"
          >VM Specification</label
        >
        <select
          id="spec"
          bind:value={spec}
          class="w-full rounded border border-gray-300 p-2 focus:border-blue-500 focus:ring-blue-500"
        >
          {#each SpecOptions as option}
            <option value={option.value}>{option.label}</option>
          {/each}
        </select>
      </div>

      <!-- Disk Size -->
      <div>
        <label for="size" class="mb-1 block text-sm font-medium text-gray-700"
          >Disk Size (GB)</label
        >
        <input
          type="number"
          id="size"
          bind:value={size}
          min={osSizeThresholds[os] || 8}
          class="w-full rounded border border-gray-300 p-2 focus:border-blue-500 focus:ring-blue-500"
          on:input={(e) => {
            if (e.target.value === '') {
              // Allow empty value in the input field
              size = null;
            }
          }}
          on:blur={() => {
            // Enforce minimum size after user finishes typing
            const minSize = osSizeThresholds[os] || 8;
            if (size !== null && size !== undefined && size < minSize) {
              size = minSize;
            }
          }}
        />
        {#if errors.size}
          <p class="mt-1 text-sm text-red-600">{errors.size}</p>
        {/if}
        <p class="mt-1 text-xs text-gray-500">
          Minimum size for {os.replace('_', ' ')}: {osSizeThresholds[os] || 8}GB
        </p>
      </div>

      <!-- Tags -->
      <div class="md:col-span-2">
        <label for="tags" class="mb-1 block text-sm font-medium text-gray-700"
          >Tags (comma-separated)</label
        >
        <input
          type="text"
          id="tags"
          bind:value={tagsInput}
          class="w-full rounded border border-gray-300 p-2 focus:border-blue-500 focus:ring-blue-500"
          placeholder="e.g., web, linux, production"
        />
        <p class="mt-1 text-xs text-gray-500">
          Optional. Add tags to help organize and filter hosts.
        </p>
      </div>

      <!-- Advanced Options Toggle -->
      <div class="mt-2 md:col-span-2">
        <button
          type="button"
          class="flex items-center text-sm text-blue-600 hover:text-blue-800"
          on:click={() => (showAdvancedOptions = !showAdvancedOptions)}
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="mr-1 h-4 w-4"
            viewBox="0 0 20 20"
            fill="currentColor"
          >
            {#if showAdvancedOptions}
              <path
                fill-rule="evenodd"
                d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
                clip-rule="evenodd"
              />
            {:else}
              <path
                fill-rule="evenodd"
                d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"
                clip-rule="evenodd"
              />
            {/if}
          </svg>
          Advanced Options
        </button>
      </div>

      <!-- Advanced Options Panel -->
      {#if showAdvancedOptions}
        <div
          class="mt-2 rounded-md border border-gray-200 bg-gray-50 p-4 md:col-span-2"
        >
          <div class="mb-4">
            <label
              for="count"
              class="mb-1 block text-sm font-medium text-gray-700"
            >
              Number of Machines to Create
            </label>
            <div class="flex items-center">
              <input
                type="number"
                id="count"
                bind:value={count}
                min="1"
                max="100"
                class="w-24 rounded border border-gray-300 p-2 focus:border-blue-500 focus:ring-blue-500"
              />
              <span class="ml-2 text-sm text-gray-500">machines</span>
            </div>
            {#if errors.count}
              <p class="mt-1 text-sm text-red-600">{errors.count}</p>
            {/if}
            {#if count > 1}
              <p class="mt-1 text-xs text-blue-600">
                We'll create {count} machines with hostnames {hostname.endsWith(
                  '-'
                )
                  ? hostname
                  : `${hostname}-`}1 through {hostname.endsWith('-')
                  ? hostname
                  : `${hostname}-`}{count}.
              </p>
            {/if}
          </div>
        </div>
      {/if}
    </div>

    <div class="mt-4">
      <button
        type="button"
        class="rounded-md border border-transparent bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        on:click={addHost}
        disabled={!selectedSubnet}
      >
        {count > 1 ? `Add ${count} Hosts` : 'Add Host'}
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
      on:click={() => goto('/blueprints/create/subnet')}
    >
      Back
    </button>
    <button
      type="button"
      class="rounded-md border border-transparent bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700"
      on:click={handleNext}
    >
      Next: Review & Create
    </button>
  </div>
</div>
