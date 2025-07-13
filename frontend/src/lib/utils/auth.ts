/**
 * Authentication utility functions
 * Provides reusable functions for authentication flows and validation
 */

import { goto } from '$app/navigation'
import { get } from 'svelte/store'
import { auth } from '$lib/stores/auth'
import { authApi } from '$lib/api'

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData {
  name: string;
  email: string;
  password: string;
  confirmPassword?: string;
}

export interface AuthValidationResult {
  isValid: boolean;
  errors: string[];
}

/**
 * Redirect authenticated users to a default page
 */
export function redirectIfAuthenticated(redirectTo: string = '/ranges'): boolean {
  if (get(auth).isAuthenticated) {
    goto(redirectTo);
    return true;
  }
  return false;
}

/**
 * Redirect unauthenticated users to login
 */
export function redirectIfNotAuthenticated(redirectTo: string = '/login'): boolean {
  if (!get(auth).isAuthenticated) {
    goto(redirectTo);
    return true;
  }
  return false;
}

/**
 * Validate login credentials
 */
export function validateLoginCredentials(credentials: LoginCredentials): AuthValidationResult {
  const errors: string[] = [];

  if (!credentials.email?.trim()) {
    errors.push('Email is required');
  } else if (!isValidEmail(credentials.email)) {
    errors.push('Please enter a valid email address');
  }

  if (!credentials.password?.trim()) {
    errors.push('Password is required');
  }

  return {
    isValid: errors.length === 0,
    errors
  };
}

/**
 * Validate registration data
 */
export function validateRegistrationData(data: RegisterData): AuthValidationResult {
  const errors: string[] = [];

  if (!data.name?.trim()) {
    errors.push('Name is required');
  } else if (data.name.trim().length < 2) {
    errors.push('Name must be at least 2 characters long');
  }

  if (!data.email?.trim()) {
    errors.push('Email is required');
  } else if (!isValidEmail(data.email)) {
    errors.push('Please enter a valid email address');
  }

  if (!data.password?.trim()) {
    errors.push('Password is required');
  } else {
    const passwordValidation = validatePassword(data.password);
    if (!passwordValidation.isValid) {
      errors.push(...passwordValidation.errors);
    }
  }

  if (data.confirmPassword !== undefined) {
    if (!data.confirmPassword?.trim()) {
      errors.push('Password confirmation is required');
    } else if (data.password !== data.confirmPassword) {
      errors.push('Passwords do not match');
    }
  }

  return {
    isValid: errors.length === 0,
    errors
  };
}

/**
 * Validate password strength
 */
export function validatePassword(password: string): AuthValidationResult {
  const errors: string[] = [];

  if (password.length < 8) {
    errors.push('Password must be at least 8 characters long');
  }

  if (!/[A-Z]/.test(password)) {
    errors.push('Password must contain at least one uppercase letter');
  }

  if (!/[a-z]/.test(password)) {
    errors.push('Password must contain at least one lowercase letter');
  }

  if (!/\d/.test(password)) {
    errors.push('Password must contain at least one number');
  }

  if (!/[!@#$%^&*(),.?":{}|<>]/.test(password)) {
    errors.push('Password must contain at least one special character');
  }

  return {
    isValid: errors.length === 0,
    errors
  };
}

/**
 * Check if password meets minimum requirements (less strict for backward compatibility)
 */
export function validatePasswordMinimum(password: string): AuthValidationResult {
  const errors: string[] = [];

  if (password.length < 8) {
    errors.push('Password must be at least 8 characters long');
  }

  return {
    isValid: errors.length === 0,
    errors
  };
}

/**
 * Validate email format
 */
export function isValidEmail(email: string): boolean {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email.trim());
}

/**
 * Handle login with validation and error handling
 */
export async function performLogin(
  credentials: LoginCredentials,
  onSuccess?: () => void,
  onError?: (error: string) => void
): Promise<{ success: boolean; error?: string }> {
  // Validate credentials
  const validation = validateLoginCredentials(credentials);
  if (!validation.isValid) {
    const error = validation.errors[0]; // Show first error
    if (onError) onError(error);
    return { success: false, error };
  }

  try {
    const result = await authApi.login(credentials);

    if (result.error) {
      if (onError) onError(result.error);
      return { success: false, error: result.error };
    }

    // Success
    if (onSuccess) onSuccess();
    return { success: true };

  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Login failed';
    if (onError) onError(errorMessage);
    return { success: false, error: errorMessage };
  }
}

/**
 * Handle registration with validation and error handling
 */
export async function performRegistration(
  data: RegisterData,
  onSuccess?: () => void,
  onError?: (error: string) => void
): Promise<{ success: boolean; error?: string }> {
  // Validate registration data
  const validation = validateRegistrationData(data);
  if (!validation.isValid) {
    const error = validation.errors[0]; // Show first error
    if (onError) onError(error);
    return { success: false, error };
  }

  try {
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { confirmPassword, ...registerPayload } = data;
    const result = await authApi.register(registerPayload);

    if (result.error) {
      if (onError) onError(result.error);
      return { success: false, error: result.error };
    }

    // Success
    if (onSuccess) onSuccess();
    return { success: true };

  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Registration failed';
    if (onError) onError(errorMessage);
    return { success: false, error: errorMessage };
  }
}

/**
 * Handle logout with error handling
 */
export async function performLogout(
  onSuccess?: () => void,
  onError?: (error: string) => void
): Promise<{ success: boolean; error?: string }> {
  try {
    const result = await authApi.logout();

    if (result.error) {
      if (onError) onError(result.error);
      return { success: false, error: result.error };
    }

    // Success
    if (onSuccess) onSuccess();
    return { success: true };

  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Logout failed';
    if (onError) onError(errorMessage);
    return { success: false, error: errorMessage };
  }
}

/**
 * Format authentication errors for display
 */
export function formatAuthError(error: string): string {
  // Common error message improvements
  const errorMappings: Record<string, string> = {
    'Invalid credentials': 'Invalid email or password. Please try again.',
    'User not found': 'No account found with this email address.',
    'Email already exists': 'An account with this email address already exists.',
    'Weak password': 'Please choose a stronger password.',
  };

  return errorMappings[error] || error;
}

/**
 * Check if user is authenticated
 */
export function isAuthenticated(): boolean {
  return get(auth).isAuthenticated;
}

/**
 * Get current user data
 */
export function getCurrentUser() {
  return get(auth).user;
}

/**
 * Password strength indicator
 */
export function getPasswordStrength(password: string): {
  score: number;
  label: 'Very Weak' | 'Weak' | 'Fair' | 'Good' | 'Strong';
  color: string;
} {
  let score = 0;

  // Length check
  if (password.length >= 8) score += 1;
  if (password.length >= 12) score += 1;

  // Character variety checks
  if (/[a-z]/.test(password)) score += 1;
  if (/[A-Z]/.test(password)) score += 1;
  if (/\d/.test(password)) score += 1;
  if (/[!@#$%^&*(),.?":{}|<>]/.test(password)) score += 1;

  // Determine label and color
  let label: 'Very Weak' | 'Weak' | 'Fair' | 'Good' | 'Strong';
  let color: string;

  if (score <= 1) {
    label = 'Very Weak';
    color = 'red';
  } else if (score <= 2) {
    label = 'Weak';
    color = 'orange';
  } else if (score <= 3) {
    label = 'Fair';
    color = 'yellow';
  } else if (score <= 4) {
    label = 'Good';
    color = 'blue';
  } else {
    label = 'Strong';
    color = 'green';
  }

  return { score, label, color };
}