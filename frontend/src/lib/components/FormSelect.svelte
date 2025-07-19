<script lang="ts">
  import { createEventDispatcher } from 'svelte';

  const dispatch = createEventDispatcher<{
    change: string;
    blur: FocusEvent;
    focus: FocusEvent;
  }>();

  interface Option {
    value: string | number;
    label: string;
    disabled?: boolean;
  }

  export let value = '';
  export let options: Option[] = [];
  export let placeholder = 'Select an option';
  export let label = '';
  export let id = '';
  export let name = '';
  export let required = false;
  export let disabled = false;
  export let error = '';
  export let hint = '';
  export let theme: 'light' | 'dark' = 'light';
  export let size: 'sm' | 'md' | 'lg' = 'md';
  export let fullWidth = true;
  export let rounded: 'none' | 'sm' | 'md' | 'lg' | 'full' = 'md';

  // Allow custom classes to be passed
  let className = '';
  export { className as class };

  // Generate unique ID if not provided
  $: selectId = id || `select-${Math.random().toString(36).substr(2, 9)}`;

  const themeClasses = {
    light: {
      base: 'border-gray-300 bg-white text-gray-900',
      focus: 'focus:border-blue-500 focus:ring-blue-500',
      error: 'border-red-300 bg-red-50 text-red-900 focus:border-red-500 focus:ring-red-500',
      disabled: 'disabled:bg-gray-50 disabled:text-gray-500 disabled:cursor-not-allowed'
    },
    dark: {
      base: 'border-gray-700 bg-gray-800 text-white',
      focus: 'focus:border-indigo-500 focus:ring-indigo-500',
      error: 'border-red-500 bg-red-900/50 text-red-300 focus:border-red-500 focus:ring-red-500',
      disabled: 'disabled:bg-gray-700 disabled:text-gray-400 disabled:cursor-not-allowed'
    }
  };

  const sizeClasses = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-3 py-2 text-sm',
    lg: 'px-4 py-3 text-base'
  };

  const roundedClasses = {
    none: 'rounded-none',
    sm: 'rounded-sm',
    md: 'rounded-md',
    lg: 'rounded-lg',
    full: 'rounded-full'
  };

  $: selectClasses = [
    'block border focus:outline-none focus:ring-1 transition-colors duration-200',
    sizeClasses[size],
    roundedClasses[rounded],
    fullWidth ? 'w-full' : '',
    error ? themeClasses[theme].error : themeClasses[theme].base,
    error ? '' : themeClasses[theme].focus,
    themeClasses[theme].disabled,
    className
  ].filter(Boolean).join(' ');

  function handleChange(event: Event) {
    const target = event.target as HTMLSelectElement;
    value = target.value;
    dispatch('change', value);
  }

  function handleBlur(event: FocusEvent) {
    dispatch('blur', event);
  }

  function handleFocus(event: FocusEvent) {
    dispatch('focus', event);
  }
</script>

<div class="form-select-container">
  {#if label}
    <label 
      for={selectId} 
      class={`block text-sm font-medium mb-1 ${theme === 'dark' ? 'text-gray-300' : 'text-gray-700'} ${required ? 'after:content-["*"] after:text-red-500 after:ml-1' : ''}`}
    >
      {label}
    </label>
  {/if}
  
  <select
    {required}
    {disabled}
    {name}
    id={selectId}
    bind:value
    class={selectClasses}
    on:change={handleChange}
    on:blur={handleBlur}
    on:focus={handleFocus}
    {...$$restProps}
  >
    {#if placeholder}
      <option value="" disabled>{placeholder}</option>
    {/if}
    
    {#each options as option}
      <option 
        value={option.value} 
        disabled={option.disabled}
      >
        {option.label}
      </option>
    {/each}
  </select>
  
  {#if error}
    <div class={`mt-1 text-sm ${theme === 'dark' ? 'text-red-300' : 'text-red-600'}`}>
      <div class="flex items-center">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          class="mr-1.5 h-4 w-4 flex-shrink-0"
          viewBox="0 0 20 20"
          fill="currentColor"
        >
          <path
            fill-rule="evenodd"
            d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
            clip-rule="evenodd"
          />
        </svg>
        {error}
      </div>
    </div>
  {/if}
  
  {#if hint && !error}
    <div class={`mt-1 text-sm ${theme === 'dark' ? 'text-gray-400' : 'text-gray-500'}`}>
      {hint}
    </div>
  {/if}
</div>