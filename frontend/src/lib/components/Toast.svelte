<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { fly } from 'svelte/transition';
  import type { AppError } from '$lib/stores/error';
  import { ErrorIcon, AlertIcon, InfoIcon, CloseIcon } from './icons';

  const dispatch = createEventDispatcher<{
    dismiss: string;
  }>();

  export let error: AppError;
  export let position: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left' = 'top-right';

  function dismiss() {
    dispatch('dismiss', error.id);
  }

  $: iconComponent = {
    error: ErrorIcon,
    warning: AlertIcon,
    info: InfoIcon
  }[error.type] || InfoIcon;

  $: colorClasses = {
    error: 'bg-red-50 border-red-200 text-red-800',
    warning: 'bg-yellow-50 border-yellow-200 text-yellow-800',
    info: 'bg-blue-50 border-blue-200 text-blue-800'
  }[error.type];

  $: iconColorClasses = {
    error: 'text-red-400',
    warning: 'text-yellow-400',
    info: 'text-blue-400'
  }[error.type];
</script>

<div
  class="max-w-sm w-full {colorClasses} border rounded-lg shadow-lg pointer-events-auto ring-1 ring-black ring-opacity-5 overflow-hidden"
  transition:fly="{{ x: position.includes('right') ? 300 : -300, duration: 300 }}"
  role="alert"
  aria-live="assertive"
  aria-atomic="true"
>
  <div class="p-4">
    <div class="flex items-start">
      <div class="flex-shrink-0">
        <svelte:component 
          this={iconComponent} 
          size="h-5 w-5" 
          color={iconColorClasses}
          ariaLabel={error.type}
        />
      </div>
      <div class="ml-3 w-0 flex-1">
        <p class="text-sm font-medium">
          {error.message}
        </p>
        {#if error.details && typeof error.details === 'string'}
          <p class="mt-1 text-sm opacity-90">
            {error.details}
          </p>
        {/if}
        <p class="mt-1 text-xs opacity-75">
          {error.timestamp.toLocaleTimeString()}
        </p>
      </div>
      {#if error.dismissible}
        <div class="ml-4 flex-shrink-0 flex">
          <button
            type="button"
            class="inline-flex rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-gray-50 focus:ring-blue-600"
            on:click={dismiss}
            aria-label="Dismiss notification"
          >
            <CloseIcon size="h-4 w-4" color="currentColor" />
          </button>
        </div>
      {/if}
    </div>
  </div>
</div>