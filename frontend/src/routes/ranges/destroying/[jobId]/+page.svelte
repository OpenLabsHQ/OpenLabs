<script lang="ts">
  import { onMount, onDestroy } from 'svelte'
  import { goto } from '$app/navigation'
  import { rangesApi, type Job } from '$lib/api'
  import { LoadingSpinner, Button, DestructionAnimation } from '$lib/components'
  import { AlertIcon, BackArrowIcon, ClockIcon, SuccessIcon, ErrorIcon, InfoIcon, GearIcon } from '$lib/components/icons'
  import Sidebar from '$lib/components/Sidebar.svelte'
  import { auth } from '$lib/stores/auth'
  import { browser } from '$app/environment'
  import logger from '$lib/utils/logger'
  import { calculateJobElapsedTime, formatElapsedTime, createElapsedTimer } from '$lib/utils/time'
  import { getDestructionStatusMessage } from '$lib/utils/job'
  import { formatErrorMessage } from '$lib/utils/error'

  // Get job ID from page data
  export let data
  const jobId = data.jobId

  // Component state
  let job: Job | null = null
  let isLoading = true
  let error = ''
  let pollingInterval: ReturnType<typeof setInterval> | null = null
  let elapsedTime = 0
  let stopElapsedTimer: (() => void) | null = null


  // Clean up intervals on component destroy
  onDestroy(() => {
    if (pollingInterval) {
      clearInterval(pollingInterval)
    }
    if (stopElapsedTimer) {
      stopElapsedTimer()
    }
  })

  // Start elapsed time counter based on job timestamp
  function startTimeCounter() {
    if (stopElapsedTimer) {
      stopElapsedTimer()
    }
    
    if (!job) return
    
    // Use start_time if available, otherwise use enqueue_time
    const referenceTime = job.start_time || job.enqueue_time
    if (!referenceTime) return
    
    // Calculate initial elapsed time
    elapsedTime = calculateJobElapsedTime(job)
    
    // Start timer that updates based on reference timestamp
    stopElapsedTimer = createElapsedTimer(referenceTime, (elapsed) => {
      elapsedTime = elapsed
    })
  }

  // Stop elapsed time counter
  function stopTimeCounter() {
    if (stopElapsedTimer) {
      stopElapsedTimer()
      stopElapsedTimer = null
    }
  }

  // Load initial job status
  async function loadJobStatus() {
    if (browser) {
      // Check authentication
      if (!$auth.isAuthenticated) {
        goto('/login')
        return
      }

      try {
        isLoading = true
        error = ''

        const result = await rangesApi.getJobStatus(jobId)
        if (result.error) {
          error = formatErrorMessage(result.error, 'Failed to load destruction status')
          return
        }

        job = result.data as Job
        
        // If job is already complete, redirect to ranges list
        if (job.status === 'complete') {
          stopTimeCounter()
          setTimeout(() => {
            goto('/ranges')
          }, 2000)
          return
        }

        // If job failed, stop time counter
        if (job.status === 'failed') {
          stopTimeCounter()
          return
        }

        // Start time counter for active jobs
        if (job.status === 'queued' || job.status === 'in_progress') {
          startTimeCounter()
        }

      } catch (err) {
        logger.error('Error loading job status', 'ranges.destroying', err)
        error = err instanceof Error ? err.message : 'Failed to load destruction status'
      } finally {
        isLoading = false
      }
    }
  }

  // Start polling for job status
  function startPolling() {
    if (pollingInterval) return

    pollingInterval = setInterval(async () => {
      try {
        const result = await rangesApi.getJobStatus(jobId)
        if (result.error) {
          logger.error('Polling error', 'ranges.destroying', result.error)
          return
        }

        const updatedJob = result.data as Job
        job = updatedJob

        // Update elapsed time calculation if job has started but timer needs updating
        if ((updatedJob.status === 'queued' || updatedJob.status === 'in_progress') && stopElapsedTimer) {
          // Recalculate elapsed time in case job status changed or timestamps updated
          elapsedTime = calculateJobElapsedTime(updatedJob)
        }

        // Handle job completion
        if (updatedJob.status === 'complete') {
          stopTimeCounter()
          if (pollingInterval) {
            clearInterval(pollingInterval)
            pollingInterval = null
          }

          // Redirect to ranges list after a short delay
          setTimeout(() => {
            goto('/ranges')
          }, 2000)
        }

        // Handle job failure
        if (updatedJob.status === 'failed') {
          stopTimeCounter()
          if (pollingInterval) {
            clearInterval(pollingInterval)
            pollingInterval = null
          }
        }

      } catch (err) {
        logger.error('Error during polling', 'ranges.destroying', err)
      }
    }, 30000) // Poll every 30 seconds
  }

  // Initial setup
  onMount(() => {
    loadJobStatus().then(() => {
      // Only start polling if job is still in progress
      if (job && (job.status === 'queued' || job.status === 'in_progress')) {
        startPolling()
      }
    })
  })

  // Go back to ranges list
  function goToRanges() {
    goto('/ranges')
  }
</script>

<svelte:head>
  <title>OpenLabs | Range Destruction</title>
</svelte:head>

<div class="font-roboto flex h-screen bg-gray-100">
  <!-- Fixed sidebar -->
  <div class="fixed inset-y-0 left-0 z-10 w-54">
    <Sidebar />
  </div>

  <!-- Main content with sidebar margin -->
  <div class="ml-54 flex-1 overflow-y-auto">
    <div class="p-6">
      {#if isLoading}
        <div class="flex flex-col items-center justify-center p-20">
          <LoadingSpinner size="lg" />
          <p class="mt-4 text-gray-600">Loading destruction status...</p>
        </div>
      {:else if error}
        <div class="mx-auto max-w-2xl">
          <div class="rounded border-l-4 border-red-500 bg-red-50 p-4 text-red-700 shadow-md">
            <div class="flex items-center">
              <AlertIcon size="lg" color="currentColor" class="mr-3" />
              <div>
                <p class="mb-2 font-bold">Unable to Load Destruction Status</p>
                <p class="mb-4">{error}</p>
              </div>
            </div>
            <div class="mt-4">
              <Button variant="primary" on:click={goToRanges}>
                Back to Ranges
              </Button>
            </div>
          </div>
        </div>
      {:else if job}
        <div class="mx-auto max-w-2xl">
          <!-- Header -->
          <div class="mb-6">
            <Button 
              variant="ghost" 
              on:click={goToRanges}
              class="mb-4 flex items-center text-blue-500 hover:text-blue-700"
            >
              <BackArrowIcon size="md" color="currentColor" class="mr-1" />
              Back to Ranges
            </Button>
            
            <h1 class="text-3xl font-bold text-gray-900">Range Destruction</h1>
            <p class="mt-2 text-gray-600">Job ID: {job.arq_job_id}</p>
          </div>

          <!-- Status Card -->
          <div class="overflow-hidden rounded-lg bg-white shadow-md">
            <div class="p-6">
              <!-- Status Header -->
              <div class="mb-6 flex items-center justify-between">
                <div class="flex items-center">
                  {#if job.status === 'queued'}
                    <div class="mr-3 h-8 w-8 rounded-full bg-orange-100 flex items-center justify-center">
                      <ClockIcon size="md" color="var(--color-orange-600)" />
                    </div>
                  {:else if job.status === 'in_progress'}
                    <div class="mr-3 h-8 w-8 rounded-full bg-red-100 flex items-center justify-center">
                      <LoadingSpinner size="sm" />
                    </div>
                  {:else if job.status === 'complete'}
                    <div class="mr-3 h-8 w-8 rounded-full bg-green-100 flex items-center justify-center">
                      <SuccessIcon size="md" color="var(--color-green-600)" />
                    </div>
                  {:else if job.status === 'failed'}
                    <div class="mr-3 h-8 w-8 rounded-full bg-red-100 flex items-center justify-center">
                      <ErrorIcon size="md" color="var(--color-red-600)" />
                    </div>
                  {/if}
                  
                  <div>
                    <h2 class="text-xl font-semibold capitalize">{job.status.replace('_', ' ')}</h2>
                    <p class="text-sm text-gray-600">{getDestructionStatusMessage(job)}</p>
                  </div>
                </div>
                
                {#if job.status === 'queued' || job.status === 'in_progress'}
                  <div class="text-right">
                    <p class="text-sm text-gray-500">Elapsed Time</p>
                    <p class="text-lg font-semibold">{formatElapsedTime(elapsedTime)}</p>
                  </div>
                {/if}
              </div>

              <!-- Progress Indicator -->
              {#if job.status === 'queued' || job.status === 'in_progress'}
                <div class="mb-6">
                  <div class="flex justify-between text-sm text-gray-600 mb-2">
                    <span>Destruction Progress</span>
                    <span>{job.status === 'queued' ? 'Waiting to start...' : 'In progress...'}</span>
                  </div>
                  <div class="w-full bg-gray-200 rounded-full h-2">
                    <div class="bg-red-600 h-2 rounded-full transition-all duration-300 {job.status === 'queued' ? 'w-1/4' : 'w-3/4'}"></div>
                  </div>
                </div>
              {/if}

              <!-- Job Details -->
              <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <h3 class="text-sm font-medium text-gray-500">Job Name</h3>
                  <p class="mt-1 text-sm text-gray-900">{job.job_name || 'Range Destruction'}</p>
                </div>
                
                <div>
                  <h3 class="text-sm font-medium text-gray-500">Queued At</h3>
                  <p class="mt-1 text-sm text-gray-900">
                    {job.enqueue_time ? new Date(job.enqueue_time).toLocaleString() : 'Unknown'}
                  </p>
                </div>
                
                {#if job.start_time}
                  <div>
                    <h3 class="text-sm font-medium text-gray-500">Started At</h3>
                    <p class="mt-1 text-sm text-gray-900">
                      {new Date(job.start_time).toLocaleString()}
                    </p>
                  </div>
                {/if}
                
                {#if job.finish_time}
                  <div>
                    <h3 class="text-sm font-medium text-gray-500">Completed At</h3>
                    <p class="mt-1 text-sm text-gray-900">
                      {new Date(job.finish_time).toLocaleString()}
                    </p>
                  </div>
                {/if}
              </div>

              <!-- Error Message for Failed Jobs -->
              {#if job.status === 'failed' && job.error_message}
                <div class="mt-6 rounded border-l-4 border-red-500 bg-red-50 p-4">
                  <div class="flex">
                    <AlertIcon size="md" color="var(--color-red-400)" />
                    <div class="ml-3">
                      <h3 class="text-sm font-medium text-red-800">Destruction Failed</h3>
                      <div class="mt-2 text-sm text-red-700">
                        <p>{job.error_message}</p>
                      </div>
                    </div>
                  </div>
                </div>
              {/if}

              <!-- Success Message and Actions -->
              {#if job.status === 'complete'}
                <div class="mt-6 rounded border-l-4 border-green-500 bg-green-50 p-4">
                  <div class="flex">
                    <SuccessIcon size="md" color="var(--color-green-400)" />
                    <div class="ml-3">
                      <h3 class="text-sm font-medium text-green-800">Destruction Successful</h3>
                      <div class="mt-2 text-sm text-green-700">
                        <p>The range and all its resources have been successfully destroyed and cleaned up.</p>
                        <p class="mt-1">Redirecting to ranges list...</p>
                      </div>
                    </div>
                  </div>
                </div>
              {/if}

              <!-- Action Buttons -->
              <div class="mt-6 flex space-x-3">
                {#if job.status === 'failed'}
                  <Button variant="primary" href="/ranges">
                    Back to Ranges
                  </Button>
                {:else if job.status === 'complete'}
                  <Button variant="primary" href="/ranges">
                    View All Ranges
                  </Button>
                {:else}
                  <Button variant="secondary" on:click={goToRanges}>
                    Back to Ranges
                  </Button>
                {/if}
              </div>
            </div>
          </div>

          <!-- Destruction Animation for active jobs -->
          {#if job && (job.status === 'queued' || job.status === 'in_progress')}
            <div class="mt-8 rounded-lg bg-red-50 p-6">
              <h3 class="mb-4 text-center text-lg font-medium text-red-800">Infrastructure Cleanup</h3>
              
              <div class="flex items-center justify-center space-x-12">
                <!-- Destruction animation on the left -->
                <DestructionAnimation label="Removing resources" />
                
                <!-- Cleanup gear animation on the right -->
                <div class="flex flex-col items-center">
                  <div class="relative h-[100px] flex items-center justify-center">
                    <!-- Main large gear -->
                    <GearIcon 
                      size="2xl" 
                      color="var(--color-red-500)" 
                      animate={true}
                      speed="slow"
                    />
                    
                    <!-- Smaller gear -->
                    <GearIcon 
                      size="xl" 
                      color="var(--color-red-300)" 
                      animate={true} 
                      reverse={true} 
                      speed="slow"
                      class="absolute -right-5 top-1" 
                    />
                  </div>
                  <p class="mt-2 text-sm font-medium text-red-700">Cleaning up infrastructure</p>
                </div>
              </div>
            </div>
          {/if}

          <!-- Help Text -->
          <div class="mt-6 rounded-lg bg-orange-50 p-4">
            <div class="flex">
              <InfoIcon size="md" color="var(--color-orange-400)" />
              <div class="ml-3">
                <h3 class="text-sm font-medium text-orange-800">About Range Destruction</h3>
                <div class="mt-2 text-sm text-orange-700">
                  <p>Range destruction time will depend on the complexity of your range.
                     We automatically check the status every 30 seconds and will redirect you when complete.
                     Feel free to leave this page at any time.</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      {/if}
    </div>
  </div>
</div>

