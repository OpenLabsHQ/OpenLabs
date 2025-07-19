<script lang="ts">
  import { errorStore } from '$lib/stores/error';
  import Toast from './Toast.svelte';

  export let position: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left' = 'top-right';
  export let maxToasts: number = 5;

  $: errors = $errorStore.errors;
  $: visibleErrors = errors.slice(-maxToasts); // Show only the most recent toasts

  function handleDismiss(event: CustomEvent<string>) {
    errorStore.removeError(event.detail);
  }

  $: positionClasses = {
    'top-right': 'top-0 right-0',
    'top-left': 'top-0 left-0', 
    'bottom-right': 'bottom-0 right-0',
    'bottom-left': 'bottom-0 left-0'
  }[position];
</script>

{#if visibleErrors.length > 0}
  <div class="fixed {positionClasses} p-6 space-y-4 z-50 pointer-events-none">
    {#each visibleErrors as error (error.id)}
      <Toast 
        {error} 
        {position}
        on:dismiss={handleDismiss}
      />
    {/each}
  </div>
{/if}