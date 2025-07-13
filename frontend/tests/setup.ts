import { cleanup } from '@testing-library/svelte';
import { afterEach, vi, beforeEach } from 'vitest';

// Import mocks
import './mocks/app-mocks';

// Silence console output to keep tests clean
beforeEach(() => {
  vi.spyOn(console, 'error').mockImplementation(() => {});
  vi.spyOn(console, 'log').mockImplementation(() => {});
  vi.spyOn(console, 'warn').mockImplementation(() => {});

  // Mock fetch global for API tests
  global.fetch = vi.fn().mockResolvedValue({
    ok: true,
    status: 200,
    json: () => Promise.resolve({ data: 'test' }),
    headers: {
      get: () => 'application/json'
    }
  });
});

// Clean up after each test
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});