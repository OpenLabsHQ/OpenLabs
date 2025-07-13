<script lang="ts">
  import { onMount, onDestroy } from 'svelte'
  import { goto } from '$app/navigation'
  import { rangesApi, type Job } from '$lib/api'
  import { LoadingSpinner, Button } from '$lib/components'
  import { AlertIcon, BackArrowIcon, ClockIcon, SuccessIcon, ErrorIcon, InfoIcon, GearIcon } from '$lib/components/icons'
  import { FlaskAnimation } from '$lib/components'
  import Sidebar from '$lib/components/Sidebar.svelte'
  import { auth } from '$lib/stores/auth'
  import { browser } from '$app/environment'
  import { calculateJobElapsedTime, formatElapsedTime, createElapsedTimer } from '$lib/utils/time'
  import { extractRangeIdFromJob, extractRangeInfoFromJob, getDeploymentStatusMessage } from '$lib/utils/job'
  import { formatErrorMessage } from '$lib/utils/error'
  import logger from '$lib/utils/logger'

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
  let rangeId: string | null = null
  let rangeInfo: { id: string; name?: string } | null = null

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
          error = formatErrorMessage(result.error, 'Failed to load deployment status')
          return
        }

        job = result.data as Job
        
        // If job is already complete, extract range ID and redirect
        if (job.status === 'complete') {
          logger.debug('Job completed', 'ranges.building', job.result);
          
          rangeInfo = extractRangeInfoFromJob(job)
          rangeId = extractRangeIdFromJob(job)
          
          stopTimeCounter()
          
          if (rangeId) {
            logger.debug('Range ID found', 'ranges.building', { rangeId, rangeInfo });
            setTimeout(() => {
              goto(`/ranges/${rangeId}`)
            }, 2000)
          } else {
            logger.warn('No range ID found in job result, redirecting to ranges list', 'ranges.building');
            setTimeout(() => {
              goto('/ranges')
            }, 2000)
          }
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
        logger.error('Error loading job status', 'ranges.building', err)
        error = err instanceof Error ? err.message : 'Failed to load deployment status'
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
          logger.error('Polling error', 'ranges.building', result.error)
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
          logger.debug('Job completed during polling', 'ranges.building', updatedJob.result);
          
          stopTimeCounter()
          if (pollingInterval) {
            clearInterval(pollingInterval)
            pollingInterval = null
          }

          // Extract range ID from job result
          rangeInfo = extractRangeInfoFromJob(updatedJob)
          rangeId = extractRangeIdFromJob(updatedJob)
          
          if (rangeId) {
            logger.debug('Range ID found during polling', 'ranges.building', { rangeId, rangeInfo });
            // Redirect to the completed range after a short delay
            setTimeout(() => {
              goto(`/ranges/${rangeId}`)
            }, 2000)
          } else {
            logger.warn('No range ID found during polling, redirecting to ranges list', 'ranges.building');
            // Fallback to ranges list if no range ID
            setTimeout(() => {
              goto('/ranges')
            }, 2000)
          }
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
        logger.error('Error during polling', 'ranges.building', err)
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
  <title>OpenLabs | Range Building</title>
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
          <p class="mt-4 text-gray-600">Loading deployment status...</p>
        </div>
      {:else if error}
        <div class="mx-auto max-w-2xl">
          <div class="rounded border-l-4 border-red-500 bg-red-50 p-4 text-red-700 shadow-md">
            <div class="flex items-center">
              <AlertIcon size="lg" color="currentColor" class="mr-3" />
              <div>
                <p class="mb-2 font-bold">Unable to Load Deployment Status</p>
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
            
            <h1 class="text-3xl font-bold text-gray-900">Range Deployment</h1>
            <p class="mt-2 text-gray-600">Job ID: {job.arq_job_id}</p>
          </div>

          <!-- Status Card -->
          <div class="overflow-hidden rounded-lg bg-white shadow-md">
            <div class="p-6">
              <!-- Status Header -->
              <div class="mb-6 flex items-center justify-between">
                <div class="flex items-center">
                  {#if job.status === 'queued'}
                    <div class="mr-3 h-8 w-8 rounded-full bg-yellow-100 flex items-center justify-center">
                      <ClockIcon size="md" color="var(--color-yellow-600)" />
                    </div>
                  {:else if job.status === 'in_progress'}
                    <div class="mr-3 h-8 w-8 rounded-full bg-blue-100 flex items-center justify-center">
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
                    <p class="text-sm text-gray-600">{getDeploymentStatusMessage(job)}</p>
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
                    <span>Deployment Progress</span>
                    <span>{job.status === 'queued' ? 'Waiting to start...' : 'In progress...'}</span>
                  </div>
                  <div class="w-full bg-gray-200 rounded-full h-2">
                    <div class="bg-blue-600 h-2 rounded-full transition-all duration-300 {job.status === 'queued' ? 'w-1/4' : 'w-3/4'}"></div>
                  </div>
                </div>
              {/if}

              <!-- Job Details -->
              <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <h3 class="text-sm font-medium text-gray-500">Job Name</h3>
                  <p class="mt-1 text-sm text-gray-900">{job.job_name || 'Range Deployment'}</p>
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
                      <h3 class="text-sm font-medium text-red-800">Deployment Failed</h3>
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
                      <h3 class="text-sm font-medium text-green-800">Deployment Successful</h3>
                      <div class="mt-2 text-sm text-green-700">
                        <p>Your range has been successfully deployed and is ready to use.</p>
                        {#if rangeId}
                          <p class="mt-1">Redirecting to your new range{rangeInfo?.name ? ` "${rangeInfo.name}"` : ''}...</p>
                        {:else}
                          <p class="mt-1">Redirecting to ranges list...</p>
                        {/if}
                      </div>
                    </div>
                  </div>
                </div>
              {/if}

              <!-- Action Buttons -->
              <div class="mt-6 flex space-x-3">
                {#if job.status === 'complete'}
                  {#if rangeId}
                    <Button variant="primary" href={`/ranges/${rangeId}`}>
                      View Range{rangeInfo?.name ? ` "${rangeInfo.name}"` : ''}
                    </Button>
                  {:else}
                    <Button variant="primary" href="/ranges">
                      View All Ranges
                    </Button>
                  {/if}
                {:else if job.status === 'failed'}
                  <Button variant="primary" href="/blueprints">
                    Try Again
                  </Button>
                {/if}
                
                <Button variant="secondary" on:click={goToRanges}>
                  Back to Ranges
                </Button>
              </div>
            </div>
          </div>

          <!-- Flask and gear animation for deploying ranges -->
          {#if job && (job.status === 'queued' || job.status === 'in_progress')}
            <div class="mt-6 rounded-lg bg-blue-50 p-6">
              <h3 class="mb-4 text-center text-lg font-medium text-blue-800">Infrastructure Creation</h3>
              
              <div class="flex items-center justify-center space-x-12">
                <!-- Flask animation on the left -->
                <FlaskAnimation label="Creating resources" color="blue" />
                
                <!-- Construction/gears animation on the right -->
                <div class="flex flex-col items-center">
                  <div class="relative h-[100px] flex items-center justify-center">
                    <!-- Main large gear -->
                    <GearIcon 
                      size="2xl" 
                      color="var(--color-blue-500)" 
                      animate={true}
                    />
                    
                    <!-- Smaller gear (positioned to mesh with main gear) -->
                    <GearIcon 
                      size="xl" 
                      color="var(--color-blue-300)" 
                      animate={true} 
                      reverse={true} 
                      class="absolute -right-5 top-1" 
                    />
                  </div>
                  <p class="mt-2 text-sm font-medium text-blue-700">Building infrastructure</p>
                </div>
              </div>
            </div>
          {/if}

          <!-- Help Text -->
          <div class="mt-6 rounded-lg bg-blue-50 p-4">
            <div class="flex">
              <InfoIcon size="md" color="var(--color-blue-400)" />
              <div class="ml-3">
                <h3 class="text-sm font-medium text-blue-800">About Range Deployment</h3>
                <div class="mt-2 text-sm text-blue-700">
                  <p>Range deployment time will depend on the complexity of your blueprint. 
                     We automatically check the status every 30 seconds and will redirect you when complete.
                     Feel free to leave this page at any time</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      {/if}
    </div>
  </div>
</div>

