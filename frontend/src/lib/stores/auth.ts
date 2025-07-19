import { writable } from 'svelte/store'
import logger from '$lib/utils/logger'

/**
 * Authentication is managed using HTTP-only cookies.
 *
 * Security advantages over localStorage:
 * - Not accessible to JavaScript, protecting against XSS attacks
 * - Can be set with HttpOnly, Secure, and SameSite flags
 * - Server controls expiration
 * - More secure against client-side attacks
 *
 * How it works:
 * - The server sets the JWT in an HTTP-only cookie upon successful login
 * - The cookie is automatically sent with every request to the same domain
 * - Authentication state is inferred from API responses, not by checking token presence
 */

interface AuthStore {
  isAuthenticated: boolean
  user?: {
    id?: string
    name?: string
    email?: string
    admin?: boolean
  }
}

// Load stored auth data from localStorage if available
const loadStoredAuthData = (): AuthStore => {
  if (typeof window !== 'undefined') {
    const storedData = localStorage.getItem('auth_data')
    if (storedData) {
      try {
        return JSON.parse(storedData)
      } catch (e) {
        logger.error('Failed to parse stored auth data', 'auth.loadStoredAuthData', e)
      }
    }
  }

  // Default initial state
  return {
    isAuthenticated: false,
    user: undefined,
  }
}

// Create auth store with initial state
const createAuthStore = () => {
  // Start with stored data or default
  const initialState: AuthStore = loadStoredAuthData()

  const { subscribe, set, update } = writable<AuthStore>(initialState)

  // Subscribe to store changes and save to localStorage
  if (typeof window !== 'undefined') {
    subscribe((state) => {
      localStorage.setItem('auth_data', JSON.stringify(state))
    })
  }

  return {
    subscribe,

    // Set auth state after login/registration (token is stored in HTTP-only cookie by the server)
    setAuth: (userData = {}) => {
      set({
        isAuthenticated: true,
        user: userData,
      })
    },

    // Update authentication state without affecting user data
    updateAuthState: (isAuthenticated: boolean) => {
      update((state) => ({
        ...state,
        isAuthenticated,
      }))
    },

    // Update user information
    updateUser: (userData = {}) => {
      update((state) => ({
        ...state,
        user: {
          ...state.user,
          ...userData,
        },
      }))
    },

    // Clear auth state on logout
    logout: async () => {
      // Import dynamically to avoid circular dependencies
      const { authApi } = await import('$lib/api')
      const { goto } = await import('$app/navigation')

      // Call the logout API to clear the cookie on the server
      await authApi.logout()

      // Clear localStorage
      if (typeof window !== 'undefined') {
        localStorage.removeItem('auth_data')
      }

      set({
        isAuthenticated: false,
        user: undefined,
      })

      // Redirect to landing page after logout
      goto('/')
    },
  }
}

// Export store singleton
export const auth = createAuthStore()
