<script lang="ts">
  export let targets: Array<{ id: string; label: string }> = [
    { id: 'main-content', label: 'Skip to main content' },
    { id: 'main-navigation', label: 'Skip to navigation' },
    { id: 'footer', label: 'Skip to footer' }
  ];

  function skipTo(targetId: string) {
    const element = document.getElementById(targetId);
    if (element) {
      element.focus();
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }

  function handleKeyDown(event: KeyboardEvent, targetId: string) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      skipTo(targetId);
    }
  }
</script>

<!-- Skip to content links - only visible when focused -->
<div class="skip-to-content sr-only focus-within:not-sr-only">
  <div class="fixed top-0 left-0 z-50 bg-blue-600 text-white p-2 space-y-1">
    {#each targets as target}
      <button
        type="button"
        class="block w-full text-left px-3 py-2 text-sm font-medium hover:bg-blue-700 focus:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-white"
        on:click={() => skipTo(target.id)}
        on:keydown={(e) => handleKeyDown(e, target.id)}
      >
        {target.label}
      </button>
    {/each}
  </div>
</div>

<style>
  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
  }

  .focus-within\:not-sr-only:focus-within {
    position: static;
    width: auto;
    height: auto;
    padding: 0;
    margin: 0;
    overflow: visible;
    clip: auto;
    white-space: normal;
  }
</style>