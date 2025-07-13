<script lang="ts">
  import { onMount } from 'svelte'
  import { goto } from '$app/navigation'
  import { workspacesApi } from '$lib/api'
  import { auth } from '$lib/stores/auth'
  import { browser } from '$app/environment'
  import Sidebar from '$lib/components/Sidebar.svelte'
  import { LoadingSpinner, Button, PageHeader, StatusBadge, EmptyState } from '$lib/components'
  import type { Workspace } from '$lib/types/workspaces'
  import { formatErrorMessage } from '$lib/utils/error'

  // Workspaces state
  let workspaces: Workspace[] = []
  let isLoading = true
  let error = ''

  // Search functionality
  let searchTerm = ''

  onMount(async () => {
    if (browser) {
      // Check authentication
      if (!$auth.isAuthenticated) {
        goto('/login')
        return
      }

      // Load workspaces
      await loadWorkspaces()
    }
  })

  // Function to load workspaces
  async function loadWorkspaces() {
    try {
      isLoading = true
      error = ''

      const response = await workspacesApi.getWorkspaces()

      if (response.error) {
        error = formatErrorMessage(response.error, 'Failed to load workspaces')
        return
      }

      if (!response.data) {
        error = 'No workspace data received from API'
        return
      }

      workspaces = response.data
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to load workspaces'
    } finally {
      isLoading = false
    }
  }


  // Function to delete a workspace
  async function confirmDeleteWorkspace(workspace: Workspace) {
    // Simple confirmation for now - could be replaced with a modal
    if (confirm(`Are you sure you want to delete the workspace "${workspace.name}"? This action cannot be undone.`)) {
      try {
        const response = await workspacesApi.deleteWorkspace(workspace.id)
        
        if (response.error) {
          error = response.error
          return
        }
        
        // Reload workspaces
        await loadWorkspaces()
      } catch (err) {
        error = err instanceof Error ? err.message : 'Failed to delete workspace'
      }
    }
  }
</script>

<svelte:head>
  <title>OpenLabs | Workspaces</title>
</svelte:head>

<div class="font-roboto flex h-screen bg-gray-100">
  <!-- Fixed sidebar -->
  <div class="fixed inset-y-0 left-0 z-10 w-54">
    <Sidebar />
  </div>

  <!-- Main content with sidebar margin -->
  <div class="ml-54 flex-1 overflow-y-auto">
    <div class="flex flex-1 flex-wrap content-start">
      <PageHeader 
        title="Workspaces"
        searchPlaceholder="Search Workspaces"
        bind:searchValue={searchTerm}
      >
        <svelte:fragment slot="actions">
          <Button href="/workspaces/create" variant="primary" class="w-full sm:w-auto whitespace-nowrap">
            Create Workspace
          </Button>
        </svelte:fragment>
      </PageHeader>
      
      <div class="w-full p-4">


      <!-- Error Message -->
      {#if error}
        <div class="mb-4 rounded-md bg-red-50 p-4 text-red-700">
          <p>{error}</p>
        </div>
      {/if}

      <!-- Loading Spinner -->
      {#if isLoading}
        <div class="flex justify-center p-12">
          <LoadingSpinner size="lg" message="Loading workspaces..." />
        </div>
      <!-- Workspaces List -->
      {:else if workspaces.length > 0}
        <div class="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
          {#each workspaces.filter(workspace => 
            workspace.name.toLowerCase().includes(searchTerm.toLowerCase()) || 
            workspace.description.toLowerCase().includes(searchTerm.toLowerCase())
          ) as workspace}
            <div class="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm transition-all duration-200 hover:shadow-md">
              <div class="border-b border-gray-200 bg-gray-50 p-4">
                <div class="flex items-center justify-between">
                  <h3 class="text-lg font-medium text-gray-900">
                    {workspace.name}
                  </h3>
                  <StatusBadge 
                    variant={workspace.is_admin ? 'primary' : 'gray'}
                    size="sm"
                  >
                    {workspace.is_admin ? 'Admin' : 'Member'}
                  </StatusBadge>
                </div>
              </div>
              
              <div class="p-4">
                {#if workspace.description}
                  <p class="mb-4 text-sm text-gray-600">{workspace.description}</p>
                {:else}
                  <p class="mb-4 text-sm italic text-gray-400">No description</p>
                {/if}
                
                {#if workspace.default_time_limit}
                  <div class="mb-4 flex items-center text-sm text-gray-500">
                    <svg xmlns="http://www.w3.org/2000/svg" class="mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    Default time limit: {workspace.default_time_limit} minutes
                  </div>
                {/if}
                
                <div class="flex border-t border-gray-100 pt-4">
                  <Button 
                    href={`/workspaces/${workspace.id}`}
                    variant="primary"
                    size="sm"
                    fullWidth
                  >
                    View Details
                  </Button>
                  
                  {#if workspace.is_admin}
                    <Button 
                      variant="danger"
                      size="sm"
                      class="ml-2"
                      on:click={() => confirmDeleteWorkspace(workspace)}
                    >
                      Delete
                    </Button>
                  {/if}
                </div>
              </div>
            </div>
          {/each}
        </div>
      {:else}
        <EmptyState
          title="No workspaces found"
          description="You don't have any workspaces yet. Create your first workspace to collaborate with others!"
          iconType="workspace"
          actionLabel="Create your first workspace"
          on:action={() => window.location.href = '/workspaces/create'}
        />
      {/if}
      </div>
    </div>
  </div>
</div>
