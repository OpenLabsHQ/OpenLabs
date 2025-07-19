<script lang="ts">
  export let size: 'sm' | 'md' | 'lg' = 'md'
  export let color: string = 'currentColor'
  export let ariaLabel: string = 'Time'
  
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
    d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" 
  />
</svg>