<script lang="ts">
  import { createEventDispatcher, onMount } from 'svelte';
  import { browser } from '$app/environment';
  import ErrorMessage from './ErrorMessage.svelte';
  import Button from './Button.svelte';
  import logger from '$lib/utils/logger';

  const dispatch = createEventDispatcher<{
    retry: void;
    report: { error: Error; errorInfo: any };
  }>();

  export let error: Error | null = null;
  export let errorInfo: any = null;
  export let fallback: boolean = true;
  export let showDetails: boolean = false;
  export let retryable: boolean = true;

  let hasError = false;
  let errorDetails = '';

  // Handle errors passed as props
  $: if (error) {
    hasError = true;
    errorDetails = error.message || 'An unexpected error occurred';
  }

  // Global error handler for unhandled promise rejections
  onMount(() => {
    if (browser) {
      const handleUnhandledRejection = (event: PromiseRejectionEvent) => {
        logger.error('Unhandled promise rejection', 'errorBoundary', event.reason);
        
        // Create a synthetic error object if needed
        const errorObj = event.reason instanceof Error 
          ? event.reason 
          : new Error(String(event.reason));
        
        handleError(errorObj, { source: 'unhandledRejection' });
        
        // Prevent the default browser error handling
        event.preventDefault();
      };

      const handleError = (errorObj: Error, info: any = {}) => {
        hasError = true;
        error = errorObj;
        errorInfo = info;
        errorDetails = errorObj.message || 'An unexpected error occurred';
        
        // Log error for debugging
        logger.error('Error boundary caught error', 'errorBoundary', { errorObj, info });
        
        // Dispatch event for parent components to handle
        dispatch('report', { error: errorObj, errorInfo: info });
      };

      // Listen for unhandled promise rejections
      window.addEventListener('unhandledrejection', handleUnhandledRejection);

      // Listen for general errors
      window.addEventListener('error', (event) => {
        handleError(event.error || new Error(event.message), {
          source: 'globalError',
          filename: event.filename,
          lineno: event.lineno,
          colno: event.colno
        });
      });

      return () => {
        window.removeEventListener('unhandledrejection', handleUnhandledRejection);
        window.removeEventListener('error', handleError);
      };
    }
  });

  function retry() {
    hasError = false;
    error = null;
    errorInfo = null;
    errorDetails = '';
    dispatch('retry');
  }

  function toggleDetails() {
    showDetails = !showDetails;
  }

  function reportError() {
    if (error) {
      dispatch('report', { error, errorInfo });
    }
  }

  // Check if we should show the error boundary
  $: shouldShowBoundary = hasError && fallback;
</script>

{#if shouldShowBoundary}
  <div class="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
    <div class="max-w-md w-full space-y-8">
      <div class="text-center">
        <div class="mx-auto h-12 w-12 text-red-500">
          <svg fill="none" stroke="currentColor" viewBox="0 0 48 48" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v3m0 0v3m0-3h3m-3 0H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
        </div>
        <h2 class="mt-6 text-center text-3xl font-extrabold text-gray-900">
          Something went wrong
        </h2>
        <p class="mt-2 text-center text-sm text-gray-600">
          An unexpected error occurred. Please try again or contact support if the problem persists.
        </p>
      </div>

      <div class="space-y-4">
        <ErrorMessage error={errorDetails} />
        
        {#if showDetails && (error?.stack || errorInfo)}
          <div class="bg-gray-100 rounded-md p-4">
            <h3 class="text-sm font-medium text-gray-900 mb-2">Error Details</h3>
            <pre class="text-xs text-gray-600 overflow-auto max-h-32 whitespace-pre-wrap">
{error?.stack || JSON.stringify(errorInfo, null, 2)}
            </pre>
          </div>
        {/if}

        <div class="flex flex-col space-y-3 sm:flex-row sm:space-y-0 sm:space-x-3">
          {#if retryable}
            <Button 
              variant="primary" 
              fullWidth={true}
              on:click={retry}
            >
              Try Again
            </Button>
          {/if}
          
          <Button 
            variant="secondary" 
            fullWidth={true}
            on:click={toggleDetails}
          >
            {showDetails ? 'Hide' : 'Show'} Details
          </Button>
        </div>

        <div class="text-center">
          <button 
            type="button"
            class="text-sm text-gray-500 hover:text-gray-700 underline"
            on:click={reportError}
          >
            Report this error
          </button>
        </div>
      </div>
    </div>
  </div>
{:else}
  <slot />
{/if}