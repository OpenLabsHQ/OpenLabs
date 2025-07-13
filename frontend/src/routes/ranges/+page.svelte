<script lang="ts">
  import { onMount } from 'svelte'
  import { goto } from '$app/navigation'
  import RangeList from '$lib/components/RangeList.svelte'
  import Sidebar from '$lib/components/Sidebar.svelte'
  import AuthGuard from '$lib/components/AuthGuard.svelte'
  import { rangesApi } from '$lib/api'
  import { auth } from '$lib/stores/auth'
  import { formatErrorMessage } from '$lib/utils/error'
  import logger from '$lib/utils/logger'

  // Define the range interface to match the API response
  interface Range {
    id: string // Unique identifier for the range
    name: string // Name of the range
    description: string // Description of the range
    isRunning: boolean // Whether the range is currently active
    created_at?: string // Creation timestamp (optional)
    updated_at?: string // Last update timestamp (optional)
  }

  // Initialize with empty array, will be populated from API
  let deployedRanges: Range[] = []

  // Fallback ranges to show if API fails
  const fallbackRanges: Range[] = [
    {
      id: '1',
      name: 'NCAE Practice v1.0',
      description: 'Sample Linux Environment modeled after NCAE',
      isRunning: true,
    },
    {
      id: '2',
      name: 'NCCDC Lab',
      description: 'Lab with 10 Windows, 10 Linux, Kubernetes, and more!',
      isRunning: true,
    },
    {
      id: '3',
      name: 'GOAD',
      description: 'Game of active directory',
      isRunning: true,
    },
    {
      id: '4',
      name: 'C2 Practice',
      description:
        'Lab with Sliver, Havoc, Cobalt Strike, Metasploit, and Epire installed.',
      isRunning: true,
    },
    {
      id: '5',
      name: 'Linux basics',
      description: '40 Linux machines with randomized misconfigurations.',
      isRunning: true,
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

    // If authenticated, fetch ranges from the API
    try {
      isLoading = true
      const result = await rangesApi.getRanges()

      if (result.error) {
        // Set a user-friendly error message
        if (result.error.includes('not be found')) {
          // 404 error - show no ranges message instead of error
          deployedRanges = [] // Empty array to trigger the "No ranges found" UI
        } else {
          // Other errors - show in the UI with fallback data
          error = formatErrorMessage(result.error, 'Failed to load ranges')
          // Use fallback data for other errors
          deployedRanges = fallbackRanges
        }
      } else if (result.data && Array.isArray(result.data)) {
        // Map API response to our Range interface
        deployedRanges = result.data.map((range) => ({
          id: range.id || `range_${Math.random().toString(36).substr(2, 9)}`,
          name: range.name || 'Unnamed Range',
          description: range.description || 'No description',
          isRunning: true, // Always show as Started
          created_at: range.created_at,
          updated_at: range.updated_at,
        }))

        // If no ranges were returned, show empty state
        if (deployedRanges.length === 0) {
          logger.info('No ranges returned from API', 'ranges')
        }
      } else {
        logger.error('Invalid API response format', 'ranges', result.data)
        error = 'Invalid data received from server'
        // Use fallback data
        deployedRanges = fallbackRanges
      }
    } catch (err) {
      logger.error('Error fetching ranges', 'ranges', err)
      // Use fallback data on error
      deployedRanges = fallbackRanges
    } finally {
      isLoading = false
    }
  })
</script>

<svelte:head>
  <title>OpenLabs | Ranges</title>
</svelte:head>

<AuthGuard>
  <div class="font-roboto flex h-screen bg-gray-100">
    <!-- Fixed sidebar -->
    <div class="fixed inset-y-0 left-0 z-10 w-54">
      <Sidebar />
    </div>

    <!-- Main content with sidebar margin -->
    <div class="ml-54 flex-1">
      <RangeList {searchTerm} {deployedRanges} {isLoading} {error} />
    </div>
  </div>
</AuthGuard>

<style>
  @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap');
</style>
