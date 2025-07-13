<script lang="ts">
  import { onMount } from 'svelte'
  import AuthCheck from '$lib/components/AuthCheck.svelte'
  import LoadingSpinner from '$lib/components/LoadingSpinner.svelte'
  import ErrorBoundary from '$lib/components/ErrorBoundary.svelte'
  import ToastContainer from '$lib/components/ToastContainer.svelte'
  import SkipToContent from '$lib/components/SkipToContent.svelte'
  import { errorStore } from '$lib/stores/error'
  import logger from '$lib/utils/logger'

  // Import Tailwind CSS
  import '../tailwind.css'

  // Global auth state management
  let isInitializing = true

  function handleAuthSuccess() {
    // Don't redirect from the landing page
    isInitializing = false
  }

  function handleAuthFailure() {
    isInitializing = false
  }

  function handleGlobalError(event: CustomEvent<{ error: Error; errorInfo: any }>) {
    logger.error('Global error caught', 'app', event.detail);
    errorStore.handleApiError(event.detail.error, 'An unexpected error occurred');
  }

  function handleErrorRetry() {
    // Reload the page to recover from the error
    window.location.reload();
  }

  onMount(() => {
    // Auth state will be checked by the AuthCheck component
    // No need to check localStorage as we're using HTTP-only cookies
  })
</script>

<!-- Skip to content links for accessibility -->
<SkipToContent />

<!-- Global error boundary wraps the entire application -->
<ErrorBoundary 
  on:report={handleGlobalError}
  on:retry={handleErrorRetry}
>
  <AuthCheck
    onAuthSuccess={handleAuthSuccess}
    onAuthFailure={handleAuthFailure}
  />

  {#if isInitializing}
    <!-- Loading screen while checking authentication -->
    <div class="fixed inset-0 flex items-center justify-center bg-gray-900">
      <LoadingSpinner size="lg" color="white" />
    </div>
  {:else}
    <slot />
  {/if}

  <!-- Toast notifications for non-critical errors -->
  <ToastContainer position="top-right" />
</ErrorBoundary>
