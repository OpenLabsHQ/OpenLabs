<script lang="ts">
  import { onMount } from 'svelte'
  import { goto } from '$app/navigation'
  import BlueprintList from '$lib/components/BlueprintList.svelte'
  import Sidebar from '$lib/components/Sidebar.svelte'
  import { rangesApi } from '$lib/api'
  import { auth } from '$lib/stores/auth'
  import logger from '$lib/utils/logger'

  // Define the blueprint interface to match the API response
  interface Blueprint {
    id: string
    provider: string
    name: string
    vnc: boolean
    vpn: boolean
    description?: string
  }

  // Initialize with empty array, will be populated from API
  let blueprints: Blueprint[] = []

  // Fallback blueprints to show if API fails
  const fallbackBlueprints: Blueprint[] = [
    {
      id: '1',
      provider: 'aws',
      name: 'aws-basic-linux',
      vnc: true,
      vpn: false,
    },
    {
      id: '2',
      provider: 'azure',
      name: 'azure-windows-ad',
      vnc: true,
      vpn: true,
    },
    {
      id: '3',
      provider: 'aws',
      name: 'aws-security-lab',
      vnc: false,
      vpn: true,
    },
    {
      id: '4',
      provider: 'gcp',
      name: 'gcp-kubernetes-cluster',
      vnc: false,
      vpn: false,
    },
    {
      id: '5',
      provider: 'vsphere',
      name: 'vsphere-network-security',
      vnc: true,
      vpn: true,
    },
  ]

  let searchTerm = ''
  let isLoading = false
  let error = ''

  // First check if authenticated, otherwise redirect to login
  onMount(async () => {
    // Check authentication
    if (!$auth.isAuthenticated) {
      goto('/login')
      return
    }

    // If authenticated, fetch blueprints from the API
    try {
      isLoading = true
      const result = await rangesApi.getBlueprints()

      if (result.error) {
        // Set a user-friendly error message
        if (result.error.includes('not be found')) {
          // 404 error - show no blueprints message instead of error
          blueprints = [] // Empty array to trigger the "No blueprints found" UI
        } else {
          // Other errors - show in the UI with fallback data
          error = result.error
          // Use fallback data for other errors
          blueprints = fallbackBlueprints
        }
      } else if (result.data && Array.isArray(result.data)) {
        // Map API response to our Blueprint interface
        blueprints = result.data.map((blueprint) => ({
          id:
            blueprint.id ||
            `blueprint_${Math.random().toString(36).substr(2, 9)}`,
          provider: blueprint.provider || 'default',
          name: blueprint.name || 'Unnamed Blueprint',
          vnc: blueprint.vnc || false,
          vpn: blueprint.vpn || false,
          description: blueprint.description,
        }))

        // If no blueprints were returned, show empty state
        if (blueprints.length === 0) {
          logger.info('No blueprints returned from API', 'blueprints')
        }
      } else {
        error = 'Invalid data received from server'
        // Use fallback data
        blueprints = fallbackBlueprints
      }
    } catch {
      // Use fallback data on error
      blueprints = fallbackBlueprints
    } finally {
      isLoading = false
    }
  })
</script>

<svelte:head>
  <title>OpenLabs | Blueprints</title>
</svelte:head>

<div class="font-roboto flex h-screen bg-gray-100">
  <!-- Fixed sidebar -->
  <div class="fixed inset-y-0 left-0 z-10 w-54">
    <Sidebar />
  </div>

  <!-- Main content with sidebar margin -->
  <div class="ml-54 flex-1">
    <BlueprintList searchTerm={searchTerm} blueprints={blueprints} isLoading={isLoading} error={error} />
  </div>
</div>

<style>
  @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap');
</style>
