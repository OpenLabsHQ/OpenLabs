<script lang="ts">
  import { onMount, onDestroy } from 'svelte'
  import { goto } from '$app/navigation'
  import { rangesApi, type Job } from '$lib/api'
  import { LoadingSpinner, Button, DestructionAnimation, FlaskAnimation } from '$lib/components'
  import { AlertIcon, BackArrowIcon, ClockIcon, SuccessIcon, ErrorIcon, InfoIcon, GearIcon } from '$lib/components/icons'
  import Sidebar from '$lib/components/Sidebar.svelte'
  import { auth } from '$lib/stores/auth'
  import { browser } from '$app/environment'
  import { calculateJobElapsedTime, formatElapsedTime, createElapsedTimer } from '$lib/utils/time'
  import { extractRangeIdFromJob, extractRangeInfoFromJob, getDeploymentStatusMessage, getDestructionStatusMessage } from '$lib/utils/job'
  import { formatErrorMessage } from '$lib/utils/error'
  import { API_TIMEOUTS } from '$lib/constants/timings'
  import logger from '$lib/utils/logger'

  // Props
  export let jobId: string
  export let jobType: 'deployment' | 'destruction'
  export let onComplete: ((job: Job) => void) | undefined = undefined
  export let successRedirectPath: string | null = null
  
  // Component state
  let job: Job | null = null
  let isLoading = true
  let error = ''
  let pollingInterval: ReturnType<typeof setInterval> | null = null
  let elapsedTime = 0
  let stopElapsedTimer: (() => void) | null = null
  let rangeId: string | null = null
  let rangeInfo: { id: string; name?: string } | null = null

  // Computed values based on job type
  $: pageTitle = jobType === 'deployment' ? 'Range Deployment' : 'Range Destruction'
  $: loadingMessage = jobType === 'deployment' ? 'Loading deployment status...' : 'Loading destruction status...'
  $: errorTitle = jobType === 'deployment' ? 'Unable to Load Deployment Status' : 'Unable to Load Destruction Status'
  $: failureMessage = jobType === 'deployment' ? 'Failed to load deployment status' : 'Failed to load destruction status'
  $: jobName = job?.job_name || (jobType === 'deployment' ? 'Range Deployment' : 'Range Destruction')
  $: statusMessage = jobType === 'deployment' ? getDeploymentStatusMessage(job) : getDestructionStatusMessage(job)
  $: progressLabel = jobType === 'deployment' ? 'Deployment Progress' : 'Destruction Progress'
  $: progressColor = jobType === 'deployment' ? 'blue' : 'red'
  $: animationColor = jobType === 'deployment' ? 'blue' : 'red'
  $: helpTitle = jobType === 'deployment' ? 'About Range Deployment' : 'About Range Destruction'
  $: helpMessage = jobType === 'deployment' 
    ? 'Range deployment time will depend on the complexity of your blueprint. We automatically check the status every 30 seconds and will redirect you when complete. Feel free to leave this page at any time'
    : 'Range destruction time will depend on the complexity of your range. We automatically check the status every 30 seconds and will redirect you when complete. Feel free to leave this page at any time.'
  $: completionMessage = jobType === 'deployment'
    ? 'Your range has been successfully deployed and is ready to use.'
    : 'The range and all its resources have been successfully destroyed and cleaned up.'
  $: completionTitle = jobType === 'deployment' ? 'Deployment Successful' : 'Destruction Successful'
  $: failureTitle = jobType === 'deployment' ? 'Deployment Failed' : 'Destruction Failed'
  $: logContext = jobType === 'deployment' ? 'ranges.building' : 'ranges.destroying'

  // Status icon colors based on type and status
  $: queuedColor = jobType === 'deployment' ? 'var(--color-yellow-600)' : 'var(--color-orange-600)'
  $: queuedBgColor = jobType === 'deployment' ? 'bg-yellow-100' : 'bg-orange-100'
  $: progressBgColor = jobType === 'deployment' ? 'bg-blue-100' : 'bg-red-100'
  $: animationBgColor = jobType === 'deployment' ? 'bg-blue-50' : 'bg-red-50'
  $: helpBgColor = jobType === 'deployment' ? 'bg-blue-50' : 'bg-orange-50'
  $: helpTextColor = jobType === 'deployment' ? 'text-blue-800' : 'text-orange-800'
  $: helpTextColorSecondary = jobType === 'deployment' ? 'text-blue-700' : 'text-orange-700'
  $: helpIconColor = jobType === 'deployment' ? 'var(--color-blue-400)' : 'var(--color-orange-400)'

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
          error = formatErrorMessage(result.error, failureMessage)
          return
        }

        job = result.data as Job
        
        // Handle job completion
        if (job.status === 'complete') {
          logger.debug('Job completed', logContext, job.result);
          
          // For deployment jobs, extract range info
          if (jobType === 'deployment') {
            rangeInfo = extractRangeInfoFromJob(job)
            rangeId = extractRangeIdFromJob(job)
          }
          
          stopTimeCounter()
          
          // Call completion callback if provided
          if (onComplete) {
            onComplete(job)
          } else {
            // Default redirect behavior
            const redirectPath = jobType === 'deployment' && rangeId 
              ? `/ranges/${rangeId}`
              : successRedirectPath || '/ranges'
            
            setTimeout(() => {
              goto(redirectPath)
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
        logger.error('Error loading job status', logContext, err)
        error = err instanceof Error ? err.message : failureMessage
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
          logger.error('Polling error', logContext, result.error)
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
          logger.debug('Job completed during polling', logContext, updatedJob.result);
          
          stopTimeCounter()
          if (pollingInterval) {
            clearInterval(pollingInterval)
            pollingInterval = null
          }

          // For deployment jobs, extract range info
          if (jobType === 'deployment') {
            rangeInfo = extractRangeInfoFromJob(updatedJob)
            rangeId = extractRangeIdFromJob(updatedJob)
          }
          
          // Call completion callback if provided
          if (onComplete) {
            onComplete(updatedJob)
          } else {
            // Default redirect behavior
            const redirectPath = jobType === 'deployment' && rangeId 
              ? `/ranges/${rangeId}`
              : successRedirectPath || '/ranges'
            
            setTimeout(() => {
              goto(redirectPath)
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
        logger.error('Error during polling', logContext, err)
      }
    }, API_TIMEOUTS.JOB_POLLING_INTERVAL)
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
  <title>OpenLabs | {pageTitle}</title>
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
          <p class="mt-4 text-gray-600">{loadingMessage}</p>
        </div>
      {:else if error}
        <div class="mx-auto max-w-2xl">
          <div class="rounded border-l-4 border-red-500 bg-red-50 p-4 text-red-700 shadow-md">
            <div class="flex items-center">
              <AlertIcon size="lg" color="currentColor" class="mr-3" />
              <div>
                <p class="mb-2 font-bold">{errorTitle}</p>
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
            
            <h1 class="text-3xl font-bold text-gray-900">{pageTitle}</h1>
            <p class="mt-2 text-gray-600">Job ID: {job.arq_job_id}</p>
          </div>

          <!-- Status Card -->
          <div class="overflow-hidden rounded-lg bg-white shadow-md">
            <div class="p-6">
              <!-- Status Header -->
              <div class="mb-6 flex items-center justify-between">
                <div class="flex items-center">
                  {#if job.status === 'queued'}
                    <div class="mr-3 h-8 w-8 rounded-full {queuedBgColor} flex items-center justify-center">
                      <ClockIcon size="md" color={queuedColor} />
                    </div>
                  {:else if job.status === 'in_progress'}
                    <div class="mr-3 h-8 w-8 rounded-full {progressBgColor} flex items-center justify-center">
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
                    <p class="text-sm text-gray-600">{statusMessage}</p>
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
                    <span>{progressLabel}</span>
                    <span>{job.status === 'queued' ? 'Waiting to start...' : 'In progress...'}</span>
                  </div>
                  <div class="w-full bg-gray-200 rounded-full h-2">
                    <div class="bg-{progressColor}-600 h-2 rounded-full transition-all duration-300 {job.status === 'queued' ? 'w-1/4' : 'w-3/4'}"></div>
                  </div>
                </div>
              {/if}

              <!-- Job Details -->
              <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <h3 class="text-sm font-medium text-gray-500">Job Name</h3>
                  <p class="mt-1 text-sm text-gray-900">{jobName}</p>
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
                      <h3 class="text-sm font-medium text-red-800">{failureTitle}</h3>
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
                      <h3 class="text-sm font-medium text-green-800">{completionTitle}</h3>
                      <div class="mt-2 text-sm text-green-700">
                        <p>{completionMessage}</p>
                        {#if jobType === 'deployment'}
                          {#if rangeId}
                            <p class="mt-1">Redirecting to your new range{rangeInfo?.name ? ` "${rangeInfo.name}"` : ''}...</p>
                          {:else}
                            <p class="mt-1">Redirecting to ranges list...</p>
                          {/if}
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
                  {#if jobType === 'deployment' && rangeId}
                    <Button variant="primary" href={`/ranges/${rangeId}`}>
                      View Range{rangeInfo?.name ? ` "${rangeInfo.name}"` : ''}
                    </Button>
                  {:else}
                    <Button variant="primary" href="/ranges">
                      View All Ranges
                    </Button>
                  {/if}
                {:else if job.status === 'failed'}
                  {#if jobType === 'deployment'}
                    <Button variant="primary" href="/blueprints">
                      Try Again
                    </Button>
                  {:else}
                    <Button variant="primary" href="/ranges">
                      Back to Ranges
                    </Button>
                  {/if}
                {/if}
                
                <Button variant="secondary" on:click={goToRanges}>
                  Back to Ranges
                </Button>
              </div>
            </div>
          </div>

          <!-- Animation for active jobs -->
          {#if job && (job.status === 'queued' || job.status === 'in_progress')}
            <div class="mt-6 rounded-lg {animationBgColor} p-6">
              <h3 class="mb-4 text-center text-lg font-medium {helpTextColor}">
                {jobType === 'deployment' ? 'Infrastructure Creation' : 'Infrastructure Cleanup'}
              </h3>
              
              <div class="flex items-center justify-center space-x-12">
                <!-- Main animation -->
                {#if jobType === 'deployment'}
                  <FlaskAnimation label="Creating resources" color={animationColor} />
                {:else}
                  <DestructionAnimation label="Removing resources" />
                {/if}
                
                <!-- Gear animation -->
                <div class="flex flex-col items-center">
                  <div class="relative h-[100px] flex items-center justify-center">
                    <!-- Main large gear -->
                    <GearIcon 
                      size="2xl" 
                      color="var(--color-{animationColor}-500)" 
                      animate={true}
                      speed={jobType === 'destruction' ? 'slow' : undefined}
                    />
                    
                    <!-- Smaller gear -->
                    <GearIcon 
                      size="xl" 
                      color="var(--color-{animationColor}-300)" 
                      animate={true} 
                      reverse={true} 
                      speed={jobType === 'destruction' ? 'slow' : undefined}
                      class="absolute -right-5 top-1" 
                    />
                  </div>
                  <p class="mt-2 text-sm font-medium {helpTextColorSecondary}">
                    {jobType === 'deployment' ? 'Building infrastructure' : 'Cleaning up infrastructure'}
                  </p>
                </div>
              </div>
            </div>
          {/if}

          <!-- Help Text -->
          <div class="mt-6 rounded-lg {helpBgColor} p-4">
            <div class="flex">
              <InfoIcon size="md" color={helpIconColor} />
              <div class="ml-3">
                <h3 class="text-sm font-medium {helpTextColor}">{helpTitle}</h3>
                <div class="mt-2 text-sm {helpTextColorSecondary}">
                  <p>{helpMessage}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      {/if}
    </div>
  </div>
</div>