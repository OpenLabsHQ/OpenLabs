<script lang="ts">
  import { onMount } from 'svelte'
  import { auth } from '$lib/stores/auth'
  import { goto } from '$app/navigation'

  onMount(async () => {
    // If user is already authenticated, redirect to ranges
    if ($auth.isAuthenticated) {
      goto('/ranges')
      return
    }
  })

  function handleGetStarted() {
    goto($auth.isAuthenticated ? '/ranges' : '/signup')
  }

  function handleLogout() {
    auth.logout()
  }
</script>

<header
  class="fixed top-0 right-0 left-0 z-50 border-b border-gray-800/75 bg-gray-900 text-sm font-medium text-white"
>
  <div
    class="mx-auto flex h-16 max-w-screen-xl items-center justify-between px-4 sm:px-6 lg:px-8"
  >
    <nav class="hidden md:flex md:items-center md:gap-4 lg:gap-8">
      <a href="https://github.com/OpenLabsHQ" class="font-bold">OpenLabsHQ</a>
      <a
        href="https://docs.openlabs.sh"
        class="font-bold"
        target="_blank"
        rel="noopener noreferrer">Documentation</a
      >
      {#if $auth.isAuthenticated}
        <a href="/ranges" class="font-bold">My Ranges</a>
      {/if}
    </nav>
    <div class="hidden md:flex md:items-center md:gap-4 lg:gap-8">
      {#if $auth.isAuthenticated}
        <span class="text-gray-300">Hello, User</span>
        <button on:click={handleLogout} class="text-red-400 hover:text-red-300"
          >Logout</button
        >
      {:else}
        <a href="/signup" class="hover:text-gray-300">Sign Up</a>
        <a href="/login" class="hover:text-gray-300">Login</a>
      {/if}
      <a
        href="https://github.com/OpenLabsHQ/Setup"
        target="_blank"
        rel="noreferrer"
      >
        <span class="sr-only">GitHub</span>
        <svg
          fill="currentColor"
          viewBox="0 0 24 24"
          aria-hidden="true"
          class="h-5 w-5"
        >
          <path
            fill-rule="evenodd"
            d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
            clip-rule="evenodd"
          ></path>
        </svg>
      </a>
    </div>
  </div>
</header>

<div class="fixed inset-0 flex flex-col bg-gray-900 pt-16">
  <div class="flex flex-1 items-center justify-center">
    <div class="px-4 text-center">
      <h1
        class="bg-gradient-to-r from-pink-500 via-red-500 to-yellow-500 bg-clip-text text-4xl font-extrabold tracking-tighter text-transparent uppercase sm:text-5xl lg:text-7xl"
      >
        OpenLabs
      </h1>
      <p class="mx-auto mt-8 max-w-2xl text-xl font-bold text-white">
        Open source platform to design and create cyber security labs.
      </p>

      <div class="mt-8">
        <button
          on:click={handleGetStarted}
          class="rounded-md bg-indigo-600 px-6 py-3 font-medium text-white shadow-sm transition-colors hover:bg-indigo-700"
        >
          {$auth.isAuthenticated ? 'Go to My Ranges' : 'Get Started'}
        </button>
      </div>
    </div>
  </div>

  <footer
    class="w-full border-t border-gray-800 bg-gray-900 py-4 text-center text-white"
  >
    <p>&copy; {new Date().getFullYear()} OpenLabs. All rights reserved.</p>
  </footer>
</div>

<style>
  a {
    font-family:
      Inter,
      ui-sans-serif,
      system-ui,
      sans-serif,
      Apple Color Emoji,
      Segoe UI Emoji,
      Segoe UI Symbol,
      Noto Color Emoji;
  }
</style>
