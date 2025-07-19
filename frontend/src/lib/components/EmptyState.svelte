<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import Button from './Button.svelte';
  import BlueprintIcon from './icons/BlueprintIcon.svelte';
  import RangeIcon from './icons/RangeIcon.svelte';
  import WorkspaceIcon from './icons/WorkspaceIcon.svelte';
  import SearchIcon from './icons/SearchIcon.svelte';

  const dispatch = createEventDispatcher<{
    action: void;
  }>();

  export let title: string;
  export let description: string;
  export let actionLabel: string | undefined = undefined;
  export let actionVariant: 'primary' | 'secondary' | 'danger' | 'success' | 'ghost' = 'primary';
  export let iconType: 'blueprint' | 'range' | 'workspace' | 'search' | 'custom' = 'search';
  
  // Allow custom classes to be passed
  let className = '';
  export { className as class };

  function handleAction() {
    dispatch('action');
  }
</script>

<div class="w-full p-10 text-center {className}">
  <div class="rounded-lg border border-blue-200 bg-blue-50 p-8 text-blue-800 shadow-sm">
    <!-- Icon -->
    <div class="mb-4">
      {#if iconType === 'custom'}
        <slot name="icon" />
      {:else if iconType === 'blueprint'}
        <BlueprintIcon />
      {:else if iconType === 'range'}
        <RangeIcon />
      {:else if iconType === 'workspace'}
        <WorkspaceIcon />
      {:else if iconType === 'search'}
        <SearchIcon />
      {/if}
    </div>
    
    <!-- Title -->
    <h3 class="text-xl font-bold text-blue-900 mb-2">
      {title}
    </h3>
    
    <!-- Description -->
    <p class="text-blue-700 mb-6">
      {description}
    </p>
    
    <!-- Action Button -->
    {#if actionLabel}
      <Button 
        variant={actionVariant}
        on:click={handleAction}
      >
        {actionLabel}
      </Button>
    {/if}
    
    <!-- Custom action slot -->
    <slot name="action" />
  </div>
</div>