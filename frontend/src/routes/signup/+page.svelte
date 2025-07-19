<script lang="ts">
  import { onMount } from 'svelte'
  import { goto } from '$app/navigation'
  import { authApi } from '$lib/api'
  import { auth } from '$lib/stores/auth'
  import { AuthGuard, FormInput, Button, ErrorMessage } from '$lib/components'

  let name = ''
  let email = ''
  let password = ''
  let confirmPassword = ''
  let error = ''
  let isLoading = false

  onMount(() => {
    if ($auth.isAuthenticated) {
      goto('/ranges')
    }
  })

  async function handleSignup() {
    // Validate form
    if (!name || !email || !password) {
      error = 'All fields are required'
      return
    }

    if (password !== confirmPassword) {
      error = 'Passwords do not match'
      return
    }

    if (password.length < 8) {
      error = 'Password must be at least 8 characters'
      return
    }

    error = ''
    isLoading = true

    try {
      // Register the user
      const registerResult = await authApi.register({ name, email, password })

      if (registerResult.error) {
        // Handle error object or string appropriately
        if (typeof registerResult.error === 'object') {
          // For validation errors (usually 422 responses)
          error = JSON.stringify(registerResult.error)
        } else {
          error = registerResult.error
        }
        return
      }

      // Auto-login after successful registration
      const loginResult = await authApi.login({ email, password })

      if (loginResult.error) {
        error =
          'Registration successful, but login failed. Please go to login page.'
        return
      }

      if (loginResult.data) {
        // With HTTP-only cookies, we don't receive the token directly
        // Just update auth state and redirect
        auth.setAuth()
        goto('/ranges')
      }
    } catch (err) {
      error = err instanceof Error ? err.message : 'Registration failed'
    } finally {
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
          Create your account
        </h2>
        <p class="mt-2 text-center text-sm text-gray-400">
          Or
          <a
            href="/login"
            class="font-medium text-indigo-400 hover:text-indigo-300"
          >
            sign in to your existing account
          </a>
        </p>
      </div>

      <form class="mt-8 space-y-6" on:submit|preventDefault={handleSignup}>
        <div class="space-y-4">
          <FormInput
            type="text"
            name="name"
            required
            bind:value={name}
            placeholder="Full name"
            theme="dark"
            rounded="md"
          />
          
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
            autocomplete="new-password"
            required
            bind:value={password}
            placeholder="Password"
            theme="dark"
            rounded="md"
          />
          
          <FormInput
            type="password"
            name="confirm-password"
            autocomplete="new-password"
            required
            bind:value={confirmPassword}
            placeholder="Confirm password"
            theme="dark"
            rounded="md"
          />
        </div>

        {#if error}
          <ErrorMessage 
            message={error}
            theme="dark"
            variant="inline"
            class="text-center"
          />
        {/if}

        <div class="mt-1 rounded-md border border-gray-700 bg-gray-800 p-3">
          <div class="flex items-center text-sm">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="mr-2 h-5 w-5 text-indigo-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <span class="text-gray-300">
              We recommend using a strong password as it will be used to encrypt
              cloud provider secrets.
            </span>
          </div>
        </div>

        <div>
          <Button
            type="submit"
            disabled={isLoading}
            loading={isLoading}
            variant="primary"
            fullWidth
            class="bg-indigo-600 hover:bg-indigo-700 focus:ring-indigo-500"
          >
            {isLoading ? 'Creating account...' : 'Create account'}
          </Button>
        </div>
      </form>
    </div>
  </div>
</AuthGuard>
