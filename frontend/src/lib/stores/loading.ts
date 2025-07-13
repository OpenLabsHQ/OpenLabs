import { writable } from 'svelte/store';

export interface LoadingState {
  isLoading: boolean;
  message?: string;
  progress?: number; // 0-100 for progress bars
}

interface GlobalLoadingState {
  [key: string]: LoadingState;
}

const createLoadingStore = () => {
  const { subscribe, update } = writable<GlobalLoadingState>({});

  return {
    subscribe,

    // Start loading for a specific key
    start: (key: string, message?: string) => {
      update(state => ({
        ...state,
        [key]: {
          isLoading: true,
          message,
          progress: undefined
        }
      }));
    },

    // Update loading progress
    updateProgress: (key: string, progress: number, message?: string) => {
      update(state => ({
        ...state,
        [key]: {
          ...state[key],
          progress,
          message: message || state[key]?.message
        }
      }));
    },

    // Update loading message
    updateMessage: (key: string, message: string) => {
      update(state => ({
        ...state,
        [key]: {
          ...state[key],
          message
        }
      }));
    },

    // Stop loading for a specific key
    stop: (key: string) => {
      update(state => {
        const newState = { ...state };
        delete newState[key];
        return newState;
      });
    },

    // Check if a specific key is loading
    isLoading: (key: string) => {
      let isLoading = false;
      subscribe(state => {
        isLoading = state[key]?.isLoading ?? false;
      })();
      return isLoading;
    },

    // Get loading state for a specific key
    getState: (key: string) => {
      let loadingState: LoadingState | undefined;
      subscribe(state => {
        loadingState = state[key];
      })();
      return loadingState;
    },

    // Clear all loading states
    clearAll: () => {
      update(() => ({}));
    }
  };
};

export const loadingStore = createLoadingStore();

// Utility function to wrap async operations with loading state
export async function withLoading<T>(
  key: string,
  operation: () => Promise<T>,
  message?: string
): Promise<T> {
  try {
    loadingStore.start(key, message);
    const result = await operation();
    return result;
  } finally {
    loadingStore.stop(key);
  }
}

// Utility function for operations with progress tracking
export async function withProgressLoading<T>(
  key: string,
  operation: (updateProgress: (progress: number, message?: string) => void) => Promise<T>,
  initialMessage?: string
): Promise<T> {
  try {
    loadingStore.start(key, initialMessage);
    
    const updateProgress = (progress: number, message?: string) => {
      loadingStore.updateProgress(key, progress, message);
    };
    
    const result = await operation(updateProgress);
    return result;
  } finally {
    loadingStore.stop(key);
  }
}