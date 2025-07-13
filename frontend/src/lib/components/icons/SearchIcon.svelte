<script lang="ts">
  export let size: string = "h-16 w-16";
  export let color: string = "text-blue-400";
  export let ariaLabel: string = 'Search';
  export let decorative: boolean = false;
</script>

<svg 
  class="mx-auto {size} {color}" 
  fill="none" 
  stroke="currentColor" 
  viewBox="0 0 24 24"
  aria-label={decorative ? undefined : ariaLabel}
  aria-hidden={decorative ? 'true' : undefined}
  role={decorative ? undefined : 'img'}
>
  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
</svg>