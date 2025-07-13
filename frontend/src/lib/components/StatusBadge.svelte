<script lang="ts">
  export let variant: 'primary' | 'success' | 'warning' | 'danger' | 'gray' | 'info' = 'primary';
  export let size: 'sm' | 'md' | 'lg' = 'md';
  export let rounded: 'normal' | 'full' = 'full';
  export let icon: boolean = false;
  
  // Allow custom classes to be passed
  let className = '';
  export { className as class };

  const baseClasses = 'inline-flex items-center font-medium';

  const variantClasses = {
    primary: 'bg-blue-100 text-blue-800',
    success: 'bg-green-100 text-green-800',
    warning: 'bg-yellow-100 text-yellow-800',
    danger: 'bg-red-100 text-red-800',
    gray: 'bg-gray-100 text-gray-800',
    info: 'bg-indigo-100 text-indigo-800'
  };

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-0.5 text-xs',
    lg: 'px-3 py-1 text-sm'
  };

  const roundedClasses = {
    normal: 'rounded',
    full: 'rounded-full'
  };

  $: classes = [
    baseClasses,
    variantClasses[variant],
    sizeClasses[size],
    roundedClasses[rounded],
    className
  ].filter(Boolean).join(' ');
</script>

<span class={classes}>
  {#if icon}
    <slot name="icon" />
  {/if}
  <slot />
</span>