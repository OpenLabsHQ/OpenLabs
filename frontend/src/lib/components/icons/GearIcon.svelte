<script lang="ts">
  export let size: 'sm' | 'md' | 'lg' | 'xl' | '2xl' = 'md'
  export let color: string = 'currentColor'
  export let ariaLabel: string = 'Settings'
  export let animate: boolean = false
  export let reverse: boolean = false
  export let speed: 'normal' | 'slow' = 'normal'
  
  const sizeClasses = {
    sm: 'h-4 w-4',
    md: 'h-5 w-5', 
    lg: 'h-6 w-6',
    xl: 'h-12 w-12',
    '2xl': 'h-20 w-20'
  }
  
  $: animationClass = animate ? 
    (reverse ? 
      (speed === 'slow' ? 'animate-spin-reverse-slow' : 'animate-spin-reverse') :
      (speed === 'slow' ? 'animate-spin-slow-slower' : 'animate-spin-slow')
    ) : ''
</script>

<svg 
  class="{sizeClasses[size]} {animationClass} {$$props.class || ''}" 
  fill="none" 
  stroke={color} 
  viewBox="0 0 24 24"
  aria-label={ariaLabel}
  role="img"
  stroke-width="1"
>
  <path d="M12 15a3 3 0 100-6 3 3 0 000 6z" />
  <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z" />
</svg>

<style>
  @keyframes spin-slow {
    from {
      transform: rotate(0deg);
    }
    to {
      transform: rotate(360deg);
    }
  }
  
  @keyframes spin-reverse {
    from {
      transform: rotate(360deg);
    }
    to {
      transform: rotate(0deg);
    }
  }
  
  .animate-spin-slow {
    animation: spin-slow 10s linear infinite;
  }
  
  .animate-spin-reverse {
    animation: spin-reverse 10s linear infinite;
  }
  
  .animate-spin-slow-slower {
    animation: spin-slow 15s linear infinite;
  }
  
  .animate-spin-reverse-slow {
    animation: spin-reverse 15s linear infinite;
  }
</style>