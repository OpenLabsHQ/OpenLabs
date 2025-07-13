<script lang="ts">
  import { onMount, onDestroy } from 'svelte'
  import { goto, beforeNavigate } from '$app/navigation'
  import { rangesApi } from '$lib/api'
  import { browser } from '$app/environment'
  import { auth } from '$lib/stores/auth'
  import Sidebar from '$lib/components/Sidebar.svelte'
  import NetworkGraph from '$lib/components/NetworkGraph.svelte'
  import LoadingSpinner from '$lib/components/LoadingSpinner.svelte'
  import { formatErrorMessage } from '$lib/utils/error'

  // Blueprint data
  let blueprint = null
  let isLoading = true
  let error = ''

  // Deployment status
  let deployingBlueprint = false
  let deploymentError = ''

  // Delete confirmation
  let showDeleteConfirm = false
  let deletingBlueprint = false
  let deleteSuccess = ''
  let deleteError = ''

  // Auto-dismiss timer
  let autoCloseTimer: ReturnType<typeof setTimeout> | null = null

  // Function to handle beforeunload event
  function handleBeforeUnload(event: BeforeUnloadEvent) {
    if (deployingBlueprint) {
      // Standard way to show a confirmation dialog when leaving page
      event.preventDefault();
      // This message text is displayed in some browsers, but most modern browsers use their own message
      event.returnValue = "A deployment is in progress. If you leave now, the deployment may be interrupted. Are you sure you want to leave?";
      return event.returnValue;
    }
  }
  
  // Use beforeNavigate (Svelte's built-in lifecycle hook) to handle navigation events like back button
  beforeNavigate(({ cancel }) => {
    if (deployingBlueprint) {
      if (confirm("A deployment is in progress. If you leave now, the deployment may be interrupted. Are you sure you want to leave?")) {
        // User confirmed they want to leave, let the navigation proceed
        return;
      }
      // User wants to stay, cancel the navigation
      cancel();
    }
  });
  
  // Set up and clean up event listeners
  onMount(() => {
    if (browser) {
      // Add beforeunload event listener when component is mounted (for closing tab/window)
      window.addEventListener('beforeunload', handleBeforeUnload);
    }
  });

  // Clean up timers and event listeners when component is destroyed
  onDestroy(() => {
    if (autoCloseTimer) {
      clearTimeout(autoCloseTimer)
    }
    
    // Remove beforeunload event listener when component is destroyed
    if (browser) {
      window.removeEventListener('beforeunload', handleBeforeUnload);
    }
  })

  // Get blueprint ID from +page.ts load function
  export let data

  // Function to load blueprint data
  async function loadBlueprintData(blueprintId: string) {
    try {
      isLoading = true
      error = ''

      const response = await rangesApi.getBlueprintById(blueprintId)

      if (response.error) {
        error = formatErrorMessage(response.error, 'Failed to load blueprint')
        return
      }

      if (!response.data) {
        error = 'No blueprint data received from API'
        return
      }

      blueprint = response.data
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to load blueprint'
    } finally {
      isLoading = false
    }
  }

  onMount(async () => {
    if (browser) {
      // Check authentication
      if (!$auth.isAuthenticated) {
        goto('/login')
        return
      }
      // Get the blueprint data from the API
      await loadBlueprintData(data.blueprintId)
    }
  })

  // Set auto-dismiss for notifications
  function setAutoDismiss(type: 'success' | 'error', notification: 'deploy' | 'delete', duration: number = 3000) {
    // Clear any existing timers
    if (autoCloseTimer) {
      clearTimeout(autoCloseTimer)
    }

    // Set a new timer
    autoCloseTimer = setTimeout(() => {
      if (type === 'success') {
        if (notification === 'delete') {
          deleteSuccess = ''
        }
        // Deploy success notifications no longer used (immediate redirect)
      } else {
        if (notification === 'deploy') {
          deploymentError = ''
        } else {
          deleteError = ''
        }
      }
      autoCloseTimer = null
    }, duration)
  }
  
  // Delete the blueprint
  async function deleteBlueprint(blueprintId: string) {
    // Reset notifications
    deleteError = ''
    deleteSuccess = ''
    
    // Set deleting state
    deletingBlueprint = true
    
    try {
      const result = await rangesApi.deleteBlueprint(blueprintId)
      
      if (result.error) {
        deleteError = result.error
        setAutoDismiss('error', 'delete', 5000) // Error messages stay longer
      } else {
        deleteSuccess = `Successfully deleted "${blueprint.name}"!`
        setAutoDismiss('success', 'delete', 3000)
        
        // Navigate back to blueprints page after successful deletion
        setTimeout(() => {
          goto('/blueprints')
        }, 1500)
      }
    } catch {
      deleteError = 'An unexpected error occurred while deleting the blueprint'
      setAutoDismiss('error', 'delete', 5000)
    } finally {
      deletingBlueprint = false
      showDeleteConfirm = false
    }
  }

  // Deploy the blueprint
  async function deployBlueprint(blueprintId: string) {
    // Reset notifications
    deploymentError = ''

    // Set deploying state
    deployingBlueprint = true

    try {
      // Create a name for the deployed range based on the blueprint name
      const rangeName = `${blueprint.name} Deployment`
      const description = `Deployed from blueprint: ${blueprint.name}`
      // Use 'us_east_1' as default region (must use underscore, not hyphen)
      const region = 'us_east_1'
      
      const result = await rangesApi.deployBlueprint(
        blueprintId,
        rangeName,
        description,
        region
      )

      if (result.error) {
        deploymentError = result.error
        setAutoDismiss('error', 'deploy', 5000) // Error messages stay longer
      } else {
        // Deployment job submitted successfully - redirect immediately
        const jobResponse = result.data
        if (jobResponse && jobResponse.arq_job_id) {
          // Redirect to range building page with job ID immediately
          goto(`/ranges/building/${jobResponse.arq_job_id}`)
        } else {
          deploymentError = 'Deployment started but no job ID returned'
          setAutoDismiss('error', 'deploy', 5000)
        }
      }
    } catch {
      deploymentError =
        'An unexpected error occurred while deploying the blueprint'
      setAutoDismiss('error', 'deploy', 5000)
    } finally {
      deployingBlueprint = false
    }
  }
</script>

<svelte:head>
  <title>OpenLabs | Blueprint Details</title>
</svelte:head>

<div class="font-roboto flex h-screen bg-gray-100">
  <!-- Fixed sidebar -->
  <div class="fixed inset-y-0 left-0 z-10 w-54">
    <Sidebar />
  </div>

  <!-- Main content with sidebar margin -->
  <div class="ml-54 flex-1 overflow-y-auto">
    <div class="p-6">
      <!-- Deployment animation overlay -->
      
      <!-- Floating notifications -->

      {#if deleteSuccess}
        <div
          class="animate-slideIn fixed top-5 right-5 z-50 max-w-md transform transition-all duration-300 ease-in-out"
        >
          <div
            class="relative flex overflow-hidden rounded-lg bg-white shadow-lg"
          >
            <button
              class="absolute top-1 right-1 text-gray-400 hover:text-gray-600"
              on:click={() => (deleteSuccess = '')}
              aria-label="Close notification"
            >
              <svg
                class="h-4 w-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
            <div
              class="flex w-12 flex-shrink-0 items-center justify-center bg-green-500"
            >
              <svg
                class="h-6 w-6 text-white"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                aria-hidden="true"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <div class="p-4">
              <div class="flex items-start">
                <div class="ml-1">
                  <h3 class="text-sm font-medium text-gray-900">
                    Delete Successful
                  </h3>
                  <div class="mt-1 text-sm text-gray-700">
                    <p>{deleteSuccess}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      {/if}

      {#if deploymentError}
        <div
          class="animate-slideIn fixed top-5 right-5 z-50 max-w-md transform transition-all duration-300 ease-in-out"
        >
          <div
            class="relative flex overflow-hidden rounded-lg bg-white shadow-lg"
          >
            <button
              class="absolute top-1 right-1 text-gray-400 hover:text-gray-600"
              on:click={() => (deploymentError = '')}
              aria-label="Close error notification"
            >
              <svg
                class="h-4 w-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
            <div
              class="flex w-12 flex-shrink-0 items-center justify-center bg-red-500"
            >
              <svg
                class="h-6 w-6 text-white"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                aria-hidden="true"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <div class="p-4">
              <div class="flex items-start">
                <div class="ml-1">
                  <h3 class="text-sm font-medium text-gray-900">
                    Deployment Failed
                  </h3>
                  <div class="mt-1 text-sm text-gray-700">
                    <p>{deploymentError}</p>
                  </div>
                  <p class="mt-2 text-xs text-gray-500">
                    Please try again later.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      {/if}
      
      {#if deleteError}
        <div
          class="animate-slideIn fixed top-5 right-5 z-50 max-w-md transform transition-all duration-300 ease-in-out"
        >
          <div
            class="relative flex overflow-hidden rounded-lg bg-white shadow-lg"
          >
            <button
              class="absolute top-1 right-1 text-gray-400 hover:text-gray-600"
              on:click={() => (deleteError = '')}
              aria-label="Close error notification"
            >
              <svg
                class="h-4 w-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
            <div
              class="flex w-12 flex-shrink-0 items-center justify-center bg-red-500"
            >
              <svg
                class="h-6 w-6 text-white"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                aria-hidden="true"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <div class="p-4">
              <div class="flex items-start">
                <div class="ml-1">
                  <h3 class="text-sm font-medium text-gray-900">
                    Delete Failed
                  </h3>
                  <div class="mt-1 text-sm text-gray-700">
                    <p>{deleteError}</p>
                  </div>
                  <p class="mt-2 text-xs text-gray-500">
                    Please try again later.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      {/if}

      {#if isLoading}
        <div class="p-20">
          <LoadingSpinner size="large" message="Loading blueprint details..." />
        </div>
      {:else if error}
        <div
          class="rounded border-l-4 border-red-500 bg-red-50 p-4 text-red-700 shadow-md"
        >
          <p class="mb-2 font-bold">Error</p>
          <p>{error}</p>
          <a
            href="/blueprints"
            class="mt-4 inline-block rounded bg-blue-500 px-4 py-2 text-white hover:bg-blue-600"
          >
            Back to Blueprints
          </a>
        </div>
      {:else if blueprint}
        <div class="mb-6">
          <a
            href="/blueprints"
            class="flex items-center text-blue-500 hover:text-blue-700"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="mr-1 h-5 w-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M10 19l-7-7m0 0l7-7m-7 7h18"
              />
            </svg>
            Back to Blueprints
          </a>
        </div>

        <!-- Blueprint details card -->
        <div class="mb-8 overflow-hidden rounded-lg bg-white shadow-md">
          <div class="bg-blue-600 p-4 text-white">
            <div class="flex items-center justify-between">
              <h1 class="text-2xl font-bold">{blueprint.name}</h1>
              <span class="rounded-full bg-blue-700 px-3 py-1 text-sm">
                {blueprint.provider || 'Unknown Provider'}
              </span>
            </div>
          </div>
          <div class="p-6">
            <div class="grid grid-cols-1 gap-6 md:grid-cols-2">
              <!-- Left column: Blueprint info -->
              <div>
                <h2 class="mb-4 text-lg font-semibold">Blueprint Details</h2>

                <div class="space-y-4">
                  {#if blueprint.description}
                    <div>
                      <h3 class="text-sm font-medium text-gray-500">
                        Description
                      </h3>
                      <p class="mt-1">{blueprint.description}</p>
                    </div>
                  {/if}

                  <div>
                    <h3 class="text-sm font-medium text-gray-500">Features</h3>
                    <div class="mt-1 flex space-x-2">
                      <span
                        class={`rounded px-2 py-1 text-xs ${blueprint.vnc ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-500'}`}
                      >
                        VNC {blueprint.vnc ? '✓' : '✗'}
                      </span>
                      <span
                        class={`rounded px-2 py-1 text-xs ${blueprint.vpn ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-500'}`}
                      >
                        VPN {blueprint.vpn ? '✓' : '✗'}
                      </span>
                    </div>
                  </div>

                  <div>
                    <h3 class="text-sm font-medium text-gray-500">
                      Blueprint ID
                    </h3>
                    <p class="mt-1 font-mono text-sm">
                      <span class="rounded bg-gray-100 p-1">{blueprint.id}</span>
                    </p>
                  </div>

                  <div class="mt-4 flex space-x-2">
                    <button
                      class="flex flex-1 items-center justify-center rounded bg-green-500 px-4 py-2 text-white hover:bg-green-600 {deployingBlueprint
                        ? 'cursor-not-allowed opacity-75'
                        : ''}"
                      on:click={() => deployBlueprint(blueprint.id)}
                      disabled={deployingBlueprint || deletingBlueprint}
                    >
                      {#if deployingBlueprint}
                        <LoadingSpinner size="sm" color="white" />
                      {:else}
                        Deploy Blueprint
                      {/if}
                    </button>
                    
                    <button
                      class="flex items-center justify-center rounded bg-red-500 px-4 py-2 text-white hover:bg-red-600 {deletingBlueprint
                        ? 'cursor-not-allowed opacity-75'
                        : ''}"
                      on:click={() => (showDeleteConfirm = true)}
                      disabled={deployingBlueprint || deletingBlueprint}
                    >
                      {#if deletingBlueprint}
                        <LoadingSpinner size="sm" color="white" />
                        Deleting...
                      {:else}
                        Delete Blueprint
                      {/if}
                    </button>
                  </div>

                  <!-- Hosts Summary Section -->
                  <div class="mt-6">
                    <h3 class="mb-2 text-sm font-medium text-gray-500">
                      Hosts Summary
                    </h3>

                    {#if blueprint.vpcs && blueprint.vpcs.length > 0}
                      {#each blueprint.vpcs as vpc}
                        {#if vpc.subnets && vpc.subnets.length > 0}
                          {#each vpc.subnets as subnet}
                            {#if subnet.hosts && subnet.hosts.length > 0}
                              <div class="mt-2 rounded bg-gray-50 p-3">
                                <p class="text-xs text-gray-500">
                                  {subnet.name || 'Unnamed Subnet'}
                                </p>
                                <div class="mt-1 space-y-2">
                                  {#each subnet.hosts as host}
                                    <!-- 
                                                                        Host information display
                                                                        Note: We will eventually allow specified private IPs for hosts
                                                                    -->
                                    <div
                                      class="flex items-center justify-between rounded border border-gray-200 bg-white p-2 text-sm"
                                    >
                                      <div>
                                        <span class="font-medium"
                                          >{host.hostname ||
                                            host.name ||
                                            'Unnamed host'}</span
                                        >
                                        {#if host.ip}
                                          <div
                                            class="mt-1 font-mono text-xs text-gray-500"
                                          >
                                            {host.ip}
                                          </div>
                                        {/if}
                                      </div>
                                      <span
                                        class="rounded-full bg-gray-100 px-2 py-1 text-xs"
                                      >
                                        {host.os || 'Unknown OS'} | {host.spec ||
                                          'Unknown spec'}
                                      </span>
                                    </div>
                                  {/each}
                                </div>
                              </div>
                            {/if}
                          {/each}
                        {/if}
                      {/each}
                    {:else if blueprint.vpc && blueprint.vpc.subnets && blueprint.vpc.subnets.length > 0}
                      {#each blueprint.vpc.subnets as subnet}
                        {#if subnet.hosts && subnet.hosts.length > 0}
                          <div class="mt-2 rounded bg-gray-50 p-3">
                            <p class="text-xs text-gray-500">
                              {subnet.name || 'Unnamed Subnet'}
                            </p>
                            <div class="mt-1 space-y-2">
                              {#each subnet.hosts as host}
                                <!-- Host information display -->
                                <div
                                  class="flex items-center justify-between rounded border border-gray-200 bg-white p-2 text-sm"
                                >
                                  <div>
                                    <span class="font-medium"
                                      >{host.hostname ||
                                        host.name ||
                                        'Unnamed host'}</span
                                    >
                                    {#if host.ip}
                                      <div
                                        class="mt-1 font-mono text-xs text-gray-500"
                                      >
                                        {host.ip}
                                      </div>
                                    {/if}
                                  </div>
                                  <span
                                    class="rounded-full bg-gray-100 px-2 py-1 text-xs"
                                  >
                                    {host.os || 'Unknown OS'} | {host.spec ||
                                      'Unknown spec'}
                                  </span>
                                </div>
                              {/each}
                            </div>
                          </div>
                        {/if}
                      {/each}
                    {:else}
                      <div
                        class="rounded bg-gray-50 p-3 text-sm text-gray-500 italic"
                      >
                        No hosts defined in this blueprint
                      </div>
                    {/if}
                  </div>
                </div>
              </div>

              <!-- Right column: Network visualization -->
              <div>
                <h2 class="mb-4 text-lg font-semibold">Network Diagram</h2>
                {#key blueprint?.id}
                  {#if blueprint}
                    <NetworkGraph blueprintData={blueprint} />
                  {:else}
                    <div class="rounded bg-gray-100 p-4">
                      Loading network data...
                    </div>
                  {/if}
                {/key}
              </div>
            </div>
          </div>
        </div>
      {:else}
        <div
          class="rounded border-l-4 border-amber-500 bg-amber-50 p-4 text-amber-700 shadow-md"
        >
          <p class="mb-2 font-bold">Blueprint Not Found</p>
          <p>Unable to find the requested blueprint.</p>
          <a
            href="/blueprints"
            class="mt-4 inline-block rounded bg-blue-500 px-4 py-2 text-white hover:bg-blue-600"
          >
            Back to Blueprints
          </a>
        </div>
      {/if}
      
      <!-- Delete confirmation modal -->
      {#if showDeleteConfirm && blueprint}
        <div class="fixed inset-0 z-50 flex items-center justify-center">
          <!-- Backdrop -->
          <div 
            class="absolute inset-0 bg-gray-800 bg-opacity-75 transition-opacity"
            on:click={() => !deletingBlueprint && (showDeleteConfirm = false)}
            on:keydown={(e) => e.key === 'Escape' && !deletingBlueprint && (showDeleteConfirm = false)}
            role="presentation"
          ></div>
          
          <!-- Modal dialog -->
          <div class="relative w-full max-w-md rounded-lg bg-white shadow-xl">
            <div class="p-6">
              <div class="mb-4 text-center">
                <svg 
                  class="mx-auto mb-4 h-12 w-12 text-red-500" 
                  xmlns="http://www.w3.org/2000/svg" 
                  fill="none" 
                  viewBox="0 0 24 24" 
                  stroke="currentColor"
                >
                  <path 
                    stroke-linecap="round" 
                    stroke-linejoin="round" 
                    stroke-width="2" 
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" 
                  />
                </svg>
                <h3 class="text-xl font-bold text-gray-900">
                  Delete Blueprint
                </h3>
                <p class="mt-2 text-gray-600">
                  Are you sure you want to delete <strong>{blueprint.name}</strong>? This action cannot be undone.
                </p>
              </div>
              
              <div class="mt-6 flex justify-end space-x-3">
                <button
                  class="rounded border border-gray-300 bg-white px-4 py-2 text-gray-700 hover:bg-gray-50"
                  on:click={() => (showDeleteConfirm = false)}
                  disabled={deletingBlueprint}
                >
                  Cancel
                </button>
                <button
                  class="rounded bg-red-500 px-4 py-2 text-white hover:bg-red-600 disabled:opacity-70"
                  on:click={() => deleteBlueprint(blueprint.id)}
                  disabled={deletingBlueprint}
                >
                  {#if deletingBlueprint}
                    <span class="flex items-center">
                      <LoadingSpinner size="sm" color="white" />
                      Deleting...
                    </span>
                  {:else}
                    Delete
                  {/if}
                </button>
              </div>
            </div>
          </div>
        </div>
      {/if}
    </div>
  </div>
</div>

<style>
  /* Animation for notifications */
  @keyframes slideIn {
    from {
      transform: translateX(100%);
      opacity: 0;
    }
    to {
      transform: translateX(0);
      opacity: 1;
    }
  }

  .animate-slideIn {
    animation: slideIn 0.3s ease-out forwards;
  }
</style>
