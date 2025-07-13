<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import Button from './Button.svelte';
  import { loadingStore } from '$lib/stores/loading';

  const dispatch = createEventDispatcher<{
    click: MouseEvent;
  }>();

  export let variant: 'primary' | 'secondary' | 'danger' | 'success' | 'ghost' = 'primary';
  export let size: 'sm' | 'md' | 'lg' = 'md';
  export let disabled: boolean = false;
  export let fullWidth: boolean = false;
  export let type: 'button' | 'submit' | 'reset' = 'button';
  export let href: string | undefined = undefined;
  export let loadingKey: string | undefined = undefined;
  export let loadingText: string = 'Loading...';
  
  // Allow custom classes to be passed
  let className = '';
  export { className as class };

  $: loadingState = loadingKey ? $loadingStore[loadingKey] : null;
  $: isLoading = loadingState?.isLoading ?? false;
  $: displayText = isLoading && loadingText ? loadingText : undefined;

  function handleClick(event: MouseEvent) {
    if (isLoading) {
      event.preventDefault();
      return;
    }
    dispatch('click', event);
  }
</script>

<Button
  {variant}
  {size}
  disabled={disabled || isLoading}
  loading={isLoading}
  {fullWidth}
  {type}
  {href}
  class={className}
  on:click={handleClick}
  {...$$restProps}
>
  {#if displayText && isLoading}
    {displayText}
  {:else}
    <slot />
  {/if}
</Button>