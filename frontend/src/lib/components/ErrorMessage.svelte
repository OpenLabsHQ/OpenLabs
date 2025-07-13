<script lang="ts">
  export let message: string;
  export let theme: 'light' | 'dark' = 'light';
  export let variant: 'inline' | 'banner' | 'card' = 'inline';
  export let dismissible = false;
  export let onDismiss: (() => void) | undefined = undefined;

  // Allow custom classes to be passed
  let className = '';
  export { className as class };

  const themeClasses = {
    light: {
      inline: 'text-red-600',
      banner: 'bg-red-50 border-red-200 text-red-700',
      card: 'bg-red-50 border-red-200 text-red-700'
    },
    dark: {
      inline: 'text-red-300',
      banner: 'bg-red-900/50 border-red-500 text-red-300',
      card: 'bg-red-900/50 border-red-500 text-red-300'
    }
  };

  const variantClasses = {
    inline: 'text-sm',
    banner: 'rounded-md border px-4 py-3',
    card: 'rounded-lg border p-4 shadow-sm'
  };

  $: classes = [
    variantClasses[variant],
    themeClasses[theme][variant],
    className
  ].filter(Boolean).join(' ');

  function handleDismiss() {
    if (onDismiss) {
      onDismiss();
    }
  }
</script>

{#if message}
  <div class={classes} role="alert">
    <div class="flex items-start">
      <svg
        xmlns="http://www.w3.org/2000/svg"
        class={`flex-shrink-0 ${variant === 'inline' ? 'mr-1.5 h-4 w-4' : 'mr-3 h-5 w-5'}`}
        viewBox="0 0 20 20"
        fill="currentColor"
      >
        <path
          fill-rule="evenodd"
          d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
          clip-rule="evenodd"
        />
      </svg>
      
      <div class="flex-1">
        {message}
      </div>
      
      {#if dismissible && onDismiss}
        <button
          type="button"
          class={`ml-2 flex-shrink-0 ${theme === 'dark' ? 'text-red-300 hover:text-red-100' : 'text-red-500 hover:text-red-700'} focus:outline-none`}
          on:click={handleDismiss}
          aria-label="Dismiss error"
        >
          <svg
            class="h-4 w-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
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
  </div>
{/if}