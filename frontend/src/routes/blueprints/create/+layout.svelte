<script lang="ts">
  import { page } from '$app/stores'
  import { goto } from '$app/navigation'
  import Sidebar from '$lib/components/Sidebar.svelte'
  import { onMount, afterUpdate } from 'svelte'
  import { auth } from '$lib/stores/auth'

  // Define the wizard steps
  const steps = [
    { id: 'range', title: 'Range Details', path: '/blueprints/create' },
    { id: 'vpc', title: 'VPC Configuration', path: '/blueprints/create/vpc' },
    {
      id: 'subnet',
      title: 'Subnet Configuration',
      path: '/blueprints/create/subnet',
    },
    { id: 'host', title: 'Host Configuration', path: '/blueprints/create/host' },
    {
      id: 'review',
      title: 'Review & Create',
      path: '/blueprints/create/review',
    },
  ]

  // Get current step index
  $: currentPath = $page.url.pathname
  $: currentStepIndex = steps.findIndex((step) => step.path === currentPath)

  // Function to update connecting lines
  function updateStepLines() {
    const stepElements = document.querySelectorAll('.step-item')
    const stepLines = document.querySelectorAll('.step-line')
    const linesContainer = document.querySelector('.step-lines-container')

    if (!stepElements.length || !stepLines.length || !linesContainer) return

    const containerRect = linesContainer.getBoundingClientRect()

    // Calculate positions for all lines
    for (let i = 0; i < stepLines.length; i++) {
      const currentElement = stepElements[i]
      const nextElement = stepElements[i + 1]
      const line = stepLines[i]

      if (currentElement && nextElement) {
        // Get positions of the circle centers
        const rect1 = currentElement
          .querySelector('.step-circle')
          .getBoundingClientRect()
        const rect2 = nextElement
          .querySelector('.step-circle')
          .getBoundingClientRect()

        // Calculate center points
        const center1X = rect1.left + rect1.width / 2
        const center2X = rect2.left + rect2.width / 2

        // Calculate line position and width
        const lineLeft = center1X - containerRect.left
        const lineWidth = center2X - center1X

        // Position the line
        line.style.left = `${lineLeft}px`
        line.style.width = `${lineWidth}px`

        // For active step, set a data attribute to handle the half-line styling
        if (i === currentStepIndex) {
          line.setAttribute('data-half-width', lineWidth / 2 + 'px')
        } else {
          line.removeAttribute('data-half-width')
        }
      }
    }
  }

  // Update lines when component is mounted and on window resize
  let resizeTimer
  onMount(() => {
    if (!$auth.isAuthenticated) {
      goto('/login')
    }

    updateStepLines()

    window.addEventListener('resize', () => {
      // Debounce the resize event
      clearTimeout(resizeTimer)
      resizeTimer = setTimeout(() => {
        updateStepLines()
      }, 100)
    })

    return () => {
      window.removeEventListener('resize', updateStepLines)
      clearTimeout(resizeTimer)
    }
  })

  // Also update after the component has been updated
  afterUpdate(updateStepLines)
</script>

<svelte:head>
  <title>OpenLabs | Create Blueprint</title>
</svelte:head>

<div class="flex h-screen bg-gray-100">
  <!-- Fixed sidebar -->
  <div class="fixed inset-y-0 left-0 z-10 w-54">
    <Sidebar />
  </div>

  <!-- Main content with sidebar margin -->
  <div class="ml-54 flex flex-1 flex-col">
    <!-- Header with step indicator -->
    <div class="sticky top-0 z-5 border-b bg-white p-6 shadow-sm">
      <h1 class="mb-6 text-2xl font-bold">Create Range Blueprint</h1>

      <div class="relative">
        <!-- Step items container with aligned circles and titles -->
        <div class="step-container mb-4">
          {#each steps as step, i}
            <div
              class="step-item {i < currentStepIndex
                ? 'step-completed'
                : i === currentStepIndex
                  ? 'step-active'
                  : 'step-pending'}"
              data-step={i}
            >
              <div class="step-circle">
                {#if i < currentStepIndex}
                  ✓
                {:else}
                  {i + 1}
                {/if}
              </div>
              <div
                class="text-sm {i === currentStepIndex
                  ? 'font-semibold text-blue-600'
                  : 'text-gray-600'}"
              >
                {step.title}
              </div>
            </div>
          {/each}
        </div>

        <!-- Step lines container (positioned behind the circles) -->
        <div class="step-lines-container">
          {#each steps.slice(0, -1).map((s, index) => index) as i}
            <div
              class="step-line"
              class:step-completed={i < currentStepIndex}
              class:step-active={i === currentStepIndex}
              class:step-pending={i > currentStepIndex}
            ></div>
          {/each}
        </div>
      </div>
    </div>

    <!-- Main content area -->
    <div class="flex-1 overflow-y-auto bg-gray-100 p-10">
      <slot />
    </div>
  </div>
</div>

<style>
  .step-container {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    width: 100%;
    max-width: 1000px;
    margin: 0 auto;
    position: relative;
    z-index: 2;
  }

  .step-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    position: relative;
  }

  .step-circle {
    border-radius: 9999px;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 2rem;
    height: 2rem;
    font-size: 0.875rem;
    font-weight: 500;
    z-index: 2;
    margin-bottom: 0.75rem;
  }

  .step-active .step-circle {
    background-color: rgb(59, 130, 246);
    color: white;
  }

  .step-completed .step-circle {
    background-color: rgb(34, 197, 94);
    color: white;
  }

  .step-pending .step-circle {
    background-color: rgb(209, 213, 219);
    color: rgb(107, 114, 128);
  }

  .step-lines-container {
    position: absolute;
    top: 1rem;
    left: 0;
    right: 0;
    width: 100%;
    height: 4px;
    z-index: 0;
  }

  .step-line {
    height: 4px;
    position: absolute;
    top: 0;
  }

  .step-line.step-active {
    background-color: transparent;
    position: relative;
    overflow: visible;
  }

  .step-line.step-active::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 50%;
    height: 100%;
    background-color: rgb(59, 130, 246);
  }

  .step-line.step-active::after {
    content: '';
    position: absolute;
    top: 0;
    right: 0;
    width: 50%;
    height: 100%;
    background-color: rgb(209, 213, 219);
  }

  .step-line.step-completed {
    background-color: rgb(34, 197, 94);
  }

  .step-line.step-pending {
    background-color: rgb(209, 213, 219);
  }

  /* Custom radio button and checkbox styles */
  :global(input[type='radio']) {
    -webkit-appearance: none;
    appearance: none;
    background-color: #fff;
    margin: 0;
    width: 1.2em;
    height: 1.2em;
    border: 1.5px solid #d1d5db;
    border-radius: 50%;
    display: grid;
    place-content: center;
  }

  :global(input[type='radio']::before) {
    content: '';
    width: 0.65em;
    height: 0.65em;
    border-radius: 50%;
    transform: scale(0);
    transition: 120ms transform ease-in-out;
    box-shadow: inset 1em 1em #3b82f6;
  }

  :global(input[type='radio']:checked::before) {
    transform: scale(1);
  }

  :global(input[type='radio']:focus) {
    outline: 2px solid rgba(59, 130, 246, 0.5);
    outline-offset: 2px;
  }

  :global(input[type='checkbox']) {
    -webkit-appearance: none;
    appearance: none;
    background-color: #fff;
    margin: 0;
    width: 1.2em;
    height: 1.2em;
    border: 1.5px solid #d1d5db;
    border-radius: 0.25em;
    display: grid;
    place-content: center;
  }

  :global(input[type='checkbox']::before) {
    content: '';
    width: 0.65em;
    height: 0.65em;
    transform: scale(0);
    transition: 120ms transform ease-in-out;
    box-shadow: inset 1em 1em #3b82f6;
    transform-origin: center;
    clip-path: polygon(14% 44%, 0 65%, 50% 100%, 100% 16%, 80% 0%, 43% 62%);
  }

  :global(input[type='checkbox']:checked::before) {
    transform: scale(1);
  }

  :global(input[type='checkbox']:focus) {
    outline: 2px solid rgba(59, 130, 246, 0.5);
    outline-offset: 2px;
  }

  /* Custom select styles */
  :global(select) {
    appearance: none;
    background-image: url("data:image/svg+xml;charset=utf-8,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3E%3Cpath stroke='%236B7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3E%3C/svg%3E");
    background-position: right 0.5rem center;
    background-repeat: no-repeat;
    background-size: 1.5em 1.5em;
    padding-right: 2.5rem;
  }

  :global(select:focus) {
    outline: 2px solid rgba(59, 130, 246, 0.5);
    outline-offset: 2px;
    border-color: #3b82f6;
  }
</style>
