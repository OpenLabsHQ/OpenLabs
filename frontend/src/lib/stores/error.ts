import { writable } from 'svelte/store';

export interface AppError {
  id: string;
  message: string;
  type: 'error' | 'warning' | 'info';
  timestamp: Date;
  details?: Record<string, unknown>;
  dismissible: boolean;
  autoClose?: number; // Auto-close after n milliseconds
}

interface ErrorStore {
  errors: AppError[];
  globalError: AppError | null;
}

const createErrorStore = () => {
  const { subscribe, update } = writable<ErrorStore>({
    errors: [],
    globalError: null
  });

  return {
    subscribe,

    // Add a new error
    addError: (
      message: string, 
      type: AppError['type'] = 'error', 
      options: Partial<Pick<AppError, 'details' | 'dismissible' | 'autoClose'>> = {}
    ) => {
      const error: AppError = {
        id: crypto.randomUUID(),
        message,
        type,
        timestamp: new Date(),
        dismissible: options.dismissible ?? true,
        ...options
      };

      update(state => ({
        ...state,
        errors: [...state.errors, error]
      }));

      // Auto-close if specified
      if (error.autoClose) {
        setTimeout(() => {
          errorStore.removeError(error.id);
        }, error.autoClose);
      }

      return error.id;
    },

    // Remove an error by ID
    removeError: (id: string) => {
      update(state => ({
        ...state,
        errors: state.errors.filter(error => error.id !== id)
      }));
    },

    // Clear all errors
    clearErrors: () => {
      update(state => ({
        ...state,
        errors: []
      }));
    },

    // Set a global error (replaces any existing global error)
    setGlobalError: (
      message: string, 
      details?: Record<string, unknown>,
      options: Partial<Pick<AppError, 'dismissible' | 'autoClose'>> = {}
    ) => {
      const error: AppError = {
        id: crypto.randomUUID(),
        message,
        type: 'error',
        timestamp: new Date(),
        details,
        dismissible: options.dismissible ?? true,
        ...options
      };

      update(state => ({
        ...state,
        globalError: error
      }));

      // Auto-close if specified
      if (error.autoClose) {
        setTimeout(() => {
          errorStore.clearGlobalError();
        }, error.autoClose);
      }

      return error.id;
    },

    // Clear the global error
    clearGlobalError: () => {
      update(state => ({
        ...state,
        globalError: null
      }));
    },

    // Handle API errors specifically
    handleApiError: (error: Record<string, unknown>, fallbackMessage = 'An error occurred') => {
      let message = fallbackMessage;
      let details = null;

      if (error?.error) {
        message = error.error;
      } else if (error?.message) {
        message = error.message;
      } else if (typeof error === 'string') {
        message = error;
      }

      // Include additional details for debugging
      if (error?.status || error?.isAuthError) {
        details = {
          status: error.status,
          isAuthError: error.isAuthError,
          originalError: error
        };
      }

      return errorStore.addError(message, 'error', { 
        details,
        autoClose: 5000 // Auto-close API errors after 5 seconds
      });
    },

    // Handle authentication errors
    handleAuthError: (message = 'Authentication failed') => {
      return errorStore.setGlobalError(message, null, {
        dismissible: false // Auth errors shouldn't be dismissible
      });
    },

    // Show success messages
    showSuccess: (message: string, autoClose = 3000) => {
      return errorStore.addError(message, 'info', {
        autoClose,
        dismissible: true
      });
    },

    // Show warning messages
    showWarning: (message: string, autoClose?: number) => {
      return errorStore.addError(message, 'warning', {
        autoClose,
        dismissible: true
      });
    }
  };
};

export const errorStore = createErrorStore();