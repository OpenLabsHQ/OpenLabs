// Configuration file for environment-specific settings

// Dynamic API URL that can be set at runtime or build time
// This allows setting the API URL even after the app is built
const getApiUrl = (): string => {
  // In development mode, always use empty string (relative URLs)
  // This ensures Vite's proxy is used
  if (typeof import.meta !== 'undefined' && import.meta.env.DEV === true) {
    return ''
  }

  // In production, check for runtime config first
  if (typeof window !== 'undefined' && (window as { __API_URL__?: string }).__API_URL__) {
    return (window as { __API_URL__: string }).__API_URL__
  }

  // During build, environment variables are accessed via import.meta.env
  // https://vitejs.dev/guide/env-and-mode.html
  if (typeof import.meta !== 'undefined' && import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL
  }

  // Default fallback - empty string means use same origin
  return ''
}

export const config = {
  apiUrl: getApiUrl(),
  // Add other configuration options here as needed
  appName: 'OpenLabsX',
  version: '0.0.1',
}

export default config
