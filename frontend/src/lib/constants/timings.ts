/**
 * Application timing constants
 * Centralized location for all timeout, interval, and duration values
 */

// API and Network Timeouts
export const API_TIMEOUTS = {
  /** Default polling interval for job status (30 seconds) */
  JOB_POLLING_INTERVAL: 30000,
  
  /** Maximum duration for job polling before timeout (30 minutes) */
  JOB_POLLING_MAX_DURATION: 1800000,
  
  /** API request timeout (2 minutes) */
  API_REQUEST_TIMEOUT: 120000,
  
  /** Retry delay for failed API requests (5 seconds) */
  API_RETRY_DELAY: 5000,
} as const;

// UI and UX Timeouts
export const UI_TIMEOUTS = {
  /** Delay for DOM initialization in components (200ms) */
  DOM_INIT_DELAY: 200,
  
  /** Auto-close duration for success notifications (3 seconds) */
  SUCCESS_NOTIFICATION_AUTO_CLOSE: 3000,
  
  /** Auto-close duration for API error notifications (5 seconds) */
  ERROR_NOTIFICATION_AUTO_CLOSE: 5000,
  
  /** Auto-close duration for warning notifications (4 seconds) */
  WARNING_NOTIFICATION_AUTO_CLOSE: 4000,
  
  /** Debounce delay for search input (300ms) */
  SEARCH_DEBOUNCE_DELAY: 300,
  
  /** Loading spinner minimum display time to prevent flashing (500ms) */
  LOADING_MIN_DISPLAY_TIME: 500,
  
  /** Animation duration for transitions (150ms) */
  ANIMATION_DURATION: 150,
  
  /** Tooltip delay before showing (700ms) */
  TOOLTIP_DELAY: 700,
} as const;

// Animation and Visual Effects
export const ANIMATION_TIMINGS = {
  /** CSS transition duration for buttons and form elements */
  TRANSITION_FAST: '150ms',
  
  /** CSS transition duration for modals and overlays */
  TRANSITION_NORMAL: '300ms',
  
  /** CSS transition duration for page transitions */
  TRANSITION_SLOW: '500ms',
  
  /** Loading spinner rotation duration */
  SPINNER_ROTATION: '1s',
  
  /** Flask animation bubble generation interval (2 seconds) */
  FLASK_BUBBLE_INTERVAL: 2000,
  
  /** Gear rotation animation duration (3 seconds) */
  GEAR_ROTATION_DURATION: 3000,
} as const;

// Component-specific Timeouts
export const COMPONENT_TIMEOUTS = {
  /** Auto-dismiss time for toast notifications (4 seconds) */
  TOAST_AUTO_DISMISS: 4000,
  
  /** Modal backdrop click debounce (100ms) */
  MODAL_CLICK_DEBOUNCE: 100,
  
  /** Form validation debounce delay (500ms) */
  FORM_VALIDATION_DEBOUNCE: 500,
  
  /** Auto-save debounce for form data (2 seconds) */
  AUTO_SAVE_DEBOUNCE: 2000,
  
  /** Keyboard navigation delay (50ms) */
  KEYBOARD_NAV_DELAY: 50,
} as const;

// Network and Connection
export const NETWORK_TIMEOUTS = {
  /** WebSocket reconnection delay (5 seconds) */
  WEBSOCKET_RECONNECT_DELAY: 5000,
  
  /** Maximum WebSocket reconnection attempts */
  WEBSOCKET_MAX_RETRIES: 5,
  
  /** Network status check interval (30 seconds) */
  NETWORK_CHECK_INTERVAL: 30000,
  
  /** Cache expiration time for API responses (5 minutes) */
  CACHE_EXPIRATION: 300000,
} as const;

// Development and Debug
export const DEBUG_TIMEOUTS = {
  /** Artificial delay for testing loading states (1 second) */
  TESTING_LOADING_DELAY: 1000,
  
  /** Debug console log throttle (500ms) */
  DEBUG_LOG_THROTTLE: 500,
} as const;

// Export all timing constants as a single object for convenience
export const TIMINGS = {
  API: API_TIMEOUTS,
  UI: UI_TIMEOUTS,
  ANIMATION: ANIMATION_TIMINGS,
  COMPONENT: COMPONENT_TIMEOUTS,
  NETWORK: NETWORK_TIMEOUTS,
  DEBUG: DEBUG_TIMEOUTS,
} as const;

// Type exports for better TypeScript integration
export type ApiTimeouts = typeof API_TIMEOUTS;
export type UiTimeouts = typeof UI_TIMEOUTS;
export type AnimationTimings = typeof ANIMATION_TIMINGS;
export type ComponentTimeouts = typeof COMPONENT_TIMEOUTS;
export type NetworkTimeouts = typeof NETWORK_TIMEOUTS;
export type DebugTimeouts = typeof DEBUG_TIMEOUTS;
export type AllTimings = typeof TIMINGS;