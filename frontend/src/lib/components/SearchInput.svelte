<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { SEARCH } from '$lib/constants';

  const dispatch = createEventDispatcher<{
    search: string;
    input: string;
    clear: void;
  }>();

  export let value = '';
  export let placeholder = 'Search...';
  export let disabled = false;
  export let debounceMs = SEARCH.DEBOUNCE_DELAY;
  export let size: 'sm' | 'md' | 'lg' = 'md';
  export let fullWidth = true;
  
  // Allow custom classes to be passed
  let className = '';
  export { className as class };

  let debounceTimer: NodeJS.Timeout;

  const sizeClasses = {
    sm: 'px-3 py-1.5 pl-10 text-sm',
    md: 'px-4 py-2 pl-10 text-base',
    lg: 'px-6 py-3 pl-12 text-lg'
  };

  const iconSizeClasses = {
    sm: 'h-4 w-4',
    md: 'h-5 w-5', 
    lg: 'h-6 w-6'
  };

  $: baseClasses = [
    'rounded-md border border-gray-300 bg-white text-gray-900 placeholder-gray-500',
    'focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500',
    'disabled:bg-gray-50 disabled:text-gray-500 disabled:cursor-not-allowed',
    sizeClasses[size],
    fullWidth ? 'w-full' : '',
    className
  ].filter(Boolean).join(' ');

  function handleInput(event: Event) {
    const target = event.target as HTMLInputElement;
    value = target.value;
    
    // Dispatch immediate input event
    dispatch('input', value);
    
    // Clear existing timer
    if (debounceTimer) {
      clearTimeout(debounceTimer);
    }
    
    // Set new debounced timer for search
    debounceTimer = setTimeout(() => {
      dispatch('search', value);
    }, debounceMs);
  }

  function handleClear() {
    value = '';
    if (debounceTimer) {
      clearTimeout(debounceTimer);
    }
    dispatch('clear');
    dispatch('search', '');
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'Escape') {
      handleClear();
    }
  }
</script>

<div class="relative {fullWidth ? 'w-full' : ''}">
  <!-- Search Icon -->
  <div class="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
    <svg
      class="text-gray-400 {iconSizeClasses[size]}"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        stroke-linecap="round"
        stroke-linejoin="round"
        stroke-width="2"
        d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
      />
    </svg>
  </div>

  <!-- Input Field -->
  <input
    type="text"
    {value}
    {placeholder}
    {disabled}
    class={baseClasses}
    on:input={handleInput}
    on:keydown={handleKeydown}
    {...$$restProps}
  />

  <!-- Clear Button (only show when there's text) -->
  {#if value.length > 0 && !disabled}
    <button
      type="button"
      class="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400 hover:text-gray-600 focus:outline-none"
      on:click={handleClear}
      aria-label="Clear search"
    >
      <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M6 18L18 6M6 6l12 12"
        />
      </svg>
    </button>
  {/if}
</div>