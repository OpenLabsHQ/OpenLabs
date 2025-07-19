<script lang="ts">
  import { onMount } from 'svelte'
  import { goto } from '$app/navigation'
  import { auth } from '$lib/stores/auth'
  import LoadingSpinner from '$lib/components/LoadingSpinner.svelte'

  export let requireAuth = true
  export let redirectTo = '/'

  let loading = true

  onMount(() => {
    // Special handling for login page - don't redirect on auth failure
    const isLoginPage = window.location.pathname.includes('/login')

    if (requireAuth && !$auth.isAuthenticated) {
      goto(redirectTo)
    } else if (!requireAuth && $auth.isAuthenticated && !isLoginPage) {
      // Only redirect authenticated users away from non-login pages
      goto('/ranges')
    } else if (!requireAuth && $auth.isAuthenticated && isLoginPage) {
      // If on login page and authenticated, redirect to ranges
      goto('/ranges')
    }

    loading = false
  })
</script>

{#if loading}
  <div class="flex h-screen items-center justify-center bg-gray-900">
    <LoadingSpinner size="lg" color="white" message="Loading..." />
  </div>
{:else if (requireAuth && $auth.isAuthenticated) || (!requireAuth && !$auth.isAuthenticated)}
  <slot></slot>
{/if}
