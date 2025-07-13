<script lang="ts">
  import { goto } from '$app/navigation'
  import { blueprintWizard } from '$lib/stores/blueprint-wizard'
  import type { OpenLabsProvider } from '$lib/types/providers'
  import type { BlueprintRange } from '$lib/stores/blueprint-wizard'
  import logger from '$lib/utils/logger'

  // Form data
  let name = $blueprintWizard.name || ''
  let provider: OpenLabsProvider = $blueprintWizard.provider || 'aws'
  let vnc = $blueprintWizard.vnc || false
  let vpn = $blueprintWizard.vpn || false

  // Advanced mode
  let showAdvanced = false
  let jsonBlueprint = ''
  let jsonError = ''

  // Form validation
  let errors = {
    name: '',
  }

  function validateForm() {
    let isValid = true

    // Reset errors
    errors.name = ''

    // Validate name
    if (!name.trim()) {
      errors.name = 'Range name is required'
      isValid = false
    } else if (name.length < 3) {
      errors.name = 'Range name must be at least 3 characters'
      isValid = false
    }

    return isValid
  }

  function handleSubmit() {
    if (validateForm()) {
      // Save to store
      blueprintWizard.setRangeDetails(name, provider, vnc, vpn)

      // Navigate to next step
      goto('/blueprints/create/vpc')
    }
  }

  function handleAdvancedSubmit() {
    try {
      jsonError = ''

      // Pre-process JSON - Sometimes users might forget to use double quotes for property names
      let processedJson = jsonBlueprint

      // Parse the JSON
      let blueprintData
      try {
        blueprintData = JSON.parse(processedJson) as BlueprintRange
      } catch (e: any) {
        logger.error('First JSON parse attempt failed', 'blueprints.create', e)
        // Show detailed error to help user fix their JSON
        jsonError = `JSON parse error: ${e.message}`
        return
      }

      // Basic validation
      if (!blueprintData) {
        jsonError = 'Invalid JSON: blueprint data is empty'
        return
      }

      // Validate minimum required structure
      if (!blueprintData.name || typeof blueprintData.name !== 'string') {
        jsonError = 'Blueprint must have a name property (string)'
        return
      }

      if (!blueprintData.provider) {
        jsonError = 'Blueprint must have a provider property'
        return
      }

      if (!Array.isArray(blueprintData.vpcs)) {
        jsonError = 'Blueprint must have a vpcs array property'
        return
      }

      // Ensure all properties exist with defaults
      blueprintData = {
        ...blueprintData,
        vnc: !!blueprintData.vnc,
        vpn: !!blueprintData.vpn,
      }

      // Ensure each VPC has required fields
      for (let i = 0; i < blueprintData.vpcs.length; i++) {
        const vpc = blueprintData.vpcs[i]
        if (!vpc.name || typeof vpc.name !== 'string') {
          jsonError = `VPC at index ${i} must have a name property (string)`
          return
        }

        if (!vpc.cidr || typeof vpc.cidr !== 'string') {
          jsonError = `VPC "${vpc.name}" must have a cidr property (string)`
          return
        }

        // Ensure subnets array exists
        if (!Array.isArray(vpc.subnets)) {
          vpc.subnets = []
        }

        // Check each subnet
        for (let j = 0; j < vpc.subnets.length; j++) {
          const subnet = vpc.subnets[j]

          if (!subnet.name || typeof subnet.name !== 'string') {
            jsonError = `Subnet at index ${j} in VPC "${vpc.name}" must have a name property (string)`
            return
          }

          if (!subnet.cidr || typeof subnet.cidr !== 'string') {
            jsonError = `Subnet "${subnet.name}" in VPC "${vpc.name}" must have a cidr property (string)`
            return
          }

          // Ensure hosts array exists
          if (!Array.isArray(subnet.hosts)) {
            subnet.hosts = []
          }

          // Check each host
          for (let k = 0; k < subnet.hosts.length; k++) {
            const host = subnet.hosts[k]

            if (!host.hostname || typeof host.hostname !== 'string') {
              jsonError = `Host at index ${k} in subnet "${subnet.name}" must have a hostname property (string)`
              return
            }

            if (!host.os || typeof host.os !== 'string') {
              jsonError = `Host "${host.hostname}" must have an os property (string)`
              return
            }

            if (!host.spec || typeof host.spec !== 'string') {
              jsonError = `Host "${host.hostname}" must have a spec property (string)`
              return
            }

            if (typeof host.size !== 'number' || host.size <= 0) {
              jsonError = `Host "${host.hostname}" must have a size property (positive number)`
              return
            }

            // Ensure tags array exists
            if (!Array.isArray(host.tags)) {
              host.tags = []
            }
          }
        }
      }

      // Validate at least one VPC with a subnet that has hosts
      const hasHosts = blueprintData.vpcs.some((vpc) =>
        vpc.subnets.some((subnet) => subnet.hosts.length > 0)
      )

      if (!hasHosts) {
        jsonError =
          'Blueprint must have at least one VPC with a subnet containing hosts'
        return
      }

      // Reset the store and set the entire blueprint
      blueprintWizard.reset()

      // Update basic properties
      blueprintWizard.setRangeDetails(
        blueprintData.name,
        blueprintData.provider,
        blueprintData.vnc || false,
        blueprintData.vpn || false
      )

      // Add each VPC with subnets and hosts
      for (const vpc of blueprintData.vpcs) {
        blueprintWizard.addVPC({
          name: vpc.name,
          cidr: vpc.cidr,
          subnets: vpc.subnets || [],
        })
      }

      // Wait a moment for store updates to propagate before redirecting
      setTimeout(() => {
        goto('/blueprints/create/review')
      }, 200)
    } catch (error: any) {
      jsonError = `Error processing blueprint: ${error.message}`
      logger.error('Blueprint processing error', 'blueprints.create', error)
    }
  }
</script>

<svelte:head>
  <title>Range Details | Create Blueprint</title>
</svelte:head>

<div class="mx-auto max-w-3xl rounded-lg bg-white p-6 shadow-sm">
  <h2 class="mb-6 text-xl font-semibold">Range Details</h2>

  {#if showAdvanced}
    <!-- Advanced JSON Mode -->
    <div class="space-y-6">
      <div>
        <div class="mb-2 flex items-center justify-between">
          <label
            for="json-blueprint"
            class="block text-sm font-medium text-gray-700">Blueprint JSON</label
          >
          <button
            type="button"
            class="text-xs text-blue-600 hover:text-blue-800"
            on:click={() => {
              jsonBlueprint = `{
  "vpcs": [
    {
      "cidr": "192.168.0.0/16",
      "name": "example-vpc-1",
      "subnets": [
        {
          "cidr": "192.168.1.0/24",
          "name": "example-subnet-1",
          "hosts": [
            {
              "hostname": "example-host-1",
              "os": "debian_11",
              "spec": "tiny",
              "size": 8,
              "tags": [
                "web",
                "linux"
              ]
            }
          ]
        }
      ]
    }
  ],
  "provider": "aws",
  "name": "example-range-1",
  "vnc": false,
  "vpn": false
}`
            }}
          >
            Load Example
          </button>
        </div>
        <textarea
          id="json-blueprint"
          bind:value={jsonBlueprint}
          rows="15"
          class="w-full rounded border border-gray-300 p-2 font-mono text-sm focus:border-blue-500 focus:ring-blue-500"
          placeholder={`{
  "name": "my-blueprint",
  "provider": "aws",
  "vnc": false,
  "vpn": true,
  "vpcs": [
    {
      "name": "main-vpc",
      "cidr": "10.0.0.0/16",
      "subnets": [
        {
          "name": "public-subnet",
          "cidr": "10.0.1.0/24",
          "hosts": [
            {
              "hostname": "jumpbox",
              "os": "ubuntu_20",
              "spec": "small",
              "size": 20,
              "tags": ["public", "jumpbox"]
            }
          ]
        }
      ]
    }
  ]
}`}
        ></textarea>
        {#if jsonError}
          <p class="mt-1 text-sm text-red-600">{jsonError}</p>
        {/if}
      </div>

      <!-- JSON Mode Navigation -->
      <div class="flex justify-end pt-4">
        <button
          type="button"
          class="mr-3 rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50"
          on:click={() => goto('/blueprints')}
        >
          Cancel
        </button>
        <button
          type="button"
          on:click={handleAdvancedSubmit}
          class="rounded-md border border-transparent bg-green-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-green-700"
        >
          Skip to Review
        </button>
      </div>
    </div>
  {:else}
    <!-- Standard Wizard Mode -->
    <form on:submit|preventDefault={handleSubmit} class="space-y-6">
      <!-- Range Name -->
      <div>
        <label for="name" class="mb-1 block text-sm font-medium text-gray-700"
          >Range Name</label
        >
        <input
          type="text"
          id="name"
          bind:value={name}
          class="w-full rounded border border-gray-300 p-2 focus:border-blue-500 focus:ring-blue-500"
          placeholder="Enter range name (e.g., my-training-range)"
        />
        {#if errors.name}
          <p class="mt-1 text-sm text-red-600">{errors.name}</p>
        {/if}
      </div>

      <!-- Cloud Provider -->
      <div>
        <p
          class="mb-1 block text-sm font-medium text-gray-700"
          id="provider-group-label"
        >
          Cloud Provider
        </p>
        <div
          class="flex space-x-4"
          role="radiogroup"
          aria-labelledby="provider-group-label"
        >
          <label class="inline-flex items-center" for="provider-aws">
            <input
              type="radio"
              id="provider-aws"
              bind:group={provider}
              value="aws"
              class="h-4 w-4 border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span class="ml-2">AWS</span>
          </label>
          <label class="inline-flex items-center" for="provider-azure">
            <input
              type="radio"
              id="provider-azure"
              bind:group={provider}
              value="azure"
              class="h-4 w-4 border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span class="ml-2">Azure</span>
          </label>
        </div>
      </div>

      <!-- Features -->
      <div>
        <p class="mb-2 block text-sm font-medium text-gray-700">Features</p>
        <div class="space-y-2">
          <label class="inline-flex items-center" for="feature-vnc">
            <input
              type="checkbox"
              id="feature-vnc"
              bind:checked={vnc}
              class="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span class="ml-2">Enable VNC configuration</span>
          </label>
          <div class="ml-6 text-sm text-gray-500">
            Allows secure remote desktop access to your virtual machines.
          </div>

          <label class="inline-flex items-center" for="feature-vpn">
            <input
              type="checkbox"
              id="feature-vpn"
              bind:checked={vpn}
              class="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span class="ml-2">Enable VPN configuration</span>
          </label>
          <div class="ml-6 text-sm text-gray-500">
            Creates a secure VPN connection to your range environment.
          </div>
        </div>
      </div>

      <!-- Navigation -->
      <div class="flex justify-end pt-4">
        <button
          type="button"
          class="mr-3 rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50"
          on:click={() => goto('/blueprints')}
        >
          Cancel
        </button>
        <button
          type="submit"
          class="rounded-md border border-transparent bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700"
        >
          Next: VPC Configuration
        </button>
      </div>
    </form>
  {/if}

  <!-- Advanced Mode Toggle -->
  <div class="mt-10 flex justify-center border-t border-gray-200 pt-6">
    <button
      type="button"
      class="flex items-center text-sm text-blue-600 hover:text-blue-800"
      on:click={() => (showAdvanced = !showAdvanced)}
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        class="mr-1 h-4 w-4"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d={showAdvanced ? 'M19 9l-7 7-7-7' : 'M9 5l7 7-7 7'}
        />
      </svg>
      {showAdvanced ? 'Standard Mode' : 'Advanced Mode (JSON)'}
    </button>
  </div>
</div>
