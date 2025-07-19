<script lang="ts">
  import { goto } from '$app/navigation'
  import { blueprintWizard, type BlueprintVPC } from '$lib/stores/blueprint-wizard'
  import { onMount } from 'svelte'

  // VPC form data
  let name = ''
  let cidr = ''

  // List of VPCs already added
  let vpcs: BlueprintVPC[] = []

  // Form validation
  let errors = {
    name: '',
    cidr: '',
  }

  // Initialize from store
  onMount(() => {
    // Check if we have range details before proceeding
    if (!$blueprintWizard.name) {
      goto('/blueprints/create')
      return
    }

    // Load existing VPCs
    vpcs = [...$blueprintWizard.vpcs]
  })

  function validateForm() {
    let isValid = true

    // Reset errors
    errors.name = ''
    errors.cidr = ''

    // Validate name
    if (!name.trim()) {
      errors.name = 'VPC name is required'
      isValid = false
    }

    // Validate CIDR
    const cidrPattern = /^(\d{1,3}\.){3}\d{1,3}\/\d{1,2}$/
    if (!cidr.trim()) {
      errors.cidr = 'CIDR range is required'
      isValid = false
    } else if (!cidrPattern.test(cidr)) {
      errors.cidr = 'CIDR must be in format like 192.168.0.0/16'
      isValid = false
    }

    // Check for duplicate VPC names
    if (name && vpcs.some((vpc) => vpc.name === name)) {
      errors.name = 'VPC with this name already exists'
      isValid = false
    }

    return isValid
  }

  function addVPC() {
    if (validateForm()) {
      // Create new VPC
      const newVPC: BlueprintVPC = {
        name,
        cidr,
        subnets: [],
      }

      // Add to store
      blueprintWizard.addVPC(newVPC)

      // Update local list
      vpcs = [...vpcs, newVPC]

      // Reset form
      name = ''
      cidr = ''
    }
  }

  function removeVPC(index: number) {
    blueprintWizard.removeVPC(index)
    vpcs = vpcs.filter((_, i) => i !== index)
  }

  let validationError = ''

  function handleNext() {
    if (vpcs.length === 0) {
      validationError = 'Please add at least one VPC before proceeding'
      return
    }
    validationError = ''
    goto('/blueprints/create/subnet')
  }
</script>

<svelte:head>
  <title>VPC Configuration | Create Blueprint</title>
</svelte:head>

<div class="mx-auto max-w-4xl rounded-lg bg-white p-6 shadow-sm">
  <h2 class="mb-6 text-xl font-semibold">VPC Configuration</h2>

  <!-- Current VPCs -->
  {#if vpcs.length > 0}
    <div class="mb-8">
      <h3 class="mb-3 text-base font-medium">Added VPCs</h3>
      <div class="rounded-md bg-gray-50 p-2">
        {#each vpcs as vpc, index}
          <div
            class="flex items-center justify-between px-3 py-2 {index !==
            vpcs.length - 1
              ? 'border-b border-gray-200'
              : ''}"
          >
            <div>
              <span class="font-medium">{vpc.name}</span>
              <span class="ml-2 text-sm text-gray-500">{vpc.cidr}</span>
            </div>
            <div class="flex space-x-2">
              <button
                type="button"
                class="text-sm text-red-600 hover:text-red-800"
                on:click={() => removeVPC(index)}
              >
                Remove
              </button>
            </div>
          </div>
        {/each}
      </div>
    </div>
  {/if}

  <!-- Add VPC Form -->
  <div class="border-t border-gray-200 pt-6">
    <h3 class="mb-4 text-base font-medium">Add New VPC</h3>

    <div class="grid gap-4 md:grid-cols-2">
      <!-- VPC Name -->
      <div>
        <label
          for="vpc-name"
          class="mb-1 block text-sm font-medium text-gray-700">VPC Name</label
        >
        <input
          type="text"
          id="vpc-name"
          bind:value={name}
          class="w-full rounded border border-gray-300 p-2 focus:border-blue-500 focus:ring-blue-500"
          placeholder="e.g., main-vpc"
        />
        {#if errors.name}
          <p class="mt-1 text-sm text-red-600">{errors.name}</p>
        {/if}
      </div>

      <!-- CIDR Range -->
      <div>
        <label
          for="vpc-cidr"
          class="mb-1 block text-sm font-medium text-gray-700">CIDR Range</label
        >
        <input
          type="text"
          id="vpc-cidr"
          bind:value={cidr}
          class="w-full rounded border border-gray-300 p-2 focus:border-blue-500 focus:ring-blue-500"
          placeholder="e.g., 192.168.0.0/16"
        />
        <p class="mt-1 text-xs text-gray-500">
          Recommended format: 192.168.0.0/16
        </p>
        {#if errors.cidr}
          <p class="mt-1 text-sm text-red-600">{errors.cidr}</p>
        {/if}
      </div>
    </div>

    <div class="mt-4">
      <button
        type="button"
        class="rounded-md border border-transparent bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        on:click={addVPC}
      >
        Add VPC
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
      on:click={() => goto('/blueprints/create')}
    >
      Back
    </button>
    <button
      type="button"
      class="rounded-md border border-transparent bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700"
      on:click={handleNext}
    >
      Next: Subnet Configuration
    </button>
  </div>
</div>
