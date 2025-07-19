import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';
import tailwindcss from '@tailwindcss/vite';
import { configDefaults } from 'vitest/config';
import { fileURLToPath } from 'url';

export default defineConfig({
	plugins: [
		sveltekit(),
		tailwindcss({
			// Explicitly set the config path, this is optional but recommended for clarity
			configPath: './tailwind.config.js',
		}),
	],
	resolve: {
		alias: {
			'$lib': fileURLToPath(new URL('./src/lib', import.meta.url)),
			'$app': fileURLToPath(new URL('./node_modules/@sveltejs/kit/src/runtime/app', import.meta.url)),
		},
	},
	// Add development server proxy to avoid CORS issues
	server: {
		proxy: {
			// Proxy all API requests to backend
			'/api': {
				target: 'http://127.0.0.1:8000',
				changeOrigin: true,
				secure: false
			}
		}
	},
	// Add CSS handling options
	css: {
		// This ensures Tailwind is processed correctly
		postcss: true
	},
	// Vitest configuration
	test: {
		globals: true,
		environment: 'jsdom',
		include: ['tests/**/*.{test,spec}.{js,ts,svelte}'],
		exclude: [...configDefaults.exclude, 'build', '.svelte-kit/**/*'],
		setupFiles: ['tests/setup.ts'],
		coverage: {
			reporter: ['text', 'html'],
			exclude: [
				'src/app.html',
				'**/*.d.ts',
				'node_modules/**',
				'.svelte-kit/**',
				'.build/**',
				'dist/**',
				'static/**',
				'**/*.config.{js,ts}'
			],
		},
		reporters: 'basic',
		outputFile: {
			json: './coverage/coverage.json'
		}
	}
});