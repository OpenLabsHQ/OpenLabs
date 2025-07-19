<script>
  import { page } from '$app/stores'
  import { formatErrorMessage } from '$lib/utils/error'

  // Safely format the error message to prevent [object Object]
  $: errorMessage = formatErrorMessage($page.error, 'Something went wrong')
</script>

<div
  class="flex min-h-screen flex-col items-center justify-center bg-gray-50 px-4"
>
  <div class="max-w-lg text-center">
    <!-- Error Number -->
    <h1 class="mb-4 text-9xl font-extrabold text-blue-600">
      {$page.status}
    </h1>

    <!-- Error Message -->
    <h2 class="mb-6 text-3xl font-bold text-gray-800">
      {#if $page.status === 404}
        Page Not Found
      {:else if $page.status === 403}
        Access Denied
      {:else if $page.status === 500}
        Server Error
      {:else}
        {errorMessage}
      {/if}
    </h2>

    <!-- Custom Message -->
    <p class="mb-8 text-lg text-gray-600">
      {#if $page.status === 404}
        The page you are looking for might have been removed, had its name
        changed, or is temporarily unavailable.
      {:else if $page.status === 403}
        You don't have permission to access this resource.
      {:else if $page.status === 500}
        Our servers are experiencing issues. Please try again later.
      {:else}
        An unexpected error occurred. We're working to fix it.
      {/if}
    </p>

    <!-- Network-themed graphic -->
    <div class="mb-16 flex w-full justify-center">
      <div class="relative inline-block h-64 w-64">
        <!-- Decorative circuit lines -->
        <div class="absolute inset-0 opacity-20">
          <div class="absolute top-1/2 left-0 h-1 w-full bg-blue-500"></div>
          <div class="absolute top-0 left-1/2 h-full w-1 bg-blue-500"></div>
          <div class="absolute top-1/4 left-0 h-1 w-full bg-blue-300"></div>
          <div class="absolute top-3/4 left-0 h-1 w-full bg-blue-300"></div>
          <div class="absolute top-0 left-1/4 h-full w-1 bg-blue-300"></div>
          <div class="absolute top-0 left-3/4 h-full w-1 bg-blue-300"></div>

          <!-- Decorative dots -->
          {#each [...Array(8).keys()] as i}
            <div
              class="absolute h-2 w-2 rounded-full bg-blue-500"
              style="top: {Math.random() * 100}%; left: {Math.random() * 100}%;"
              data-index={i}
            ></div>
          {/each}
        </div>

        <!-- Broken connection icon -->
        <div class="absolute inset-0 flex items-center justify-center">
          <svg
            class="h-32 w-32 text-blue-600"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="1.5"
              d="M18.364 5.636a9 9 0 010 12.728m0 0l-2.829-2.829m2.829 2.829L21 21M15.536 8.464a5 5 0 010 7.072m0 0l-2.829-2.829m-4.243 2.829a4.978 4.978 0 01-1.414-2.83m-1.414 5.658a9 9 0 01-2.167-9.238m7.824 2.167a1 1 0 111.414 1.414m-1.414-1.414L3 3m8.293 8.293l1.414 1.414"
            ></path>
          </svg>
        </div>
      </div>
    </div>

    <!-- Action Button - Clearly separated from the image -->
    <div class="mb-10 w-full">
      <a
        href="/"
        class="inline-flex items-center rounded-md border border-transparent bg-blue-600 px-6 py-3 text-base font-medium text-white shadow-sm transition-colors duration-200 hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:outline-none"
      >
        <svg
          class="mr-2 h-5 w-5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"
          ></path>
        </svg>
        Return Home
      </a>
    </div>
  </div>

  <!-- Footer -->
  <div class="mt-12 text-sm text-gray-500">
    <p>OpenLabs &copy; {new Date().getFullYear()}</p>
  </div>
</div>
