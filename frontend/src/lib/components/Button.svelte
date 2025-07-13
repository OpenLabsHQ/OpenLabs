<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import LoadingSpinner from './LoadingSpinner.svelte';
  
  const dispatch = createEventDispatcher<{
    click: MouseEvent;
  }>();

  export let variant: 'primary' | 'secondary' | 'danger' | 'success' | 'ghost' = 'primary';
  export let size: 'sm' | 'md' | 'lg' = 'md';
  export let disabled = false;
  export let loading = false;
  export let fullWidth = false;
  export let type: 'button' | 'submit' | 'reset' = 'button';
  export let href: string | undefined = undefined;
  
  // Allow custom classes to be passed
  let className = '';
  export { className as class };

  $: isDisabled = disabled || loading;

  const baseClasses = 'inline-flex items-center justify-center font-medium rounded focus:outline-none focus:ring-2 focus:ring-offset-2 transition-colors duration-200 ease-in-out';

  const variantClasses = {
    primary: 'bg-blue-500 text-white hover:bg-blue-700 focus:ring-blue-500 disabled:bg-blue-300',
    secondary: 'border border-gray-300 bg-white text-gray-700 hover:bg-gray-50 focus:ring-blue-500 disabled:bg-gray-100 disabled:text-gray-400',
    danger: 'bg-red-500 text-white hover:bg-red-600 focus:ring-red-500 disabled:bg-red-300',
    success: 'bg-green-500 text-white hover:bg-green-600 focus:ring-green-500 disabled:bg-green-300',
    ghost: 'text-gray-700 hover:bg-gray-100 focus:ring-blue-500 disabled:text-gray-400 disabled:hover:bg-transparent'
  };

  const sizeClasses = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2 text-base',
    lg: 'px-6 py-3 text-lg'
  };

  $: classes = [
    baseClasses,
    variantClasses[variant],
    sizeClasses[size],
    fullWidth ? 'w-full' : '',
    isDisabled ? 'cursor-not-allowed' : 'cursor-pointer',
    className
  ].filter(Boolean).join(' ');

  function handleClick(event: MouseEvent) {
    if (isDisabled) {
      event.preventDefault();
      return;
    }
    dispatch('click', event);
  }
</script>

{#if href && !isDisabled}
  <a
    {href}
    class={classes}
    on:click={handleClick}
    {...$$restProps}
  >
    {#if loading}
      <LoadingSpinner size="sm" class="mr-2" />
    {/if}
    <slot />
  </a>
{:else}
  <button
    {type}
    class={classes}
    disabled={isDisabled}
    on:click={handleClick}
    {...$$restProps}
  >
    {#if loading}
      <LoadingSpinner size="sm" class="mr-2" />
    {/if}
    <slot />
  </button>
{/if}