<script lang="ts">
  import { createEventDispatcher } from 'svelte';

  const dispatch = createEventDispatcher<{
    input: string;
    change: string;
    blur: FocusEvent;
    focus: FocusEvent;
  }>();

  export let type: 'text' | 'email' | 'password' | 'number' | 'tel' | 'url' = 'text';
  export let value = '';
  export let placeholder = '';
  export let label = '';
  export let id = '';
  export let name = '';
  export let required = false;
  export let disabled = false;
  export let readonly = false;
  export let autocomplete = '';
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
  $: inputId = id || `input-${Math.random().toString(36).substr(2, 9)}`;

  const themeClasses = {
    light: {
      base: 'border-gray-300 bg-white text-gray-900 placeholder-gray-500',
      focus: 'focus:border-blue-500 focus:ring-blue-500',
      error: 'border-red-300 bg-red-50 text-red-900 placeholder-red-400 focus:border-red-500 focus:ring-red-500',
      disabled: 'disabled:bg-gray-50 disabled:text-gray-500 disabled:cursor-not-allowed'
    },
    dark: {
      base: 'border-gray-700 bg-gray-800 text-white placeholder-gray-500',
      focus: 'focus:border-indigo-500 focus:ring-indigo-500',
      error: 'border-red-500 bg-red-900/50 text-red-300 placeholder-red-400 focus:border-red-500 focus:ring-red-500',
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

  $: inputClasses = [
    'block border focus:outline-none focus:ring-1 transition-colors duration-200',
    sizeClasses[size],
    roundedClasses[rounded],
    fullWidth ? 'w-full' : '',
    error ? themeClasses[theme].error : themeClasses[theme].base,
    error ? '' : themeClasses[theme].focus,
    themeClasses[theme].disabled,
    className
  ].filter(Boolean).join(' ');

  function handleInput(event: Event) {
    const target = event.target as HTMLInputElement;
    value = target.value;
    dispatch('input', value);
  }

  function handleChange(event: Event) {
    const target = event.target as HTMLInputElement;
    dispatch('change', target.value);
  }

  function handleBlur(event: FocusEvent) {
    dispatch('blur', event);
  }

  function handleFocus(event: FocusEvent) {
    dispatch('focus', event);
  }
</script>

<div class="form-input-container">
  {#if label}
    <label 
      for={inputId} 
      class={`block text-sm font-medium mb-1 ${theme === 'dark' ? 'text-gray-300' : 'text-gray-700'} ${required ? 'after:content-["*"] after:text-red-500 after:ml-1' : ''}`}
    >
      {label}
    </label>
  {/if}
  
  <input
    {type}
    {placeholder}
    {required}
    {disabled}
    {readonly}
    {autocomplete}
    {name}
    id={inputId}
    {value}
    class={inputClasses}
    on:input={handleInput}
    on:change={handleChange}
    on:blur={handleBlur}
    on:focus={handleFocus}
    {...$$restProps}
  />
  
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