<script lang="ts">
  import { loadingStore } from '$lib/stores/loading';
  import LoadingSpinner from './LoadingSpinner.svelte';
  import { fade } from 'svelte/transition';

  export let loadingKey: string;
  export let overlay: boolean = true;
  export let showProgress: boolean = false;
  export let showMessage: boolean = true;
  export let spinnerSize: 'sm' | 'md' | 'lg' = 'md';
  export let spinnerColor: 'blue' | 'gray' | 'white' = 'blue';

  $: loadingState = $loadingStore[loadingKey];
  $: isLoading = loadingState?.isLoading ?? false;
  $: message = loadingState?.message;
  $: progress = loadingState?.progress;

  // Calculate progress bar classes
  $: progressBarClasses = overlay
    ? 'bg-white bg-opacity-20'
    : 'bg-gray-200';

  $: progressFillClasses = overlay
    ? 'bg-white'
    : 'bg-blue-500';
</script>

{#if isLoading}
  <div 
    class="
      {overlay ? 'absolute inset-0 bg-black bg-opacity-50 z-40' : 'relative'}
      flex flex-col items-center justify-center p-6
    "
    transition:fade="{{ duration: 200 }}"
    aria-live="polite"
    aria-busy="true"
  >
    <div class="text-center">
      <!-- Spinner -->
      <LoadingSpinner 
        size={spinnerSize} 
        color={overlay ? 'white' : spinnerColor}
        overlay={false}
      />

      <!-- Message -->
      {#if showMessage && message}
        <p class="mt-4 text-sm {overlay ? 'text-white' : 'text-gray-600'}">
          {message}
        </p>
      {/if}

      <!-- Progress Bar -->
      {#if showProgress && progress !== undefined}
        <div class="mt-4 w-48">
          <div class="flex justify-between text-xs {overlay ? 'text-white' : 'text-gray-600'} mb-1">
            <span>Progress</span>
            <span>{Math.round(progress)}%</span>
          </div>
          <div class="w-full {progressBarClasses} rounded-full h-2">
            <div 
              class="{progressFillClasses} h-2 rounded-full transition-all duration-300 ease-out"
              style="width: {progress}%"
              role="progressbar"
              aria-valuenow={progress}
              aria-valuemin="0"
              aria-valuemax="100"
            ></div>
          </div>
        </div>
      {/if}
    </div>
  </div>
{/if}