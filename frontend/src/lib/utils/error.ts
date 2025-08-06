/**
 * Error utility functions to ensure proper error message formatting
 */
import logger from './logger'

/**
 * Converts any error value to a user-friendly string message
 * Prevents "[object Object]" from being displayed to users
 * @param error - Any error value (Error, string, object, etc.)
 * @param fallbackMessage - Default message if error cannot be converted
 * @returns A user-friendly error message string
 */
export function formatErrorMessage(error: unknown, fallbackMessage: string = 'An unexpected error occurred'): string {
  // If it's already a string, return it
  if (typeof error === 'string') {
    return error.trim() || fallbackMessage
  }

  // If it's an Error object, use its message
  if (error instanceof Error) {
    return error.message.trim() || fallbackMessage
  }

  // If it's an object with a message property
  if (error && typeof error === 'object' && 'message' in error) {
    const message = (error as { message: unknown }).message
    if (typeof message === 'string' && message.trim()) {
      return message.trim()
    }
  }

  // If it's an object with an error property
  if (error && typeof error === 'object' && 'error' in error) {
    const errorMsg = (error as { error: unknown }).error
    if (typeof errorMsg === 'string' && errorMsg.trim()) {
      return errorMsg.trim()
    }
  }

  // If it's an object with a detail property (common in API responses)
  if (error && typeof error === 'object' && 'detail' in error) {
    const detail = (error as { detail: unknown }).detail
    if (typeof detail === 'string' && detail.trim()) {
      return detail.trim()
    }
  }

  // For any other case, return the fallback message
  return fallbackMessage
}

// Used specifically for pydantic errors thrown back to the user at the endpoint before the endpoint function is executed
export function extractPydanticErrors(error: any): string {
  let errorObj = error;

  // 2. Map over the array to get just the 'msg' string from each object.
  const messages = errorObj.map((err: any) =>err.msg.replace(/^Value error,\s*/i, ''))

  // 3. Join the array of messages into a single string, separated by newlines.
  return messages.join('\n');
}


/**
 * Creates a safe error handler function that always returns a string
 * @param fallbackMessage - Default message for unhandled errors
 * @returns Function that safely formats error messages
 */
export function createErrorHandler(fallbackMessage: string = 'An unexpected error occurred') {
  return (error: unknown): string => formatErrorMessage(error, fallbackMessage)
}

/**
 * Logs error details for debugging while returning a user-friendly message
 * @param error - The error to log and format
 * @param context - Context string for logging (e.g., 'Blueprint deployment')
 * @param fallbackMessage - User-friendly fallback message
 * @returns Formatted error message for display
 */
export function logAndFormatError(
  error: unknown, 
  context: string = 'Operation',
  fallbackMessage: string = 'An unexpected error occurred'
): string {
  logger.error(`${context} error`, 'logAndFormatError', error)
  return formatErrorMessage(error, fallbackMessage)
}