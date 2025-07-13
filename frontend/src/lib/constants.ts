/**
 * OpenLabs Frontend Constants
 * Centralized constants for consistent values across the application
 */

// Layout Constants
export const LAYOUT = {
  SIDEBAR_WIDTH: 'w-54',
  MAIN_MARGIN: 'ml-54',
  HEADER_HEIGHT: 'h-15',
  CONTENT_PADDING: 'p-4',
  CARD_PADDING: 'p-6',
} as const;

// Grid Layout Breakpoints
export const GRID_BREAKPOINTS = {
  MOBILE: 'grid-cols-1',
  TABLET: 'md:grid-cols-2',
  DESKTOP: 'lg:grid-cols-3',
  WIDE: 'xl:grid-cols-4',
} as const;

// Button Variants
export const BUTTON_VARIANTS = {
  PRIMARY: 'rounded bg-blue-500 px-4 py-2 text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2',
  SECONDARY: 'rounded border border-gray-300 bg-white px-4 py-2 text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2',
  DANGER: 'rounded bg-red-500 px-4 py-2 text-white hover:bg-red-600 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2',
  SUCCESS: 'rounded bg-green-500 px-4 py-2 text-white hover:bg-green-600 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2',
  GHOST: 'rounded px-4 py-2 text-gray-700 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2',
} as const;

// Button Sizes
export const BUTTON_SIZES = {
  SM: 'px-3 py-1.5 text-sm',
  MD: 'px-4 py-2 text-base',
  LG: 'px-6 py-3 text-lg',
} as const;

// Input Variants
export const INPUT_VARIANTS = {
  DEFAULT: 'w-full rounded border border-gray-300 p-2 focus:border-blue-500 focus:ring-blue-500 focus:outline-none',
  ERROR: 'w-full rounded border border-red-300 p-2 focus:border-red-500 focus:ring-red-500 focus:outline-none',
  SUCCESS: 'w-full rounded border border-green-300 p-2 focus:border-green-500 focus:ring-green-500 focus:outline-none',
} as const;

// Card Variants
export const CARD_VARIANTS = {
  DEFAULT: 'rounded-lg bg-white p-6 shadow-sm',
  ELEVATED: 'rounded-lg bg-white p-6 shadow-md',
  BORDERED: 'rounded-lg border border-gray-200 bg-white p-6',
  HOVER: 'rounded-lg bg-white p-6 shadow-sm hover:shadow-md transition-shadow',
} as const;

// Status Badge Variants
export const BADGE_VARIANTS = {
  PRIMARY: 'inline-flex items-center rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-800',
  SUCCESS: 'inline-flex items-center rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-800',
  WARNING: 'inline-flex items-center rounded-full bg-yellow-100 px-2.5 py-0.5 text-xs font-medium text-yellow-800',
  DANGER: 'inline-flex items-center rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-800',
  GRAY: 'inline-flex items-center rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-800',
} as const;

// Notification Settings
export const NOTIFICATIONS = {
  SUCCESS_DURATION: 3000,
  ERROR_DURATION: 5000,
  WARNING_DURATION: 4000,
  AUTO_DISMISS: true,
  POSITION: 'top-right',
} as const;

// Animation Durations (in milliseconds)
export const ANIMATIONS = {
  FAST: 150,
  NORMAL: 300,
  SLOW: 500,
  GEAR_ROTATION: 3000,
  BUBBLE_FLOAT: 2000,
  FLASK_BUBBLE: 500,
} as const;

// Z-Index Layers
export const Z_INDEX = {
  DROPDOWN: 10,
  STICKY: 20,
  FIXED: 30,
  MODAL_BACKDROP: 40,
  MODAL: 50,
  POPOVER: 60,
  TOOLTIP: 70,
} as const;

// API Configuration
export const API = {
  BASE_URL: '/api/v1',
  TIMEOUT: 30000,
  RETRY_ATTEMPTS: 3,
  RETRY_DELAY: 1000,
} as const;

// API Endpoints
export const ENDPOINTS = {
  AUTH: {
    LOGIN: '/auth/login',
    LOGOUT: '/auth/logout',
    REGISTER: '/auth/register',
  },
  USERS: {
    ME: '/users/me',
    PASSWORD: '/users/me/password',
    SECRETS: '/users/me/secrets',
    AWS_SECRETS: '/users/me/secrets/aws',
    AZURE_SECRETS: '/users/me/secrets/azure',
  },
  BLUEPRINTS: {
    HOSTS: '/blueprints/hosts',
    RANGES: '/blueprints/ranges',
    SUBNETS: '/blueprints/subnets',
    VPCS: '/blueprints/vpcs',
    PERMISSIONS: (type: string, id: string) => `/blueprints/${type}/${id}/permissions`,
  },
  RANGES: {
    BASE: '/ranges',
    DEPLOY: '/ranges/deploy',
    DETAIL: (id: string) => `/ranges/${id}`,
    KEY: (id: string) => `/ranges/${id}/key`,
  },
  WORKSPACES: {
    BASE: '/workspaces',
    DETAIL: (id: string) => `/workspaces/${id}`,
    BLUEPRINTS: (id: string) => `/workspaces/${id}/blueprints`,
    USERS: (id: string) => `/workspaces/${id}/users`,
  },
} as const;

// Cloud Providers
export const PROVIDERS = {
  AWS: 'aws',
  AZURE: 'azure',
} as const;

// Default Regions
export const DEFAULT_REGIONS = {
  AWS: 'us_east_1',
  AZURE: 'eastus',
} as const;

// Operating Systems
export const OPERATING_SYSTEMS = {
  UBUNTU: 'ubuntu',
  CENTOS: 'centos',
  RHEL: 'rhel',
  DEBIAN: 'debian',
  WINDOWS: 'windows',
} as const;

// Workspace Roles
export const WORKSPACE_ROLES = {
  ADMIN: 'admin',
  MEMBER: 'member',
  VIEWER: 'viewer',
} as const;

// Permission Types
export const PERMISSION_TYPES = {
  READ: 'read',
  WRITE: 'write',
  DELETE: 'delete',
  ADMIN: 'admin',
} as const;

// Range States
export const RANGE_STATES = {
  PENDING: 'pending',
  DEPLOYING: 'deploying',
  RUNNING: 'running',
  STOPPING: 'stopping',
  STOPPED: 'stopped',
  ERROR: 'error',
} as const;

// Validation Constants
export const VALIDATION = {
  PASSWORD_MIN_LENGTH: 8,
  PASSWORD_REQUIRE_UPPERCASE: true,
  PASSWORD_REQUIRE_LOWERCASE: true,
  PASSWORD_REQUIRE_NUMBERS: true,
  PASSWORD_REQUIRE_SPECIAL: true,
  
  USERNAME_MIN_LENGTH: 3,
  USERNAME_MAX_LENGTH: 50,
  
  WORKSPACE_NAME_MIN_LENGTH: 3,
  WORKSPACE_NAME_MAX_LENGTH: 100,
  
  BLUEPRINT_NAME_MIN_LENGTH: 3,
  BLUEPRINT_NAME_MAX_LENGTH: 100,
} as const;

// Pagination
export const PAGINATION = {
  DEFAULT_PAGE_SIZE: 20,
  MAX_PAGE_SIZE: 100,
  SHOW_SIZE_OPTIONS: [10, 20, 50, 100],
} as const;

// File Upload
export const FILE_UPLOAD = {
  MAX_SIZE: 10 * 1024 * 1024, // 10MB
  ALLOWED_TYPES: ['text/plain', 'application/json', 'text/csv'],
  CHUNK_SIZE: 1024 * 1024, // 1MB chunks
} as const;

// Search Configuration
export const SEARCH = {
  DEBOUNCE_DELAY: 300,
  MIN_QUERY_LENGTH: 2,
  MAX_RESULTS: 50,
} as const;

// Loading States
export const LOADING_STATES = {
  IDLE: 'idle',
  LOADING: 'loading',
  SUCCESS: 'success',
  ERROR: 'error',
} as const;

// Common CSS Classes
export const COMMON_CLASSES = {
  SCREEN_READER_ONLY: 'sr-only',
  VISUALLY_HIDDEN: 'absolute -m-px h-px w-px overflow-hidden whitespace-nowrap border-0 p-0',
  FOCUS_VISIBLE: 'focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2',
  TRANSITION_DEFAULT: 'transition-colors duration-200 ease-in-out',
  TRUNCATE: 'truncate',
  FULL_WIDTH: 'w-full',
  FULL_HEIGHT: 'h-full',
} as const;

// Breakpoint Values (for programmatic use)
export const BREAKPOINTS = {
  SM: 640,
  MD: 768,
  LG: 1024,
  XL: 1280,
  '2XL': 1536,
} as const;

// Export all constants as a single object for easy importing
export const CONSTANTS = {
  LAYOUT,
  GRID_BREAKPOINTS,
  BUTTON_VARIANTS,
  BUTTON_SIZES,
  INPUT_VARIANTS,
  CARD_VARIANTS,
  BADGE_VARIANTS,
  NOTIFICATIONS,
  ANIMATIONS,
  Z_INDEX,
  API,
  ENDPOINTS,
  PROVIDERS,
  DEFAULT_REGIONS,
  OPERATING_SYSTEMS,
  WORKSPACE_ROLES,
  PERMISSION_TYPES,
  RANGE_STATES,
  VALIDATION,
  PAGINATION,
  FILE_UPLOAD,
  SEARCH,
  LOADING_STATES,
  COMMON_CLASSES,
  BREAKPOINTS,
} as const;

export default CONSTANTS;