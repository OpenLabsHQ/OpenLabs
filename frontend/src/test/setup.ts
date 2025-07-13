import { cleanup } from '@testing-library/svelte'
import { afterEach, vi } from 'vitest'

// Silence console output to keep tests clean
vi.spyOn(console, 'error').mockImplementation(() => {})
vi.spyOn(console, 'log').mockImplementation(() => {})
vi.spyOn(console, 'warn').mockImplementation(() => {})

// Mock window.location
Object.defineProperty(window, 'location', {
  value: {
    href: 'http://localhost:5173/',
    pathname: '/',
    search: '',
    hash: '',
    assign: vi.fn(),
    replace: vi.fn(),
  },
  writable: true,
})

// Clean up after each test
afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})
