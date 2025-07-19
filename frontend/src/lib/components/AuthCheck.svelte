<script lang="ts">
  import { onMount } from 'svelte'
  import { auth } from '$lib/stores/auth'
  import { authApi } from '$lib/api'

  export let onAuthSuccess: () => void = () => {}
  export let onAuthFailure: () => void = () => {}

  onMount(async () => {
    // First, check if we're already authenticated in the store
    // If yes, keep that state and still verify in the background
    let localAuth = $auth.isAuthenticated

    if (localAuth) {
      // Call success right away to avoid visual flicker
      onAuthSuccess()
    }

    // Always verify with the API, but don't block UI if already authenticated
    try {
      const result = await authApi.getCurrentUser()

      if (result.data) {
        // Successfully verified authentication
        // Include the user data when setting auth state
        auth.setAuth(result.data.user)

        // Only call success if we weren't already authenticated
        if (!localAuth) {
          onAuthSuccess()
        }
      } else if (
        result.isAuthError === true ||
        result.status === 401 ||
        result.status === 403
      ) {
        // This is definitely an auth error
        auth.logout()
        onAuthFailure()
      } else {
        // Already handled if previously authenticated
        if (!localAuth) {
          onAuthFailure()
        }
      }
    } catch {
      // Only call failure if we weren't already authenticated
      if (!localAuth) {
        onAuthFailure()
      }
    }
  })
</script>
