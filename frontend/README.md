# OpenLabs Frontend

A modern web application for visualizing network templates and ranges, built with SvelteKit, TailwindCSS, and vis.js.

## Deployment

### Docker Deployment

The application can be containerized using Docker:

```bash
# Build the Docker image
docker build -t openlabs-frontend .

# Run the container
docker run -p 3000:3000 openlabs-frontend
```

You can also use docker-compose:

```bash
# Start the application with docker-compose
docker-compose up
```

### Static Site Deployment

The application can be built as a static site:

```bash
# Build the application
bun run build

# The built files will be in the 'build' directory
```

### Using Bun adapter

When using the Bun adapter (installed in setup), you can:

```bash
# Start production server with Bun
bun run build
bun ./build/index.js
```

## Features

- Template visualization with hierarchical network diagrams
- Interactive network components (VPC, subnets, hosts)
- Responsive design with TailwindCSS

## Prerequisites

- [Bun](https://bun.sh/) (latest)

## Setup

```bash
# Install Bun if not already installed
curl -fsSL https://bun.sh/install | bash

# Install dependencies
bun install

# Set up environment variables
cp .env.example .env
# Edit .env to configure your environment

# Start development server
bun run dev

# Build for production
bun run build

# Preview production build
bun run preview
```

## Environment Configuration

The app uses environment variables for configuration:

- `VITE_API_URL`: The URL of the API server
  - For development: Leave empty to use relative URLs with Vite's proxy
  - For production: Set to your actual API server URL (e.g., https://api.openlabs.sh)

### Development Configuration

1. Copy `.env.example` to `.env`
2. Leave `VITE_API_URL` empty (this uses Vite's proxy)
3. Run `bun run dev`

The application is configured to always use Vite's built-in proxy in development mode, 
regardless of any other configuration. This ensures API requests are correctly
proxied to your backend without CORS issues.

### Production Configuration

The app supports different deployment strategies through multiple configuration methods:

1. Build-time configuration: `.env.production` file (used with `bun run build:prod`)
2. Runtime configuration: `static/js/runtime-config.js` (can be modified after deployment)
3. API proxy: For when your API doesn't support CORS (use `bun run proxy`)

#### Option 1: Run with API on same domain (Recommended)

The simplest approach is to have your API and frontend on the same domain to avoid CORS issues.

```bash
# Build with production settings
bun run build:prod

# Run the production build
bun run start
```

#### Option 2: Use the API proxy (Solves CORS issues)

If your API is on a different domain and doesn't have CORS configured:

```bash
# Build the application
bun run build:prod

# In one terminal, run the frontend
bun run start

# In another terminal, start the API proxy 
# This will handle CORS and proxy requests to your actual API
API_URL=http://your-api-url.com bun run proxy
```

Then set the `window.__API_URL__` in your static/js/runtime-config.js to use the proxy:
```js
window.__API_URL__ = "http://localhost:3001";
```

The proxy works by:
1. Running on port 3001 (configurable via PROXY_PORT environment variable)
2. Adding CORS headers to all responses
3. Automatically handling OPTIONS preflight requests
4. Forwarding all API requests to your backend API server
5. Preserving all request data (headers, body, etc.)

This is especially useful in environments where:
- You don't control the API server
- The API doesn't support CORS
- You need to access the API from a different domain or port

#### Option 3: Configure API with CORS support

If you control the API server, enable CORS by adding these headers to API responses:

```
Access-Control-Allow-Origin: http://your-frontend-domain.com
Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS
Access-Control-Allow-Headers: Content-Type, Authorization
```

Then you can build and run directly:

```bash
# Set API URL directly
VITE_API_URL=https://api.openlabsx.com bun run build:prod
bun run start
```

## Development

### TailwindCSS

This project uses TailwindCSS for styling. The configuration is in `tailwind.config.js` and the global styles are in `app.postcss`.

### Network Visualization

The network visualization is built with vis.js and is located in `src/lib/components/NetworkGraph.svelte`.

### Testing

The project uses [Vitest](https://vitest.dev/) for unit and component testing. All tests are located in the `tests` directory with a structure that mirrors the source code.

```bash
# Run tests once
bun run test

# Run tests in watch mode (re-run on file changes)
bun run test:watch

# Run tests with coverage report
bun run test:coverage
```

Test files follow the naming convention `*.test.ts` and are organized to match the source file structure:

```
tests/
├── lib/             # Tests for lib files
│   ├── api/         # API tests
│   ├── components/  # Component tests
│   └── stores/      # Store tests
└── routes/          # Route tests
```

Component tests use `@testing-library/svelte` for rendering and interacting with Svelte components in tests.


### Linting

The project uses ESLint for code quality checks with configurations for JavaScript, TypeScript, and Svelte files. The configuration is in `eslint.config.js`.

```bash
# Run linting
bun run lint
```

ESLint is configured with:
- TypeScript integration
- Svelte-specific rules
- Prettier integration to avoid conflicts

### Code Formatting

The project uses Prettier for consistent code formatting across all files. Prettier is configured to work with Svelte and TailwindCSS through plugins.

```bash
# Format all files
bun run format

# Check if files are properly formatted (useful in CI)
bun run format:check
```

Prettier configuration (`.prettierrc`):

```json
{
  "semi": false,
  "singleQuote": true,
  "trailingComma": "es5",
  "tabWidth": 2,
  "useTabs": false,
  "plugins": ["prettier-plugin-svelte", "prettier-plugin-tailwindcss"]
}
```

Prettier will automatically format:
- JavaScript and TypeScript files
- Svelte components
- CSS files
- HTML files

It's recommended to set up your editor to format on save using the project's Prettier configuration.

### API Proxy Configuration

The API proxy (`proxy.js`) can be customized for different environments:

```bash
# Run with custom settings
API_URL=https://api.example.com PROXY_PORT=8080 bun run proxy
```

Available environment variables:
- `API_URL`: The target API server URL (default: http://localhost:8000)
- `PROXY_PORT`: The port to run the proxy on (default: 3001)

For production deployments, you might want to:
1. Run the proxy behind a reverse proxy like Nginx
2. Set up SSL termination
3. Add authentication or rate limiting

## Directory Structure

```
Frontend/
├── src/
│   ├── lib/             # Reusable components
│   │   ├── components/  # UI components
│   │   ├── stores/      # Svelte stores
│   │   └── types/       # TypeScript type definitions
│   ├── routes/          # SvelteKit routes
│   └── app.postcss      # Global styles
├── static/              # Static assets
│   └── images/          # Images for network visualization
├── tests/               # Test files
│   ├── lib/             # Tests for lib files
│   │   ├── api/         # API tests
│   │   ├── components/  # Component tests
│   │   └── stores/      # Store tests
│   ├── routes/          # Route tests
│   └── setup.ts         # Test setup and mocks
├── eslint.config.js     # ESLint configuration
├── tailwind.config.js   # TailwindCSS configuration
├── svelte.config.js     # SvelteKit configuration
└── vitest.config.ts     # Vitest configuration
```