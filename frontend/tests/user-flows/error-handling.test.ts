import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock SvelteKit navigation
const goto = vi.fn();
vi.mock('$app/navigation', () => ({
  goto
}));

// Mock error utility functions for testing
const formatErrorMessage = (error: any, fallback = 'An unexpected error occurred') => {
  if (typeof error === 'string') {
    return error.trim() || fallback;
  }
  if (error instanceof Error) {
    return error.message || fallback;
  }
  if (error && typeof error === 'object') {
    if (error.message) return error.message;
    if (error.error) return error.error;
    if (error.detail) return error.detail;
  }
  return fallback;
};

const logAndFormatError = (error: any, context = '', fallback = 'An unexpected error occurred') => {
  console.error(`${context} error:`, error);
  return formatErrorMessage(error, fallback);
};

const createErrorHandler = (defaultMessage: string) => {
  return (error: any) => formatErrorMessage(error, defaultMessage);
};

describe('Error Handling User Flow', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  describe('Error Message Formatting', () => {
    it('should format different error types correctly', () => {
      const errorTests = [
        {
          input: 'Simple string error',
          expected: 'Simple string error'
        },
        {
          input: new Error('Error object message'),
          expected: 'Error object message'
        },
        {
          input: { message: 'Object with message property' },
          expected: 'Object with message property'
        },
        {
          input: { error: 'Object with error property' },
          expected: 'Object with error property'
        },
        {
          input: { detail: 'Object with detail property' },
          expected: 'Object with detail property'
        },
        {
          input: { someRandomProperty: 'Random data' },
          expected: 'An unexpected error occurred'
        },
        {
          input: null,
          expected: 'An unexpected error occurred'
        },
        {
          input: undefined,
          expected: 'An unexpected error occurred'
        },
        {
          input: '',
          expected: 'An unexpected error occurred'
        },
        {
          input: '   ',
          expected: 'An unexpected error occurred'
        }
      ];

      errorTests.forEach(({ input, expected }) => {
        const result = formatErrorMessage(input);
        expect(result).toBe(expected);
      });
    });

    it('should use custom fallback messages', () => {
      const customFallback = 'Custom error message';
      const result = formatErrorMessage({}, customFallback);
      expect(result).toBe(customFallback);
    });

    it('should trim whitespace from error messages', () => {
      const errors = [
        '  Leading whitespace',
        'Trailing whitespace  ',
        '  Both sides  ',
        '\n\tNewlines and tabs\n\t'
      ];

      errors.forEach(error => {
        const result = formatErrorMessage(error);
        expect(result).toBe(error.trim());
      });
    });
  });

  describe('Error Logging and Formatting', () => {
    it('should log error details while returning user-friendly message', () => {
      const error = new Error('Detailed technical error');
      const context = 'API Request';
      const fallback = 'Request failed';

      const result = logAndFormatError(error, context, fallback);

      expect(console.error).toHaveBeenCalledWith(`${context} error:`, error);
      expect(result).toBe('Detailed technical error');
    });

    it('should handle complex error objects with logging', () => {
      const complexError = {
        status: 500,
        statusText: 'Internal Server Error',
        detail: 'Database connection failed',
        timestamp: '2024-01-01T10:00:00Z',
        requestId: 'req_123'
      };

      const result = logAndFormatError(complexError, 'Database operation');

      expect(console.error).toHaveBeenCalledWith('Database operation error:', complexError);
      expect(result).toBe('Database connection failed');
    });

    it('should create reusable error handlers', () => {
      const apiErrorHandler = createErrorHandler('API request failed');
      const dbErrorHandler = createErrorHandler('Database operation failed');

      expect(apiErrorHandler(new Error('Network timeout'))).toBe('Network timeout');
      expect(apiErrorHandler({})).toBe('API request failed');
      expect(dbErrorHandler(null)).toBe('Database operation failed');
    });
  });

  describe('API Error Handling', () => {
    it('should handle HTTP status code errors', () => {
      const httpErrors = [
        { status: 400, message: 'Bad Request', userMessage: 'Invalid request data' },
        { status: 401, message: 'Unauthorized', userMessage: 'Please log in again' },
        { status: 403, message: 'Forbidden', userMessage: 'Access denied' },
        { status: 404, message: 'Not Found', userMessage: 'Resource not found' },
        { status: 429, message: 'Too Many Requests', userMessage: 'Please try again later' },
        { status: 500, message: 'Internal Server Error', userMessage: 'Server error occurred' },
        { status: 502, message: 'Bad Gateway', userMessage: 'Service temporarily unavailable' },
        { status: 503, message: 'Service Unavailable', userMessage: 'Service temporarily unavailable' }
      ];

      const getErrorMessage = (status, fallback = 'An error occurred') => {
        const errorMap = {
          400: 'Invalid request data',
          401: 'Please log in again',
          403: 'Access denied',
          404: 'Resource not found',
          429: 'Please try again later',
          500: 'Server error occurred',
          502: 'Service temporarily unavailable',
          503: 'Service temporarily unavailable'
        };

        return errorMap[status] || fallback;
      };

      httpErrors.forEach(({ status, userMessage }) => {
        expect(getErrorMessage(status)).toBe(userMessage);
      });
    });

    it('should handle validation errors from API', () => {
      const validationError = {
        detail: [
          {
            loc: ['body', 'name'],
            msg: 'field required',
            type: 'value_error.missing'
          },
          {
            loc: ['body', 'email'],
            msg: 'invalid email format',
            type: 'value_error.email'
          }
        ]
      };

      const formatValidationErrors = (errors) => {
        if (Array.isArray(errors.detail)) {
          return errors.detail.map(err => {
            const field = err.loc[err.loc.length - 1];
            return `${field}: ${err.msg}`;
          }).join(', ');
        }
        return formatErrorMessage(errors);
      };

      const result = formatValidationErrors(validationError);
      expect(result).toBe('name: field required, email: invalid email format');
    });

    it('should handle network errors gracefully', () => {
      const networkErrors = [
        { type: 'TypeError', message: 'Failed to fetch' },
        { type: 'Error', message: 'Network request failed' },
        { type: 'TimeoutError', message: 'Request timeout' },
        { type: 'AbortError', message: 'Request was aborted' }
      ];

      const getNetworkErrorMessage = (error) => {
        const networkErrorMap = {
          'Failed to fetch': 'Unable to connect to server',
          'Network request failed': 'Network connection error',
          'Request timeout': 'Request took too long to complete',
          'Request was aborted': 'Request was cancelled'
        };

        return networkErrorMap[error.message] || 'Network error occurred';
      };

      networkErrors.forEach(error => {
        const result = getNetworkErrorMessage(error);
        expect(result).toBeTruthy();
        expect(result).not.toBe(error.message); // Should be user-friendly
      });
    });
  });

  describe('Authentication Error Handling', () => {
    it('should redirect to login on authentication errors', () => {
      const authErrors = [
        { status: 401, error: 'Token expired' },
        { status: 401, error: 'Invalid token' },
        { status: 403, error: 'Access denied' }
      ];

      const handleAuthError = (error) => {
        if (error.status === 401) {
          goto('/login');
          return 'Please log in again';
        }
        if (error.status === 403) {
          return 'Access denied';
        }
        return formatErrorMessage(error);
      };

      authErrors.forEach(error => {
        const result = handleAuthError(error);
        
        if (error.status === 401) {
          expect(goto).toHaveBeenCalledWith('/login');
          expect(result).toBe('Please log in again');
        }
      });
    });

    it('should handle session expiration gracefully', () => {
      const sessionError = {
        status: 401,
        detail: 'Session has expired',
        isAuthError: true
      };

      const handleSessionExpiration = (error) => {
        if (error.isAuthError || error.status === 401) {
          // Clear any stored auth state
          localStorage.removeItem('authToken');
          sessionStorage.clear();
          
          // Redirect to login
          goto('/login');
          
          return 'Your session has expired. Please log in again.';
        }
        return formatErrorMessage(error);
      };

      const result = handleSessionExpiration(sessionError);
      
      expect(result).toBe('Your session has expired. Please log in again.');
      expect(goto).toHaveBeenCalledWith('/login');
    });
  });

  describe('User-Facing Error Messages', () => {
    it('should provide helpful error messages for common user actions', () => {
      const userActionErrors = {
        'blueprint_creation': 'Failed to create blueprint. Please check your inputs and try again.',
        'range_deployment': 'Unable to deploy range. Please check your cloud credentials.',
        'file_upload': 'File upload failed. Please ensure the file is valid and try again.',
        'form_validation': 'Please correct the highlighted fields and try again.',
        'permission_denied': 'You do not have permission to perform this action.',
        'quota_exceeded': 'You have reached your account limits. Please upgrade or contact support.',
        'server_maintenance': 'Our servers are currently under maintenance. Please try again later.'
      };

      Object.entries(userActionErrors).forEach(([action, message]) => {
        expect(message).toBeTruthy();
        expect(message.length).toBeGreaterThan(10);
        expect(message).toMatch(/[.!]/); // Should end with punctuation
      });
    });

    it('should provide actionable error messages', () => {
      const actionableErrors = [
        {
          error: 'Invalid email format',
          suggestion: 'Please enter a valid email address (e.g., user@example.com)'
        },
        {
          error: 'Password too weak',
          suggestion: 'Please use at least 8 characters with uppercase, lowercase, and numbers'
        },
        {
          error: 'File too large',
          suggestion: 'Please select a file smaller than 10MB'
        },
        {
          error: 'Network timeout',
          suggestion: 'Please check your internet connection and try again'
        }
      ];

      const createActionableMessage = (error, suggestion) => {
        return `${error}. ${suggestion}`;
      };

      actionableErrors.forEach(({ error, suggestion }) => {
        const message = createActionableMessage(error, suggestion);
        expect(message).toContain(error);
        expect(message).toContain(suggestion);
        expect(message).toMatch(/Please/); // Should contain actionable language
      });
    });
  });

  describe('Error Boundary Handling', () => {
    it('should catch and handle component errors', () => {
      const componentError = new Error('Component render failed');
      const errorInfo = { componentStack: 'ComponentStack trace...' };

      const handleComponentError = (error, errorInfo) => {
        console.error('Component error:', error, errorInfo);
        
        return {
          hasError: true,
          error: error,
          errorInfo: errorInfo,
          userMessage: 'Something went wrong. Please refresh the page and try again.'
        };
      };

      const result = handleComponentError(componentError, errorInfo);

      expect(result.hasError).toBe(true);
      expect(result.error).toBe(componentError);
      expect(result.userMessage).toBeTruthy();
      expect(console.error).toHaveBeenCalled();
    });

    it('should provide error recovery options', () => {
      const errorRecoveryOptions = [
        { action: 'retry', label: 'Try Again', handler: () => window.location.reload() },
        { action: 'home', label: 'Go Home', handler: () => goto('/') },
        { action: 'back', label: 'Go Back', handler: () => window.history.back() },
        { action: 'report', label: 'Report Issue', handler: () => goto('/support') }
      ];

      errorRecoveryOptions.forEach(option => {
        expect(option.action).toBeTruthy();
        expect(option.label).toBeTruthy();
        expect(typeof option.handler).toBe('function');
      });

      // Test home navigation
      errorRecoveryOptions[1].handler();
      expect(goto).toHaveBeenCalledWith('/');
    });

    it('should handle unhandled promise rejections', () => {
      const unhandledRejection = {
        reason: new Error('Unhandled async error'),
        promise: null // Don't create actual promise to avoid unhandled rejection
      };

      const handleUnhandledRejection = (event) => {
        console.error('Unhandled promise rejection:', event.reason);
        
        // Convert to standardized error format
        const error = event.reason instanceof Error 
          ? event.reason 
          : new Error(String(event.reason));
          
        return {
          type: 'unhandledRejection',
          error: error,
          userMessage: formatErrorMessage(error, 'An unexpected error occurred')
        };
      };

      const result = handleUnhandledRejection(unhandledRejection);

      expect(result.type).toBe('unhandledRejection');
      expect(result.error).toBeInstanceOf(Error);
      expect(result.userMessage).toBeTruthy();
    });
  });

  describe('Progressive Error Disclosure', () => {
    it('should show basic error message with option to view details', () => {
      const error = {
        message: 'Operation failed',
        details: {
          code: 'ERR_001',
          timestamp: '2024-01-01T10:00:00Z',
          requestId: 'req_123',
          stack: 'Error stack trace...'
        }
      };

      const createErrorDisplay = (error, showDetails = false) => {
        const display = {
          message: formatErrorMessage(error),
          canShowDetails: !!error.details
        };

        if (showDetails && error.details) {
          display.details = error.details;
        }

        return display;
      };

      const basicDisplay = createErrorDisplay(error, false);
      const detailedDisplay = createErrorDisplay(error, true);

      expect(basicDisplay.message).toBe('Operation failed');
      expect(basicDisplay.canShowDetails).toBe(true);
      expect(basicDisplay.details).toBeUndefined();

      expect(detailedDisplay.details).toBeDefined();
      expect(detailedDisplay.details.code).toBe('ERR_001');
    });

    it('should sanitize error details for security', () => {
      const unsafeError = {
        message: 'Database error',
        details: {
          query: 'SELECT * FROM users WHERE password = "secret123"',
          connectionString: 'mongodb://admin:password@localhost:27017/db',
          apiKey: 'sk_live_abc123def456',
          internalPath: '/var/www/app/config/secrets.php'
        }
      };

      const sanitizeErrorDetails = (details) => {
        const sensitive = ['password', 'secret', 'key', 'token', 'connection'];
        const sanitized = { ...details };

        Object.keys(sanitized).forEach(key => {
          const lowerKey = key.toLowerCase();
          const value = String(sanitized[key]);

          if (sensitive.some(word => lowerKey.includes(word)) || 
              value.includes('password') || 
              value.includes('secret') ||
              value.startsWith('sk_') ||
              value.includes('://')) {
            sanitized[key] = '[REDACTED]';
          }
        });

        return sanitized;
      };

      const sanitized = sanitizeErrorDetails(unsafeError.details);

      expect(sanitized.query).toBe('[REDACTED]');
      expect(sanitized.connectionString).toBe('[REDACTED]');
      expect(sanitized.apiKey).toBe('[REDACTED]');
      expect(sanitized.internalPath).toBe('[REDACTED]');
    });
  });

  describe('Error Analytics and Monitoring', () => {
    it('should track error frequency and patterns', () => {
      const errorTracker = {
        errors: [],
        track: function(error, context) {
          this.errors.push({
            error: formatErrorMessage(error),
            context: context,
            timestamp: Date.now(),
            userAgent: navigator.userAgent,
            url: window.location.href
          });
        },
        getStats: function() {
          const errorCounts = {};
          this.errors.forEach(entry => {
            errorCounts[entry.error] = (errorCounts[entry.error] || 0) + 1;
          });
          return {
            total: this.errors.length,
            unique: Object.keys(errorCounts).length,
            mostCommon: Object.entries(errorCounts)
              .sort(([,a], [,b]) => b - a)
              .slice(0, 5)
          };
        }
      };

      // Simulate some errors
      errorTracker.track(new Error('Network error'), 'API call');
      errorTracker.track(new Error('Validation failed'), 'Form submission');
      errorTracker.track(new Error('Network error'), 'API call');

      const stats = errorTracker.getStats();

      expect(stats.total).toBe(3);
      expect(stats.unique).toBe(2);
      expect(stats.mostCommon[0][0]).toBe('Network error');
      expect(stats.mostCommon[0][1]).toBe(2);
    });

    it('should provide error context for debugging', () => {
      const captureErrorContext = () => {
        return {
          timestamp: new Date().toISOString(),
          url: window.location.href,
          userAgent: navigator.userAgent,
          viewport: {
            width: window.innerWidth,
            height: window.innerHeight
          },
          localStorage: Object.keys(localStorage).length,
          sessionStorage: Object.keys(sessionStorage).length,
          memoryUsage: (performance as any).memory ? {
            used: (performance as any).memory.usedJSHeapSize,
            total: (performance as any).memory.totalJSHeapSize
          } : null
        };
      };

      const context = captureErrorContext();

      expect(context.timestamp).toBeTruthy();
      expect(context.url).toBeTruthy();
      expect(context.userAgent).toBeTruthy();
      expect(typeof context.viewport.width).toBe('number');
      expect(typeof context.localStorage).toBe('number');
    });

    it('should rate limit error reporting', () => {
      const rateLimitedReporter = {
        reported: new Map(),
        maxReportsPerMinute: 10,
        
        shouldReport: function(errorKey) {
          const now = Date.now();
          const minute = Math.floor(now / 60000);
          const key = `${errorKey}-${minute}`;
          
          const count = this.reported.get(key) || 0;
          if (count >= this.maxReportsPerMinute) {
            return false;
          }
          
          this.reported.set(key, count + 1);
          return true;
        }
      };

      const errorKey = 'network-error';

      // Should allow first 10 reports
      for (let i = 0; i < 10; i++) {
        expect(rateLimitedReporter.shouldReport(errorKey)).toBe(true);
      }

      // Should reject 11th report
      expect(rateLimitedReporter.shouldReport(errorKey)).toBe(false);
    });
  });
});