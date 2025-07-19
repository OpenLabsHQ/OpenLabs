import type { Job, DeployJobResult } from '$lib/types/api';

/**
 * Extract range ID from a completed deployment job result
 * Handles various possible result structures from the API
 */
export function extractRangeIdFromJob(job: Job): string | null {
  if (!job.result || job.status !== 'complete') {
    return null;
  }

  const result = job.result as DeployJobResult;

  // Try different possible locations for the range ID
  if (result.range_id) {
    return String(result.range_id);
  }

  if (result.range?.id) {
    return String(result.range.id);
  }

  // Check if result is directly the range object
  if (typeof result === 'object' && 'id' in result) {
    return String(result.id);
  }

  // Check for nested range data
  if (result.data?.range_id) {
    return String(result.data.range_id);
  }

  if (result.data?.id) {
    return String(result.data.id);
  }

  // Check if the result has a range property with an id
  if (result.range_data?.id) {
    return String(result.range_data.id);
  }

  return null;
}

/**
 * Extract range information from a completed deployment job
 * Returns both ID and optional name/details
 */
export function extractRangeInfoFromJob(job: Job): { id: string; name?: string } | null {
  if (!job.result || job.status !== 'complete') {
    return null;
  }

  const result = job.result as DeployJobResult;
  const rangeId = extractRangeIdFromJob(job);

  if (!rangeId) {
    return null;
  }

  // Extract additional range information if available
  let rangeName: string | undefined;

  if (result.range?.name) {
    rangeName = result.range.name;
  } else if (result.name) {
    rangeName = result.name;
  } else if (result.data?.name) {
    rangeName = result.data.name;
  }

  return {
    id: rangeId,
    name: rangeName
  };
}

/**
 * Check if a job result indicates successful deployment
 */
export function isDeploymentSuccessful(job: Job): boolean {
  return job.status === 'complete' && extractRangeIdFromJob(job) !== null;
}

/**
 * Get a user-friendly status message for a deployment job
 */
export function getDeploymentStatusMessage(job: Job): string {
  switch (job.status) {
    case 'queued':
      return 'Your range deployment is queued and will start shortly...';
    case 'in_progress':
      return 'Building your range infrastructure in the cloud...';
    case 'complete':
      if (isDeploymentSuccessful(job)) {
        return 'Range deployment completed successfully!';
      }
      return 'Deployment completed but range information is not available.';
    case 'failed':
      return job.error_message || 'Range deployment failed.';
    case 'not_found':
      return 'Deployment job not found.';
    default:
      return 'Processing...';
  }
}

/**
 * Get a user-friendly status message for a destruction job
 */
export function getDestructionStatusMessage(job: Job): string {
  switch (job.status) {
    case 'queued':
      return 'Your range destruction is queued and will start shortly...';
    case 'in_progress':
      return 'Destroying range infrastructure and cleaning up resources...';
    case 'complete':
      return 'Range destruction completed successfully!';
    case 'failed':
      return job.error_message || 'Range destruction failed.';
    case 'not_found':
      return 'Destruction job not found.';
    default:
      return 'Processing...';
  }
}