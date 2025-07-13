/**
 * Shared form utilities and styling classes
 * Provides consistent theming and styling across all form components
 */

export type FormTheme = 'light' | 'dark';
export type FormSize = 'sm' | 'md' | 'lg';
export type FormRounded = 'none' | 'sm' | 'md' | 'lg' | 'full';

export interface FormThemeClasses {
  base: string;
  focus: string;
  error: string;
  disabled: string;
}

/**
 * Theme classes for form components
 */
export const formThemeClasses: Record<FormTheme, FormThemeClasses> = {
  light: {
    base: 'border-gray-300 bg-white text-gray-900 placeholder-gray-500',
    focus: 'focus:border-primary-500 focus:ring-primary-500',
    error: 'border-danger-300 bg-danger-50 text-danger-900 placeholder-danger-400 focus:border-danger-500 focus:ring-danger-500',
    disabled: 'disabled:bg-gray-50 disabled:text-gray-500 disabled:cursor-not-allowed'
  },
  dark: {
    base: 'border-gray-700 bg-gray-800 text-white placeholder-gray-500',
    focus: 'focus:border-primary-500 focus:ring-primary-500',
    error: 'border-danger-500 bg-danger-900/50 text-danger-300 placeholder-danger-400 focus:border-danger-500 focus:ring-danger-500',
    disabled: 'disabled:bg-gray-700 disabled:text-gray-400 disabled:cursor-not-allowed'
  }
};

/**
 * Size classes for form components
 */
export const formSizeClasses: Record<FormSize, string> = {
  sm: 'px-3 py-1.5 text-sm',
  md: 'px-3 py-2 text-sm',
  lg: 'px-4 py-3 text-base'
};

/**
 * Rounded corner classes for form components
 */
export const formRoundedClasses: Record<FormRounded, string> = {
  none: 'rounded-none',
  sm: 'rounded-sm',
  md: 'rounded-md',
  lg: 'rounded-lg',
  full: 'rounded-full'
};

/**
 * Base classes that all form inputs share
 */
export const formBaseClasses = 'block border focus:outline-none focus:ring-1 transition-colors duration-200';

/**
 * Generate form input classes based on theme, size, and state
 */
export function generateFormClasses(
  theme: FormTheme,
  size: FormSize,
  rounded: FormRounded,
  hasError: boolean,
  fullWidth: boolean,
  additionalClasses?: string
): string {
  const themeClass = hasError 
    ? formThemeClasses[theme].error 
    : formThemeClasses[theme].base;
  
  const focusClass = hasError ? '' : formThemeClasses[theme].focus;
  const disabledClass = formThemeClasses[theme].disabled;
  
  const classes = [
    formBaseClasses,
    formSizeClasses[size],
    formRoundedClasses[rounded],
    fullWidth ? 'w-full' : '',
    themeClass,
    focusClass,
    disabledClass,
    additionalClasses || ''
  ].filter(Boolean);

  return classes.join(' ');
}

/**
 * Generate unique ID for form elements
 */
export function generateFormId(prefix: string): string {
  return `${prefix}-${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Form validation utilities
 */
export class FormValidator {
  private errors: Record<string, string> = {};

  /**
   * Add validation error for a field
   */
  setError(field: string, message: string): void {
    this.errors[field] = message;
  }

  /**
   * Get validation error for a field
   */
  getError(field: string): string {
    return this.errors[field] || '';
  }

  /**
   * Check if a field has an error
   */
  hasError(field: string): boolean {
    return Boolean(this.errors[field]);
  }

  /**
   * Check if any field has errors
   */
  hasErrors(): boolean {
    return Object.values(this.errors).some(error => error !== '');
  }

  /**
   * Clear error for a specific field
   */
  clearError(field: string): void {
    delete this.errors[field];
  }

  /**
   * Clear all errors
   */
  clearAll(): void {
    this.errors = {};
  }

  /**
   * Get all errors
   */
  getAllErrors(): Record<string, string> {
    return { ...this.errors };
  }

  /**
   * Validate required field
   */
  validateRequired(value: string, fieldName: string): boolean {
    if (!value || value.trim() === '') {
      this.setError(fieldName, `${fieldName} is required`);
      return false;
    }
    this.clearError(fieldName);
    return true;
  }

  /**
   * Validate email format
   */
  validateEmail(email: string, fieldName = 'Email'): boolean {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      this.setError(fieldName, 'Please enter a valid email address');
      return false;
    }
    this.clearError(fieldName);
    return true;
  }

  /**
   * Validate minimum length
   */
  validateMinLength(value: string, minLength: number, fieldName: string): boolean {
    if (value.length < minLength) {
      this.setError(fieldName, `${fieldName} must be at least ${minLength} characters long`);
      return false;
    }
    this.clearError(fieldName);
    return true;
  }

  /**
   * Validate maximum length
   */
  validateMaxLength(value: string, maxLength: number, fieldName: string): boolean {
    if (value.length > maxLength) {
      this.setError(fieldName, `${fieldName} must not exceed ${maxLength} characters`);
      return false;
    }
    this.clearError(fieldName);
    return true;
  }

  /**
   * Validate pattern match
   */
  validatePattern(value: string, pattern: RegExp, fieldName: string, errorMessage: string): boolean {
    if (!pattern.test(value)) {
      this.setError(fieldName, errorMessage);
      return false;
    }
    this.clearError(fieldName);
    return true;
  }
}

/**
 * Create a new form validator instance
 */
export function createFormValidator(): FormValidator {
  return new FormValidator();
}