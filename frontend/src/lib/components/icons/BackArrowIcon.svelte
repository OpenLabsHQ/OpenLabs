<script lang="ts">
  export let size: 'sm' | 'md' | 'lg' = 'md'
  export let color: string = 'currentColor'
  export let ariaLabel: string = 'Go back'
  
  const sizeClasses = {
    sm: 'h-4 w-4',
    md: 'h-5 w-5', 
    lg: 'h-6 w-6'
  }
</script>

<svg 
  class={sizeClasses[size]} 
  fill="none" 
  stroke={color} 
  viewBox="0 0 24 24"
  aria-label={ariaLabel}
  role="img"
>
  <path 
    stroke-linecap="round" 
    stroke-linejoin="round" 
    stroke-width="2" 
    d="M10 19l-7-7m0 0l7-7m-7 7h18" 
  />
</svg>