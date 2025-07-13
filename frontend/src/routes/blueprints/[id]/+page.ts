// Only load the id from parameters - let the component fetch the data
import { error } from '@sveltejs/kit'
import type { PageLoad } from './$types'

// Mark this as a client-side load function
export const ssr = false

export const load = (({ params }) => {
  // Validate that the ID is present and reasonable
  if (!params.id) {
    throw error(404, 'Blueprint ID is required')
  }

  // Basic validation - blueprint IDs should be numeric or alphanumeric
  if (!/^[a-zA-Z0-9-_]+$/.test(params.id)) {
    throw error(404, 'Invalid blueprint ID format')
  }

  // Just return the blueprint ID
  return {
    blueprintId: params.id,
  }
}) satisfies PageLoad
