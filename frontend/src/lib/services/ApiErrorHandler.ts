/**
 * Centralized API error handling service
 * Provides consistent error message formatting and handling across the application
 */

import logger from '$lib/utils/logger'

export interface ApiError {
  error: string;
  status: number;
  isAuthError: boolean;
  details?: any;
}

export interface ErrorResponse {
  detail?: string;
  message?: string;
  error?: string;
  [key: string]: any;
}

export class ApiErrorHandler {
  /**
   * HTTP status code to user-friendly message mapping
   */
  private static readonly STATUS_MESSAGES: Record<number, string> = {
    400: 'The request contains invalid data. Please check your input and try again.',
    401: 'Your session has expired. Please log in again.',
    403: "You don't have permission to access this resource.",
    404: 'The requested information could not be found.',
    408: 'The request timed out. Please try again.',
    409: 'There was a conflict with your request. Please refresh and try again.',
    422: 'The submitted data contains validation errors.',
    429: 'Too many requests. Please wait a moment and try again.',
    500: 'The server encountered an internal error. Please try again later.',
    502: 'The server is currently unavailable. Please try again later.',
    503: 'The server is currently unavailable. Please try again later.',
    504: 'The server request timed out. Please try again later.',
  };

  /**
   * HTTP status codes that indicate authentication/authorization errors
   */
  private static readonly AUTH_ERROR_CODES = new Set([401, 403]);

  /**
   * Handle API error response and return standardized error object
   */
  static handleError(
    response: Response,
    result: ErrorResponse | string,
    context?: string
  ): ApiError {
    const status = response.status;
    const isAuthError = this.AUTH_ERROR_CODES.has(status);
    
    // Log the error for debugging
    logger.error('API error', context || 'api', {
      status,
      url: response.url,
      result,
    });

    const errorMessage = this.extractErrorMessage(result, status);

    return {
      error: errorMessage,
      status,
      isAuthError,
      details: typeof result === 'object' ? result : undefined,
    };
  }

  /**
   * Extract meaningful error message from response data
   */
  private static extractErrorMessage(result: ErrorResponse | string, status: number): string {
    // If result is a string, use it directly
    if (typeof result === 'string') {
      return result || this.getDefaultMessage(status);
    }

    // If result is an object, try to extract message from various fields
    if (result && typeof result === 'object') {
      const message = result.detail || result.message || result.error;
      if (message && typeof message === 'string') {
        return message;
      }
    }

    // Fall back to default message for status code
    return this.getDefaultMessage(status);
  }

  /**
   * Get default error message for HTTP status code
   */
  private static getDefaultMessage(status: number): string {
    return this.STATUS_MESSAGES[status] || `Something went wrong (${status})`;
  }

  /**
   * Handle network errors (when fetch itself fails)
   */
  static handleNetworkError(error: Error, context?: string): ApiError {
    logger.error('Network error', context || 'api', error);

    let errorMessage = 'Network error. Please check your connection and try again.';
    
    // Handle specific error types
    if (error.name === 'AbortError') {
      errorMessage = 'The request was cancelled.';
    } else if (error.message.includes('fetch')) {
      errorMessage = 'Unable to connect to the server. Please check your connection.';
    }

    return {
      error: errorMessage,
      status: 0,
      isAuthError: false,
      details: { originalError: error.message },
    };
  }

  /**
   * Handle timeout errors
   */
  static handleTimeoutError(context?: string): ApiError {
    logger.error('Request timeout', context || 'api');

    return {
      error: 'The request timed out. Please try again.',
      status: 408,
      isAuthError: false,
    };
  }

  /**
   * Check if an error is an authentication error
   */
  static isAuthError(error: ApiError): boolean {
    return error.isAuthError;
  }

  /**
   * Check if an error is retryable (temporary server issues)
   */
  static isRetryable(error: ApiError): boolean {
    const retryableStatuses = new Set([408, 429, 500, 502, 503, 504]);
    return retryableStatuses.has(error.status);
  }

  /**
   * Get user-friendly error message for display
   */
  static getUserMessage(error: ApiError): string {
    return error.error;
  }

  /**
   * Format error for logging or debugging
   */
  static formatForLogging(error: ApiError, context?: string): string {
    return `${context ? `[${context}] ` : ''}HTTP ${error.status}: ${error.error}`;
  }
}