<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import SearchInput from './SearchInput.svelte';
  import Button from './Button.svelte';

  const dispatch = createEventDispatcher<{
    search: string;
    action: void;
  }>();

  export let title: string;
  export let searchPlaceholder = 'Search...';
  export let actionLabel: string | undefined = undefined;
  export let actionVariant: 'primary' | 'secondary' | 'danger' | 'success' | 'ghost' = 'primary';
  export let showSearch = true;
  export let searchValue = '';
  
  // Allow custom classes to be passed
  let className = '';
  export { className as class };

  function handleSearch(event: CustomEvent<string>) {
    searchValue = event.detail;
    dispatch('search', event.detail);
  }

  function handleAction() {
    dispatch('action');
  }
</script>

<div class="top-10 flex h-auto md:h-15 w-full flex-col md:flex-row md:items-center justify-between border-b border-gray-300 bg-gray-100 p-4 space-y-4 md:space-y-0 {className}">
  <div class="flex items-center space-x-4">
    <h1 class="text-xl font-semibold text-gray-900">{title}</h1>
  </div>
  
  <div class="flex flex-col sm:flex-row items-stretch sm:items-center space-y-2 sm:space-y-0 sm:space-x-4">
    {#if showSearch}
      <div class="w-full sm:w-64">
        <SearchInput 
          bind:value={searchValue}
          placeholder={searchPlaceholder}
          on:search={handleSearch}
          size="md"
        />
      </div>
    {/if}
    
    {#if actionLabel}
      <Button 
        variant={actionVariant}
        on:click={handleAction}
        class="w-full sm:w-auto whitespace-nowrap"
      >
        {actionLabel}
      </Button>
    {/if}
    
    <!-- Allow additional action buttons through slot -->
    <div class="w-full sm:w-auto">
      <slot name="actions" />
    </div>
  </div>
</div>