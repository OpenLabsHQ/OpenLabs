import { error } from '@sveltejs/kit'
import type { PageLoad } from './$types'

// This load function is needed for server-side rendering
// The actual data fetching happens in the component
export const load: PageLoad = async ({ params }) => {
  if (!params.id) {
    throw error(404, 'Range ID is required')
  }

  // Basic validation - range IDs should be numeric or alphanumeric
  if (!/^[a-zA-Z0-9-_]+$/.test(params.id)) {
    throw error(404, 'Invalid range ID format')
  }

  // Return the range ID for use in the component
  return {
    rangeId: params.id
  }
}