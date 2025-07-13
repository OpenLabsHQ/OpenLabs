<script lang="ts">
  export let size: string = "h-16 w-16";
  export let color: string = "text-blue-400";
  export let ariaLabel: string = 'Workspace';
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
  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/>
</svg>