<style>
  @keyframes slideIn {
    from { transform: translateX(20px); opacity: 0; }
    to { transform: translateX(0); opacity: 1; }
  }
  
  .animate-slideIn {
    animation: slideIn 0.3s ease-out forwards;
  }
  
  /* Markdown styling */
  .markdown-content :global(h1) {
    font-size: 1.5rem;
    font-weight: 700;
    margin-top: 1rem;
    margin-bottom: 0.5rem;
  }
  
  .markdown-content :global(h2) {
    font-size: 1.25rem;
    font-weight: 600;
    margin-top: 1rem;
    margin-bottom: 0.5rem;
  }
  
  .markdown-content :global(h3) {
    font-size: 1.125rem;
    font-weight: 600;
    margin-top: 0.75rem;
    margin-bottom: 0.5rem;
  }
  
  .markdown-content :global(p) {
    margin-bottom: 0.75rem;
  }
  
  .markdown-content :global(ul), 
  .markdown-content :global(ol) {
    margin-left: 1.5rem;
    margin-bottom: 0.75rem;
  }
  
  .markdown-content :global(ul) {
    list-style-type: disc;
  }
  
  .markdown-content :global(ol) {
    list-style-type: decimal;
  }
  
  .markdown-content :global(li) {
    margin-bottom: 0.25rem;
  }
  
  .markdown-content :global(code) {
    background-color: rgba(0, 0, 0, 0.05);
    padding: 0.125rem 0.25rem;
    border-radius: 0.25rem;
    font-family: monospace;
  }
  
  .markdown-content :global(pre) {
    background-color: rgba(0, 0, 0, 0.05);
    padding: 0.75rem;
    border-radius: 0.25rem;
    overflow-x: auto;
    margin-bottom: 0.75rem;
  }
  
  .markdown-content :global(a) {
    color: #3182ce;
    text-decoration: underline;
  }
  
  .markdown-content :global(a:hover) {
    color: #2c5282;
  }
  
  .markdown-content :global(blockquote) {
    border-left: 4px solid #e2e8f0;
    padding-left: 1rem;
    font-style: italic;
    margin-bottom: 0.75rem;
  }
  
  .markdown-content :global(hr) {
    border: 0;
    border-top: 1px solid #e2e8f0;
    margin: 1rem 0;
  }
</style>

<script lang="ts">
  import { onMount, onDestroy } from 'svelte'
  import { goto } from '$app/navigation'
  import { rangesApi } from '$lib/api'
  import NetworkGraph from '$lib/components/NetworkGraph.svelte'
  import Sidebar from '$lib/components/Sidebar.svelte'
  import LoadingSpinner from '$lib/components/LoadingSpinner.svelte'
  import { auth } from '$lib/stores/auth'
  import { browser } from '$app/environment'
  import { marked } from 'marked'
  import { formatErrorMessage } from '$lib/utils/error'
  import logger from '$lib/utils/logger'

  // Get range ID from page data
  export let data
  const rangeId = data.rangeId

  // Range data
  let rangeData: any = null
  let networkData: any = null
  let sshKey: string = ''
  let isLoading = true
  let error = ''
  let activeTab = 'overview'
  let showSSHKey = false
  let copiedSSH = false
  
  // Range status polling
  let pollingInterval: ReturnType<typeof setInterval> | null = null
  let isPollingEnabled = false
  
  // Placeholder README if none exists
  let readmeHtml = ''
  const placeholderReadme = `# Range Usage Guide
  
## Getting Started

This range has been provisioned for you to use. Follow these steps to get started:

1. Connect to the range using SSH
2. Access resources through the jumpbox
3. Follow security best practices

## Network Layout

The range consists of:
- A jumpbox for access
- Subnets as shown in the network diagram
- Virtual machines with various configurations

## Support

If you encounter any issues, please contact support.`

  // Delete confirmation state
  let showDeleteConfirm = false
  let isDeletingRange = false

  // Notification state
  let successMessage = ''
  let errorMessage = ''
  let autoCloseTimer: ReturnType<typeof setTimeout> | null = null

  // Clean up timers when component is destroyed
  onDestroy(() => {
    if (autoCloseTimer) {
      clearTimeout(autoCloseTimer)
    }
    if (pollingInterval) {
      clearInterval(pollingInterval)
    }
  })

  // Set auto-dismiss for notifications
  function setAutoDismiss(type: 'success' | 'error', duration: number = 3000) {
    // Clear any existing timers
    if (autoCloseTimer) {
      clearTimeout(autoCloseTimer)
    }

    // Set a new timer
    autoCloseTimer = setTimeout(() => {
      if (type === 'success') {
        successMessage = ''
      } else {
        errorMessage = ''
      }
      autoCloseTimer = null
    }, duration)
  }

  // Start polling for range status updates
  function startPolling() {
    if (pollingInterval || !isPollingEnabled) return

    pollingInterval = setInterval(async () => {
      try {
        const rangeResult = await rangesApi.getRangeById(rangeId)
        if (rangeResult.error) {
          logger.error('Polling error', 'ranges.detail', rangeResult.error)
          return
        }
        
        const updatedRange = rangeResult.data
        
        // Check if range state has changed from deploying to deployed
        if (rangeData?.state === 'starting' && updatedRange.state === 'on') {
          // Range is now fully deployed, reload the page data
          loadRangeData()
          stopPolling()
        } else if (updatedRange.state !== rangeData?.state) {
          // State changed, update the range data
          rangeData = updatedRange
        }
      } catch (err) {
        logger.error('Error during polling', 'ranges.detail', err)
      }
    }, 30000) // Poll every 30 seconds
  }

  // Stop polling for range status updates
  function stopPolling() {
    if (pollingInterval) {
      clearInterval(pollingInterval)
      pollingInterval = null
    }
    isPollingEnabled = false
  }

  // Load range data
  async function loadRangeData() {
    if (browser) {
      // Check authentication
      if (!$auth.isAuthenticated) {
        goto('/login')
        return
      }

      try {
        isLoading = true
        error = ''

        // Load range details
        const rangeResult = await rangesApi.getRangeById(rangeId)
        if (rangeResult.error) {
          error = rangeResult.error
          return
        }
        
        // Process range data
        rangeData = rangeResult.data
        
        // Extract jumpbox IP from state_file outputs if available
        if (rangeData.state_file && rangeData.state_file.outputs) {
          const outputs = rangeData.state_file.outputs;
          
          // Find the jumpbox public IP in the outputs
          for (const key in outputs) {
            if (key.includes('JumpboxPublicIp') && outputs[key].value) {
              rangeData.jumpbox_ip = outputs[key].value;
              break;
            }
          }
          
          // Set private key if available
          if (rangeData.range_private_key) {
            sshKey = rangeData.range_private_key;
          } else {
            // Look for private key in outputs
            for (const key in outputs) {
              if (key.includes('private-key') && outputs[key].value) {
                sshKey = outputs[key].value;
                break;
              }
            }
          }
        }
        
        // Set isRunning based on range state
        rangeData.isRunning = rangeData.state === 'on' || rangeData.state === 'starting';
        
        // Check if range is still deploying and enable polling
        if (rangeData.state === 'starting') {
          isPollingEnabled = true
          startPolling()
        } else {
          stopPolling()
        }
        
        // Process readme (if exists)
        if (rangeData.readme) {
          readmeHtml = marked(rangeData.readme)
        } else {
          // Use placeholder readme
          readmeHtml = marked(placeholderReadme)
        }
        
        // Use the range data directly for network graph
        networkData = rangeData;
      } catch (err) {
        logger.error('Error loading range', 'ranges.detail', err)
        error = err instanceof Error ? err.message : 'Failed to load range data'
      } finally {
        isLoading = false
      }
    }
  }

  // Initial data load
  onMount(() => {
    loadRangeData()
  })

  // Get SSH key for the range
  async function loadSSHKey() {
    try {
      const result = await rangesApi.getRangeSSHKey(rangeId)
      if (result.error) {
        errorMessage = `Failed to load SSH key: ${formatErrorMessage(result.error, 'Unknown error')}`
        setAutoDismiss('error', 5000)
        return
      }
      
      sshKey = result.data.range_private_key || ''
      showSSHKey = true
    } catch (err) {
      logger.error('Error loading SSH key', 'ranges.detail', err)
      errorMessage = err instanceof Error ? err.message : 'Failed to load SSH key'
      setAutoDismiss('error', 5000)
    }
  }

  // Copy SSH key to clipboard
  function copySSHKey() {
    if (!sshKey) return
    
    navigator.clipboard.writeText(sshKey)
      .then(() => {
        copiedSSH = true
        setTimeout(() => {
          copiedSSH = false
        }, 2000)
      })
      .catch(err => {
        logger.error('Failed to copy SSH key', 'ranges.detail', err)
      })
  }
  
  // Copy IP address to clipboard
  function copyIPAddress(ip: string, hostName: string) {
    if (!ip) return
    
    navigator.clipboard.writeText(ip)
      .then(() => {
        copiedIP = true
        copiedIPAddress = ip
        successMessage = `Copied IP address ${ip} for ${hostName} to clipboard`
        setAutoDismiss('success', 2000)
        
        setTimeout(() => {
          copiedIP = false
          copiedIPAddress = ''
        }, 2000)
      })
      .catch(err => {
        logger.error('Failed to copy IP address', 'ranges.detail', err)
        errorMessage = 'Failed to copy IP address to clipboard'
        setAutoDismiss('error', 3000)
      })
  }
  
  // Handle keyboard events for accessibility
  function handleKeyDown(event: KeyboardEvent, ip: string, hostName: string) {
    // Only respond to Enter or Space key presses
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault(); // Prevent default behavior (like scrolling on Space)
      copyIPAddress(ip, hostName);
    }
  }
  
  // Handle keyboard navigation for tabs
  function handleTabKeyDown(event: KeyboardEvent) {
    const tabs = ['overview', 'network', 'access', 'readme'];
    const currentIndex = tabs.indexOf(activeTab);
    
    if (event.key === 'ArrowRight' || event.key === 'ArrowDown') {
      event.preventDefault();
      const nextIndex = (currentIndex + 1) % tabs.length;
      activeTab = tabs[nextIndex];
      document.getElementById(`tab-${activeTab}`)?.focus();
    } else if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') {
      event.preventDefault();
      const prevIndex = (currentIndex - 1 + tabs.length) % tabs.length;
      activeTab = tabs[prevIndex];
      document.getElementById(`tab-${activeTab}`)?.focus();
    } else if (event.key === 'Home') {
      event.preventDefault();
      activeTab = tabs[0];
      document.getElementById(`tab-${activeTab}`)?.focus();
    } else if (event.key === 'End') {
      event.preventDefault();
      activeTab = tabs[tabs.length - 1];
      document.getElementById(`tab-${activeTab}`)?.focus();
    }
  }
  
  // Download SSH key as PEM file
  function downloadSSHKey() {
    if (!sshKey) return
    
    // Create safe filename from range name
    const safeName = (rangeData.name || 'range')
      .toLowerCase()
      .replace(/[^a-z0-9]/g, '-')
      .replace(/-+/g, '-')
      .replace(/^-|-$/g, '');
    
    const filename = `${safeName}.pem`;
    
    // Create a blob from the SSH key
    const blob = new Blob([sshKey], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    
    // Create a temporary anchor element to trigger the download
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    
    // Clean up
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  // Delete range
  async function deleteRange() {
    try {
      isDeletingRange = true
      errorMessage = ''
      
      const result = await rangesApi.deleteRange(rangeId)
      
      if (result.error) {
        errorMessage = formatErrorMessage(result.error, 'Failed to delete range')
        setAutoDismiss('error', 5000)
        return
      }
      
      // Deletion job submitted successfully
      const jobResponse = result.data
      if (jobResponse && jobResponse.arq_job_id) {
        // Redirect to destruction progress page with job ID
        goto(`/ranges/destroying/${jobResponse.arq_job_id}`)
      } else {
        // Fallback for immediate deletion response
        successMessage = `Successfully deleted range "${rangeData.name}"`
        setAutoDismiss('success', 3000)
        
        setTimeout(() => {
          goto('/ranges')
        }, 1500)
      }
    } catch (err) {
      logger.error('Error deleting range', 'ranges.detail', err)
      errorMessage = err instanceof Error ? err.message : 'Failed to delete range'
      setAutoDismiss('error', 5000)
    } finally {
      isDeletingRange = false
      showDeleteConfirm = false
    }
  }
</script>

<svelte:head>
  <title>OpenLabs | Range Details</title>
</svelte:head>

<div class="font-roboto flex h-screen bg-gray-100">
  <!-- Fixed sidebar -->
  <div class="fixed inset-y-0 left-0 z-10 w-54">
    <Sidebar />
  </div>

  <!-- Main content with sidebar margin -->
  <div class="ml-54 flex-1 overflow-y-auto">
    <div class="p-6">
      <!-- Floating success notification -->
      {#if successMessage}
        <div class="animate-slideIn fixed top-5 right-5 z-50 max-w-md transform transition-all duration-300 ease-in-out" 
          role="alert"
          aria-live="polite">
          <div class="relative flex overflow-hidden rounded-lg bg-white shadow-lg">
            <button
              class="absolute top-1 right-1 text-gray-400 hover:text-gray-600 focus:outline-none focus:ring-2 focus:ring-green-300 rounded-full"
              on:click={() => (successMessage = '')}
              on:keydown={(e) => e.key === 'Escape' && (successMessage = '')}
              aria-label="Close success notification"
            >
              <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
            <div class="flex w-12 flex-shrink-0 items-center justify-center bg-green-500">
              <svg
                class="h-6 w-6 text-white"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                aria-hidden="true"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div class="p-4">
              <div class="flex items-start">
                <div class="ml-1">
                  <h3 class="text-sm font-medium text-gray-900">Success</h3>
                  <div class="mt-1 text-sm text-gray-700">
                    <p>{successMessage}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      {/if}

      <!-- Floating error notification -->
      {#if errorMessage}
        <div class="animate-slideIn fixed top-5 right-5 z-50 max-w-md transform transition-all duration-300 ease-in-out"
          role="alert"
          aria-live="assertive">
          <div class="relative flex overflow-hidden rounded-lg bg-white shadow-lg">
            <button
              class="absolute top-1 right-1 text-gray-400 hover:text-gray-600 focus:outline-none focus:ring-2 focus:ring-red-300 rounded-full"
              on:click={() => (errorMessage = '')}
              on:keydown={(e) => e.key === 'Escape' && (errorMessage = '')}
              aria-label="Close error notification"
            >
              <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
            <div class="flex w-12 flex-shrink-0 items-center justify-center bg-red-500">
              <svg
                class="h-6 w-6 text-white"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                aria-hidden="true"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div class="p-4">
              <div class="flex items-start">
                <div class="ml-1">
                  <h3 class="text-sm font-medium text-gray-900">Error</h3>
                  <div class="mt-1 text-sm text-gray-700">
                    <p>{errorMessage}</p>
                  </div>
                  <p class="mt-2 text-xs text-gray-500">Please try again later.</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      {/if}

      {#if isLoading}
        <div class="p-20">
          <LoadingSpinner size="large" message="Loading range details..." />
        </div>
      {:else if error}
        <div class="rounded border-l-4 border-red-500 bg-red-50 p-4 text-red-700 shadow-md">
          <p class="mb-2 font-bold">Error</p>
          <p>{error}</p>
          <a
            href="/ranges"
            class="mt-4 inline-block rounded bg-blue-500 px-4 py-2 text-white hover:bg-blue-600"
          >
            Back to Ranges
          </a>
        </div>
      {:else if rangeData}
        <div class="mb-6">
          <a
            href="/ranges"
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
            Back to Ranges
          </a>
        </div>

        <!-- Range details card -->
        <div class="mb-8 overflow-hidden rounded-lg bg-white shadow-md">
          <div class="bg-blue-600 p-4 text-white">
            <div class="flex items-center justify-between">
              <h1 class="text-2xl font-bold">{rangeData.name || 'Unnamed Range'}</h1>
              <span class="rounded-full px-3 py-1 text-sm {
                rangeData.state === 'starting' ? 'bg-yellow-600' :
                rangeData.state === 'on' ? 'bg-green-600' :
                rangeData.state === 'stopping' ? 'bg-orange-600' :
                rangeData.state === 'off' ? 'bg-gray-600' :
                'bg-blue-700'
              }">
                {#if rangeData.state === 'starting'}
                  <span class="flex items-center">
                    <svg class="mr-1 h-3 w-3 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Deploying
                  </span>
                {:else if rangeData.state === 'on'}
                  Started
                {:else if rangeData.state === 'stopping'}
                  Stopping
                {:else if rangeData.state === 'off'}
                  Stopped
                {:else}
                  {rangeData.state || 'Unknown'}
                {/if}
              </span>
            </div>
            {#if rangeData.description}
              <p class="mt-1 text-sm opacity-90">{rangeData.description}</p>
            {/if}
          </div>

          <!-- Tab navigation -->
          <div class="border-b border-gray-200 bg-gray-50">
            <div class="-mb-px flex space-x-8 px-6" role="tablist" aria-label="Range details tabs">
              <button
                class="whitespace-nowrap border-b-2 py-4 px-1 text-sm font-medium {activeTab === 'overview' ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'} focus:outline-none focus:ring-2 focus:ring-blue-300 focus:ring-offset-2"
                on:click={() => (activeTab = 'overview')}
                on:keydown={handleTabKeyDown}
                aria-selected={activeTab === 'overview'}
                role="tab"
                id="tab-overview"
                aria-controls="panel-overview"
                tabindex={activeTab === 'overview' ? 0 : -1}
              >
                Overview
              </button>
              <button
                class="whitespace-nowrap border-b-2 py-4 px-1 text-sm font-medium {activeTab === 'network' ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'} focus:outline-none focus:ring-2 focus:ring-blue-300 focus:ring-offset-2"
                on:click={() => (activeTab = 'network')}
                on:keydown={handleTabKeyDown}
                aria-selected={activeTab === 'network'}
                role="tab"
                id="tab-network"
                aria-controls="panel-network"
                tabindex={activeTab === 'network' ? 0 : -1}
              >
                Network Graph
              </button>
              <button
                class="whitespace-nowrap border-b-2 py-4 px-1 text-sm font-medium {activeTab === 'access' ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'} focus:outline-none focus:ring-2 focus:ring-blue-300 focus:ring-offset-2"
                on:click={() => (activeTab = 'access')}
                on:keydown={handleTabKeyDown}
                aria-selected={activeTab === 'access'}
                role="tab"
                id="tab-access"
                aria-controls="panel-access"
                tabindex={activeTab === 'access' ? 0 : -1}
              >
                Access Information
              </button>
              <button
                class="whitespace-nowrap border-b-2 py-4 px-1 text-sm font-medium {activeTab === 'readme' ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'} focus:outline-none focus:ring-2 focus:ring-blue-300 focus:ring-offset-2"
                on:click={() => (activeTab = 'readme')}
                on:keydown={handleTabKeyDown}
                aria-selected={activeTab === 'readme'}
                role="tab"
                id="tab-readme"
                aria-controls="panel-readme"
                tabindex={activeTab === 'readme' ? 0 : -1}
              >
                Read Me
              </button>
            </div>
          </div>

          <!-- Tab content -->
          <div class="p-6">
            {#if activeTab === 'overview'}
              <div 
                class="grid grid-cols-1 gap-6 md:grid-cols-2"
                role="tabpanel"
                id="panel-overview"
                aria-labelledby="tab-overview"
                tabindex="0"
              >
                <!-- Left column: Range info -->
                <div>
                  <h2 class="mb-4 text-lg font-semibold">Range Details</h2>
                  <div class="space-y-4">
                    <div>
                      <h3 class="text-sm font-medium text-gray-500">Range ID</h3>
                      <p class="mt-1 font-mono text-sm">
                        <span class="rounded bg-gray-100 p-1">{rangeData.id}</span>
                      </p>
                    </div>
                    
                    <div>
                      <h3 class="text-sm font-medium text-gray-500">Status</h3>
                      <p class="mt-1">
                        <span class="inline-flex items-center rounded-full px-2 py-1 text-xs font-semibold {
                          rangeData.state === 'starting' ? 'bg-yellow-100 text-yellow-800' :
                          rangeData.state === 'on' ? 'bg-green-100 text-green-800' :
                          rangeData.state === 'stopping' ? 'bg-orange-100 text-orange-800' :
                          rangeData.state === 'off' ? 'bg-gray-100 text-gray-800' :
                          'bg-blue-100 text-blue-800'
                        }">
                          {#if rangeData.state === 'starting'}
                            <svg class="mr-1 h-2 w-2 animate-spin" fill="none" viewBox="0 0 24 24">
                              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                            Deploying
                          {:else if rangeData.state === 'on'}
                            Started
                          {:else if rangeData.state === 'stopping'}
                            Stopping
                          {:else if rangeData.state === 'off'}
                            Stopped
                          {:else}
                            {rangeData.state || 'Unknown'}
                          {/if}
                        </span>
                      </p>
                    </div>
                    
                    <div>
                      <h3 class="text-sm font-medium text-gray-500">Created</h3>
                      <p class="mt-1">
                        {rangeData.date 
                          ? new Date(rangeData.date).toLocaleString() 
                          : 'Unknown'}
                      </p>
                    </div>
                    
                    <div>
                      <h3 class="text-sm font-medium text-gray-500">Region</h3>
                      <p class="mt-1 font-mono text-sm">
                        <span class="rounded bg-gray-100 p-1">{rangeData.region || 'Unknown'}</span>
                      </p>
                    </div>


                    <div class="mt-4 flex space-x-2">
                      <button
                        class="flex flex-1 items-center justify-center rounded bg-green-500 px-4 py-2 text-white hover:bg-green-600"
                      >
                        {rangeData.isRunning ? 'Stop Range' : 'Start Range'}
                      </button>
                      
                      <button
                        class="flex items-center justify-center rounded bg-red-500 px-4 py-2 text-white hover:bg-red-600"
                        on:click={() => (showDeleteConfirm = true)}
                      >
                        Delete Range
                      </button>
                    </div>
                  </div>
                </div>

                <!-- Right column: Hosts Status -->
                <div>
                  <h2 class="mb-4 text-lg font-semibold">Hosts Status</h2>
                  
                  <div class="rounded-lg border border-gray-200 bg-white shadow">
                    <!-- Jumpbox (always present) -->
                    <div class="border-b border-gray-200 px-4 py-3">
                      <div class="flex items-center justify-between">
                        <div>
                          <h3 class="font-medium">Jumpbox</h3>
                          {#if rangeData.jumpbox_ip || rangeData.jumpbox_public_ip}
                            <button 
                              type="button"
                              class="text-left text-sm text-gray-500 hover:text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-300 rounded"
                              on:click={() => copyIPAddress(rangeData.jumpbox_ip || rangeData.jumpbox_public_ip, 'Jumpbox')}
                              on:keydown={(e) => handleKeyDown(e, rangeData.jumpbox_ip || rangeData.jumpbox_public_ip, 'Jumpbox')}
                              aria-label="Copy Jumpbox IP address to clipboard"
                            >
                              {rangeData.jumpbox_ip || rangeData.jumpbox_public_ip}
                            </button>
                          {:else}
                            <p class="text-sm text-gray-500">
                              IP pending
                            </p>
                          {/if}
                        </div>
                        <span class="rounded-full bg-green-100 px-2 py-1 text-xs font-medium text-green-800">
                          Started
                        </span>
                      </div>
                      {#if rangeData.jumpbox_ip || rangeData.jumpbox_public_ip}
                        <div class="mt-2 flex">
                          <button
                            class="text-sm text-blue-600 hover:text-blue-800"
                            on:click={() => (activeTab = 'access')}
                          >
                            View SSH Info
                          </button>
                        </div>
                      {/if}
                    </div>
                    
                    <!-- Check if there are VPCs with subnets and hosts -->
                    {#if networkData && networkData.vpcs && networkData.vpcs.length > 0}
                      {#each networkData.vpcs as vpc}
                        {#if vpc.subnets && vpc.subnets.length > 0}
                          {#each vpc.subnets as subnet}
                            {#if subnet.hosts && subnet.hosts.length > 0}
                              {#each subnet.hosts as host}
                                <div class="border-b border-gray-200 px-4 py-3">
                                  <div class="flex items-center justify-between">
                                    <div>
                                      <h3 class="font-medium">{host.hostname || 'Unnamed Host'}</h3>
                                      {#if host.ip_address || host.ip}
                                        <button 
                                          type="button"
                                          class="text-left text-sm text-gray-500 hover:text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-300 rounded"
                                          on:click={() => copyIPAddress(host.ip_address || host.ip, host.hostname || 'Unnamed Host')}
                                          aria-label="Copy {host.hostname || 'host'} IP address to clipboard"
                                        >
                                          {subnet.name || 'Unknown Subnet'} • {host.ip_address || host.ip}
                                        </button>
                                      {:else}
                                        <p class="text-sm text-gray-500">
                                          {subnet.name || 'Unknown Subnet'} • IP pending
                                        </p>
                                      {/if}
                                      <p class="text-xs text-gray-500">
                                        {host.os || 'Unknown OS'} • {host.spec || 'Unknown spec'}
                                      </p>
                                    </div>
                                    <span class="rounded-full bg-green-100 px-2 py-1 text-xs font-medium text-green-800">
                                      Started
                                    </span>
                                  </div>
                                </div>
                              {/each}
                            {/if}
                          {/each}
                        {/if}
                      {/each}
                    <!-- Alternative structure where vpc is a single object -->
                    {:else if networkData && networkData.vpc && networkData.vpc.subnets && networkData.vpc.subnets.length > 0}
                      {#each networkData.vpc.subnets as subnet}
                        {#if subnet.hosts && subnet.hosts.length > 0}
                          {#each subnet.hosts as host}
                            <div class="border-b border-gray-200 px-4 py-3">
                              <div class="flex items-center justify-between">
                                <div>
                                  <h3 class="font-medium">{host.hostname || 'Unnamed Host'}</h3>
                                  {#if host.ip_address || host.ip}
                                    <button 
                                      type="button"
                                      class="text-left text-sm text-gray-500 hover:text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-300 rounded"
                                      on:click={() => copyIPAddress(host.ip_address || host.ip, host.hostname || 'Unnamed Host')}
                                      on:keydown={(e) => handleKeyDown(e, host.ip_address || host.ip, host.hostname || 'Unnamed Host')}
                                      aria-label="Copy {host.hostname || 'host'} IP address to clipboard"
                                    >
                                      {subnet.name || 'Unknown Subnet'} • {host.ip_address || host.ip}
                                    </button>
                                  {:else}
                                    <p class="text-sm text-gray-500">
                                      {subnet.name || 'Unknown Subnet'} • IP pending
                                    </p>
                                  {/if}
                                  <p class="text-xs text-gray-500">
                                    {host.os || 'Unknown OS'} • {host.spec || 'Unknown spec'}
                                  </p>
                                </div>
                                <span class="rounded-full bg-green-100 px-2 py-1 text-xs font-medium text-green-800">
                                  Started
                                </span>
                              </div>
                            </div>
                          {/each}
                        {/if}
                      {/each}
                    <!-- Case where hosts might be directly in range data -->
                    {:else if rangeData.hosts && rangeData.hosts.length > 0}
                      {#each rangeData.hosts as host}
                        <div class="border-b border-gray-200 px-4 py-3">
                          <div class="flex items-center justify-between">
                            <div>
                              <h3 class="font-medium">{host.hostname || 'Unnamed Host'}</h3>
                              {#if host.ip_address || host.ip}
                                <button 
                                  type="button"
                                  class="text-left text-sm text-gray-500 hover:text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-300 rounded"
                                  on:click={() => copyIPAddress(host.ip_address || host.ip, host.hostname || 'Unnamed Host')}
                                  on:keydown={(e) => handleKeyDown(e, host.ip_address || host.ip, host.hostname || 'Unnamed Host')}
                                  aria-label="Copy {host.hostname || 'host'} IP address to clipboard"
                                >
                                  {host.subnet_name || 'Unknown Subnet'} • {host.ip_address || host.ip}
                                </button>
                              {:else}
                                <p class="text-sm text-gray-500">
                                  {host.subnet_name || 'Unknown Subnet'} • IP pending
                                </p>
                              {/if}
                              <p class="text-xs text-gray-500">
                                {host.os || 'Unknown OS'} • {host.spec || 'Unknown spec'}
                              </p>
                            </div>
                            <span class="rounded-full bg-green-100 px-2 py-1 text-xs font-medium text-green-800">
                              Started
                            </span>
                          </div>
                        </div>
                      {/each}
                    <!-- No hosts found case -->
                    {:else}
                      <div class="px-4 py-6 text-center text-gray-500">
                        <p>No additional hosts found in this range.</p>
                        <div class="mt-3 flex justify-center space-x-3">
                          <button
                            class="rounded-md bg-blue-500 px-3 py-1 text-sm text-white hover:bg-blue-700"
                            on:click={() => (activeTab = 'network')}
                          >
                            View Network Graph
                          </button>
                          <button
                            class="rounded-md bg-blue-500 px-3 py-1 text-sm text-white hover:bg-blue-700"
                            on:click={() => (activeTab = 'readme')}
                          >
                            View README
                          </button>
                        </div>
                      </div>
                    {/if}
                  </div>
                </div>
              </div>
            {:else if activeTab === 'network'}
              <div
                role="tabpanel"
                id="panel-network"
                aria-labelledby="tab-network"
                tabindex="0"
              >
                <h2 class="mb-4 text-lg font-semibold">Network Graph</h2>
                {#if networkData}
                  <NetworkGraph blueprintData={networkData} />
                {:else}
                  <div class="rounded border-l-4 border-amber-500 bg-amber-50 p-4 text-amber-700">
                    <p>Network data isn't available for this range.</p>
                  </div>
                {/if}
              </div>
            {:else if activeTab === 'readme'}
              <div
                role="tabpanel"
                id="panel-readme"
                aria-labelledby="tab-readme"
                tabindex="0"
              >
                <h2 class="mb-4 text-lg font-semibold">README</h2>
                <div class="markdown-content rounded border border-gray-200 bg-gray-50 p-6">
                  {@html readmeHtml}
                </div>
              </div>
            {:else if activeTab === 'access'}
              <div
                role="tabpanel"
                id="panel-access"
                aria-labelledby="tab-access"
                tabindex="0"
              >
                <h2 class="mb-4 text-lg font-semibold">Access Information</h2>
                
                <div class="mb-6 rounded-lg border border-gray-200 bg-gray-50 p-4">
                  <h3 class="mb-2 text-md font-medium">SSH Access</h3>
                  
                  {#if !showSSHKey}
                    <button
                      class="rounded-md bg-blue-500 px-4 py-2 text-white hover:bg-blue-700"
                      on:click={loadSSHKey}
                    >
                      Show SSH Key
                    </button>
                  {:else}
                    <div class="mb-2">
                      <p class="mb-1 text-gray-600">Use this private key to SSH into your range:</p>
                      <div class="relative">
                        <pre class="max-h-60 overflow-auto rounded border border-gray-300 bg-gray-100 p-3 text-sm">{sshKey}</pre>
                        <div class="absolute top-2 right-2 flex space-x-1">
                          <button
                            class="rounded bg-gray-200 p-1 hover:bg-gray-300"
                            on:click={copySSHKey}
                            title="Copy to clipboard"
                            aria-label="Copy SSH key to clipboard"
                          >
                            {#if copiedSSH}
                              <svg class="h-5 w-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                              </svg>
                            {:else}
                              <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3"></path>
                              </svg>
                            {/if}
                          </button>
                          <button
                            class="rounded bg-gray-200 p-1 hover:bg-gray-300"
                            on:click={downloadSSHKey}
                            title="Download as PEM file"
                            aria-label="Download SSH key as PEM file"
                          >
                            <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path>
                            </svg>
                          </button>
                        </div>
                      </div>
                    </div>
                    
                    <div class="mt-4">
                      <h4 class="mb-1 font-medium">Connection Instructions:</h4>
                      <ol class="list-inside list-decimal space-y-2 text-sm">
                        <li>Save the private key to a file (e.g., <code>{(rangeData.name || 'range').toLowerCase().replace(/[^a-z0-9]/g, '-')}.pem</code>) or use the download button</li>
                        <li>Set the correct permissions: <code>chmod 600 {(rangeData.name || 'range').toLowerCase().replace(/[^a-z0-9]/g, '-')}.pem</code></li>
                        <li>Connect using: <code>ssh -i {(rangeData.name || 'range').toLowerCase().replace(/[^a-z0-9]/g, '-')}.pem ubuntu@{rangeData.jumpbox_ip || rangeData.jumpbox_public_ip || 'JUMPBOX_IP'}</code></li>
                      </ol>
                    </div>
                    
                    <div class="mt-4 flex">
                      <button
                        class="flex items-center rounded-md bg-blue-500 px-4 py-2 text-white hover:bg-blue-700"
                        on:click={downloadSSHKey}
                      >
                        <svg class="mr-2 h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path>
                        </svg>
                        Download Key
                      </button>
                    </div>
                  {/if}
                </div>

                {#if rangeData.vpn_enabled}
                  <div class="rounded-lg border border-gray-200 bg-gray-50 p-4">
                    <h3 class="mb-2 text-md font-medium">VPN Access</h3>
                    <p>VPN configuration and connection instructions will be displayed here.</p>
                    <!-- VPN content would go here when implemented -->
                  </div>
                {/if}
              </div>
            {/if}
          </div>
        </div>
      {:else}
        <div class="rounded border-l-4 border-amber-500 bg-amber-50 p-4 text-amber-700 shadow-md">
          <p class="mb-2 font-bold">Range Not Found</p>
          <p>The requested range could not be found or you don't have permission to view it.</p>
          <a
            href="/ranges"
            class="mt-4 inline-block rounded bg-blue-500 px-4 py-2 text-white hover:bg-blue-600"
          >
            Back to Ranges
          </a>
        </div>
      {/if}
      
      <!-- Delete confirmation modal -->
      {#if showDeleteConfirm && rangeData}
        <div class="fixed inset-0 z-50 flex items-center justify-center" 
          role="dialog" 
          aria-modal="true" 
          aria-labelledby="delete-dialog-title">
          <!-- Backdrop -->
          <div 
            class="absolute inset-0 bg-gray-800 bg-opacity-75 transition-opacity"
            on:click={() => !isDeletingRange && (showDeleteConfirm = false)}
            on:keydown={(e) => e.key === 'Escape' && !isDeletingRange && (showDeleteConfirm = false)}
            role="presentation"
          ></div>
          
          <!-- Modal dialog -->
          <div class="relative w-full max-w-md rounded-lg bg-white shadow-xl">
            <!-- Close button -->
            <button 
              class="absolute top-2 right-2 text-gray-400 hover:text-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-300 rounded-full p-1" 
              on:click={() => !isDeletingRange && (showDeleteConfirm = false)}
              aria-label="Close dialog"
            >
              <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
            
            <div class="p-6">
              <div class="mb-4 text-center">
                <svg 
                  class="mx-auto mb-4 h-12 w-12 text-red-500" 
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
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" 
                  />
                </svg>
                <h3 id="delete-dialog-title" class="text-xl font-bold text-gray-900">
                  Delete Range
                </h3>
                <p class="mt-2 text-gray-600">
                  Are you sure you want to delete <strong>{rangeData.name}</strong>? This action cannot be undone.
                </p>
              </div>
              
              <div class="mt-6 flex justify-end space-x-3">
                <button
                  class="rounded border border-gray-300 bg-white px-4 py-2 text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-300"
                  on:click={() => (showDeleteConfirm = false)}
                  disabled={isDeletingRange}
                >
                  Cancel
                </button>
                <button
                  class="rounded bg-red-500 px-4 py-2 text-white hover:bg-red-600 disabled:opacity-70 focus:outline-none focus:ring-2 focus:ring-red-300"
                  on:click={deleteRange}
                  disabled={isDeletingRange}
                >
                  {#if isDeletingRange}
                    <span class="flex items-center">
                      <svg
                        class="mr-2 -ml-1 h-4 w-4 animate-spin text-white"
                        xmlns="http://www.w3.org/2000/svg"
                        fill="none"
                        viewBox="0 0 24 24"
                        aria-hidden="true"
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
