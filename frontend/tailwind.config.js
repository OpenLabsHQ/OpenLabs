/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{html,js,ts,svelte}'],
  theme: {
    extend: {
      // Custom Colors using CSS Variables
      colors: {
        primary: {
          50: 'var(--color-primary-50)',
          100: 'var(--color-primary-100)',
          200: 'var(--color-primary-200)',
          300: 'var(--color-primary-300)',
          400: 'var(--color-primary-400)',
          500: 'var(--color-primary-500)',
          600: 'var(--color-primary-600)',
          700: 'var(--color-primary-700)',
          800: 'var(--color-primary-800)',
          900: 'var(--color-primary-900)',
        },
        success: {
          50: 'var(--color-success-50)',
          100: 'var(--color-success-100)',
          500: 'var(--color-success-500)',
          600: 'var(--color-success-600)',
          700: 'var(--color-success-700)',
        },
        danger: {
          50: 'var(--color-danger-50)',
          100: 'var(--color-danger-100)',
          500: 'var(--color-danger-500)',
          600: 'var(--color-danger-600)',
          700: 'var(--color-danger-700)',
        },
        warning: {
          50: 'var(--color-warning-50)',
          100: 'var(--color-warning-100)',
          500: 'var(--color-warning-500)',
          600: 'var(--color-warning-600)',
          700: 'var(--color-warning-700)',
        },
      },
      // Custom Spacing using CSS Variables
      spacing: {
        'sidebar': 'var(--layout-sidebar-width)',
        'header': 'var(--layout-header-height)',
        'content': 'var(--layout-content-margin)',
        'section': 'var(--space-section)',
        'card': 'var(--space-card)',
      },
      // Custom Border Radius using CSS Variables
      borderRadius: {
        'theme-sm': 'var(--radius-sm)',
        'theme-md': 'var(--radius-md)',
        'theme-lg': 'var(--radius-lg)',
        'theme-xl': 'var(--radius-xl)',
      },
      // Custom Box Shadows using CSS Variables
      boxShadow: {
        'theme-sm': 'var(--shadow-sm)',
        'theme-md': 'var(--shadow-md)',
        'theme-lg': 'var(--shadow-lg)',
        'theme-xl': 'var(--shadow-xl)',
      },
      // Custom Font Sizes using CSS Variables
      fontSize: {
        'theme-xs': 'var(--font-size-xs)',
        'theme-sm': 'var(--font-size-sm)',
        'theme-base': 'var(--font-size-base)',
        'theme-lg': 'var(--font-size-lg)',
        'theme-xl': 'var(--font-size-xl)',
        'theme-2xl': 'var(--font-size-2xl)',
      },
      // Custom Z-Index using CSS Variables
      zIndex: {
        'dropdown': 'var(--z-dropdown)',
        'sticky': 'var(--z-sticky)',
        'fixed': 'var(--z-fixed)',
        'modal-backdrop': 'var(--z-modal-backdrop)',
        'modal': 'var(--z-modal)',
        'popover': 'var(--z-popover)',
        'tooltip': 'var(--z-tooltip)',
      },
      // Custom Animation Timing
      transitionDuration: {
        'fast': 'var(--animation-duration-fast)',
        'normal': 'var(--animation-duration-normal)',
        'slow': 'var(--animation-duration-slow)',
      },
      transitionTimingFunction: {
        'theme': 'var(--animation-timing)',
      },
      // Custom Animations
      animation: {
        'flask-bubble': 'flask-bubble var(--animation-duration-slow) var(--animation-timing) infinite alternate',
        'gear-rotate': 'gear-rotate 3s linear infinite',
        'bubble-float': 'bubble-float 2s ease-in-out infinite',
        'spinner': 'spinner-spin 1s linear infinite',
      },
      // Custom Keyframes
      keyframes: {
        'flask-bubble': {
          '0%': { transform: 'scale(0.8) translateY(10px)', opacity: '0.6' },
          '50%': { transform: 'scale(1.1) translateY(-5px)', opacity: '0.8' },
          '100%': { transform: 'scale(1) translateY(0)', opacity: '1' },
        },
        'gear-rotate': {
          'from': { transform: 'rotate(0deg)' },
          'to': { transform: 'rotate(360deg)' },
        },
        'bubble-float': {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        'spinner-spin': {
          'to': { transform: 'rotate(360deg)' },
        },
      },
    },
  },
  plugins: [],
};