/**
 * Time utility functions for job tracking and elapsed time calculations
 */

/**
 * Calculate elapsed time since a given timestamp
 * @param timestamp - ISO string timestamp
 * @returns elapsed time in seconds
 */
export function calculateElapsedSeconds(timestamp: string): number {
  const startTime = new Date(timestamp).getTime();
  const currentTime = Date.now();
  
  if (isNaN(startTime)) {
    return 0;
  }
  
  return Math.floor((currentTime - startTime) / 1000);
}

/**
 * Calculate elapsed time for a job based on its status and timestamps
 * @param job - Job object with timestamps
 * @returns elapsed time in seconds
 */
export function calculateJobElapsedTime(job: {
  status: string;
  enqueue_time?: string;
  start_time?: string;
  finish_time?: string;
}): number {
  // If job is finished, calculate total duration
  if (job.finish_time && (job.start_time || job.enqueue_time)) {
    const startTime = job.start_time || job.enqueue_time;
    const finishTime = new Date(job.finish_time).getTime();
    const beginTime = new Date(startTime!).getTime();
    
    if (!isNaN(finishTime) && !isNaN(beginTime)) {
      return Math.floor((finishTime - beginTime) / 1000);
    }
  }
  
  // For active jobs, calculate elapsed time from start or queue time
  const referenceTime = job.start_time || job.enqueue_time;
  
  if (!referenceTime) {
    return 0;
  }
  
  return calculateElapsedSeconds(referenceTime);
}

/**
 * Format elapsed time in a human-readable format
 * @param seconds - elapsed time in seconds
 * @returns formatted time string
 */
export function formatElapsedTime(seconds: number): string {
  if (seconds < 60) {
    return `${seconds}s`;
  }
  
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  
  if (minutes < 60) {
    return `${minutes}m ${remainingSeconds}s`;
  }
  
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  
  return `${hours}h ${remainingMinutes}m ${remainingSeconds}s`;
}

/**
 * Create a timer that updates elapsed time based on a reference timestamp
 * @param timestamp - reference timestamp to calculate elapsed time from
 * @param callback - function to call with updated elapsed time
 * @returns cleanup function to stop the timer
 */
export function createElapsedTimer(
  timestamp: string,
  callback: (elapsedSeconds: number) => void
): () => void {
  // Calculate initial elapsed time
  let elapsedSeconds = calculateElapsedSeconds(timestamp);
  callback(elapsedSeconds);
  
  // Update every second
  const interval = setInterval(() => {
    elapsedSeconds = calculateElapsedSeconds(timestamp);
    callback(elapsedSeconds);
  }, 1000);
  
  // Return cleanup function
  return () => clearInterval(interval);
}