<script lang="ts">
  import { onMount } from 'svelte'
  import { goto } from '$app/navigation'
  import { authApi } from '$lib/api'
  import { auth } from '$lib/stores/auth'
  import { AuthGuard, FormInput, Button, ErrorMessage } from '$lib/components'
  import logger from '$lib/utils/logger'

  let email = ''
  let password = ''
  let error = ''
  let isLoading = false

  // Redirect if already authenticated
  onMount(() => {
    if ($auth.isAuthenticated) {
      goto('/ranges')
    }
  })

  async function handleLogin() {
    if (!email || !password) {
      error = 'Email and password are required'
      return
    }

    error = ''
    isLoading = true

    try {
      const result = await authApi.login({ email, password })

      if (result.error) {
        // Display the server error message and prevent redirection
        error = result.error || 'Invalid email or password'
        isLoading = false
        return // Important - stop execution here
      }

      // Only set auth and redirect if login was successful
      if (result.data) {
        // After login, fetch user data to get all user details including ID
        const userInfo = await authApi.getCurrentUser();
        if (userInfo.data?.user) {
          auth.setAuth(userInfo.data.user);
        } else {
          // Fallback if /users/me endpoint fails
          auth.setAuth(result.data.user || {});
        }
        goto('/ranges')
      } else {
        // Fallback error if no data and no error
        error = 'Login failed. Please check your credentials.'
        isLoading = false
      }
    } catch (err) {
      logger.error('Login exception', 'login', err)
      error = err instanceof Error ? err.message : 'Login failed'
      isLoading = false
    }
  }
</script>

<AuthGuard requireAuth={false} redirectTo="/">
  <div
    class="flex min-h-screen items-center justify-center bg-gray-900 px-4 py-12 sm:px-6 lg:px-8"
  >
    <div class="w-full max-w-md space-y-8">
      <div>
        <h2 class="mt-6 text-center text-3xl font-extrabold text-white">
          Sign in to your account
        </h2>
        <p class="mt-2 text-center text-sm text-gray-400">
          Or
          <a
            href="/signup"
            class="font-medium text-indigo-400 hover:text-indigo-300"
          >
            create a new account
          </a>
        </p>
      </div>

      <form class="mt-8 space-y-6" on:submit|preventDefault={handleLogin}>
        <div class="space-y-4">
          <FormInput
            type="email"
            name="email"
            autocomplete="email"
            required
            bind:value={email}
            placeholder="Email address"
            theme="dark"
            rounded="md"
          />
          
          <FormInput
            type="password"
            name="password"
            autocomplete="current-password"
            required
            bind:value={password}
            placeholder="Password"
            theme="dark"
            rounded="md"
          />
        </div>

        {#if error}
          <ErrorMessage 
            message={error}
            theme="dark"
            variant="banner"
          />
        {/if}

        <div>
          <Button
            type="submit"
            disabled={isLoading}
            loading={isLoading}
            variant="primary"
            fullWidth
            class="bg-indigo-600 hover:bg-indigo-700 focus:ring-indigo-500"
          >
            {isLoading ? 'Signing in...' : 'Sign in'}
          </Button>
        </div>
      </form>
    </div>
  </div>
</AuthGuard>
