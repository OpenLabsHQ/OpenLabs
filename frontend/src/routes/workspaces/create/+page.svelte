<style>
  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
  }
  
  .animate-fadeIn {
    animation: fadeIn 0.3s ease-out forwards;
  }
</style>

<script lang="ts">
  import { onMount } from 'svelte'
  import { goto } from '$app/navigation'
  import { workspacesApi } from '$lib/api'
  import { auth } from '$lib/stores/auth'
  import { browser } from '$app/environment'
  import Sidebar from '$lib/components/Sidebar.svelte'

  // Form state
  let name = ''
  let description = ''
  let defaultTimeLimit: number | undefined = undefined
  let isCreating = false
  let createError = ''

  onMount(async () => {
    if (browser) {
      // Check authentication
      if (!$auth.isAuthenticated) {
        goto('/login')
        return
      }
    }
  })

  // Function to create a new workspace
  async function createWorkspace() {
    if (!name.trim()) {
      createError = 'Workspace name is required'
      return
    }

    try {
      isCreating = true
      createError = ''

      const workspaceData = {
        name: name.trim(),
        description: description.trim(),
        ...(defaultTimeLimit && { default_time_limit: defaultTimeLimit })
      }

      const response = await workspacesApi.createWorkspace(workspaceData)

      if (response.error) {
        createError = response.error
        return
      }

      // Redirect to the new workspace
      if (response.data?.id) {
        goto(`/workspaces/${response.data.id}`)
      } else {
        // Fall back to workspaces list
        goto('/workspaces')
      }
    } catch (err) {
      createError = err instanceof Error ? err.message : 'Failed to create workspace'
    } finally {
      isCreating = false
    }
  }
</script>

<svelte:head>
  <title>OpenLabs | Create Workspace</title>
</svelte:head>

<div class="font-roboto flex h-screen bg-gray-100">
  <!-- Fixed sidebar -->
  <div class="fixed inset-y-0 left-0 z-10 w-54">
    <Sidebar />
  </div>

  <!-- Main content with sidebar margin -->
  <div class="ml-54 flex-1 overflow-y-auto">
    <!-- Top navigation bar -->
    <div class="flex h-15 w-full items-center justify-between border-b border-gray-300 bg-gray-100 p-4">
      <a
        href="/workspaces"
        class="flex items-center text-blue-600 hover:text-blue-800 transition-colors"
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
        Back to Workspaces
      </a>
      <h1 class="text-xl font-semibold text-gray-800">Create New Workspace</h1>
      <div class="w-24"><!-- Empty space to balance the header --></div>
    </div>

    <div class="p-6">
      {#if createError}
        <div class="mb-6 rounded-lg overflow-hidden shadow-sm animate-fadeIn">
          <div class="bg-red-600 px-4 py-2 flex items-center">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2 text-white" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
            </svg>
            <h3 class="text-sm font-medium text-white">Error Creating Workspace</h3>
          </div>
          <div class="bg-red-50 px-4 py-3 border-t border-red-200">
            <p class="text-sm text-red-800">{createError}</p>
          </div>
        </div>
      {/if}

      <!-- Create Workspace Form -->
      <div class="mx-auto max-w-3xl animate-fadeIn">
        <div class="overflow-hidden rounded-lg bg-white shadow mb-6 transition-all duration-300 hover:shadow-md">
          <div class="bg-gradient-to-r from-blue-600 to-blue-700 p-4 text-white">
            <h2 class="text-lg font-semibold">Workspace Information</h2>
            <p class="text-sm text-blue-100">Create a collaborative space for users to share resources</p>
          </div>
          
          <div class="p-5">
            <div class="space-y-5">
              <div>
                <label for="name" class="mb-2 block text-sm font-medium text-gray-700">
                  Workspace Name <span class="text-red-500">*</span>
                </label>
                <div class="relative">
                  <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-gray-400" viewBox="0 0 20 20" fill="currentColor">
                      <path d="M13 6a3 3 0 11-6 0 3 3 0 016 0zM18 8a2 2 0 11-4 0 2 2 0 014 0zM14 15a4 4 0 00-8 0v3h8v-3zM6 8a2 2 0 11-4 0 2 2 0 014 0zM16 18v-3a5.972 5.972 0 00-.75-2.906A3.005 3.005 0 0119 15v3h-3zM4.75 12.094A5.973 5.973 0 004 15v3H1v-3a3 3 0 013.75-2.906z" />
                    </svg>
                  </div>
                  <input
                    type="text"
                    id="name"
                    class="block w-full rounded-md border border-gray-300 pl-10 py-2.5 text-gray-700 bg-white bg-opacity-80 shadow-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-200 focus:bg-white transition duration-150 ease-in-out"
                    placeholder="Enter a descriptive name (e.g., Blue Team, Pentesting Class)"
                    bind:value={name}
                    required
                  />
                </div>
                <p class="mt-1.5 text-xs text-gray-500">
                  Choose a clear, descriptive name for your workspace
                </p>
              </div>
              
              <div>
                <label for="description" class="mb-2 block text-sm font-medium text-gray-700">
                  Description
                </label>
                <div class="relative">
                  <div class="absolute top-3 left-3 pointer-events-none">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-gray-400" viewBox="0 0 20 20" fill="currentColor">
                      <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" />
                    </svg>
                  </div>
                  <textarea
                    id="description"
                    rows="4"
                    class="block w-full rounded-md border border-gray-300 pl-10 py-2.5 text-gray-700 bg-white bg-opacity-80 shadow-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-200 focus:bg-white transition duration-150 ease-in-out resize-none"
                    placeholder="Describe the purpose of this workspace and what resources will be shared"
                    bind:value={description}
                  ></textarea>
                </div>
                <p class="mt-1.5 text-xs text-gray-500">
                  Add details about what this workspace will be used for
                </p>
              </div>
              
              <div>
                <label for="timeLimit" class="mb-2 block text-sm font-medium text-gray-700">
                  Default Time Limit (minutes)
                </label>
                <div class="relative w-1/3">
                  <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <input
                    type="number"
                    id="timeLimit"
                    class="block w-full rounded-md border border-gray-300 pl-10 py-2.5 text-gray-700 bg-white bg-opacity-80 shadow-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-200 focus:bg-white transition duration-150 ease-in-out"
                    placeholder="No limit"
                    bind:value={defaultTimeLimit}
                    min="1"
                  />
                </div>
                <p class="mt-1.5 text-xs text-gray-500">
                  Set a default time limit for workspace resources (leave empty for no limit)
                </p>
              </div>
            </div>
          </div>
        </div>
        
        <!-- Information card -->
        <div class="bg-blue-50 rounded-lg border border-blue-200 p-4 mb-6">
          <div class="flex">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2 text-blue-500" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" />
            </svg>
            <div>
              <h3 class="text-sm font-medium text-blue-800">About Workspaces</h3>
              <p class="mt-1 text-sm text-blue-600">
                Workspaces allow you to collaborate with team members and share blueprints.
                After creating a workspace, you can add users and start sharing resources.
              </p>
            </div>
          </div>
        </div>
        
        <!-- Action Buttons -->
        <div class="flex justify-end space-x-4">
          <a
            href="/workspaces"
            class="flex items-center justify-center rounded-md border border-gray-300 bg-white px-5 py-2.5 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 hover:border-gray-400 focus:ring-2 focus:ring-gray-200 transition-all duration-200"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-1 text-gray-500" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
            </svg>
            Cancel
          </a>
          <button
            type="button"
            class="flex items-center justify-center rounded-md bg-gradient-to-r from-blue-600 to-blue-700 px-6 py-2.5 text-sm font-medium text-white shadow-sm hover:from-blue-700 hover:to-blue-800 focus:ring-2 focus:ring-blue-300 focus:outline-none transition-all duration-200 {isCreating ? 'cursor-not-allowed opacity-70' : ''}"
            on:click={createWorkspace}
            disabled={isCreating}
          >
            {#if isCreating}
              <svg
                class="mr-2 h-4 w-4 animate-spin text-white"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  class="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  stroke-width="4"
                ></circle>
                <path
                  class="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                ></path>
              </svg>
              Creating...
            {:else}
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-1" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clip-rule="evenodd" />
              </svg>
              Create Workspace
            {/if}
          </button>
        </div>
      </div>
    </div>
  </div>
</div>
