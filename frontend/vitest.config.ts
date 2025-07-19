import { defineConfig } from 'vitest/config';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import { fileURLToPath } from 'url';

export default defineConfig({
  plugins: [svelte({ hot: !process.env.VITEST })],
  resolve: {
    alias: {
      '$lib': fileURLToPath(new URL('./src/lib', import.meta.url)),
      '$app': fileURLToPath(new URL('./node_modules/@sveltejs/kit/src/runtime/app', import.meta.url))
    }
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['tests/setup.ts'],
    include: ['tests/**/*.{test,spec}.{js,ts}'],
    deps: {
      optimizer: {
        web: {
          include: [/svelte/]
        }
      }
    },
    coverage: {
      reporter: ['text', 'lcov'],
      exclude: [
        'node_modules/**',
        '.svelte-kit/**',
        '.build/**',
        'dist/**',
        'static/**',
        '**/*.config.{js,ts}',
        '**/setup.ts',
        '**/*.d.ts',
      ],
    },
    reporters: ['default'],
    outputFile: {
      json: './coverage/coverage.json',
    },
    silent: true,
  },
});