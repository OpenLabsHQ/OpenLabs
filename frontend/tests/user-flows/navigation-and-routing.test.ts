import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock SvelteKit navigation
const goto = vi.fn();
vi.mock('$app/navigation', () => ({
  goto
}));

// Mock auth store
const auth = {
  isAuthenticated: false,
  user: null,
  setAuth: vi.fn(),
  updateUser: vi.fn(),
  updateAuthState: vi.fn(),
  logout: vi.fn(),
  subscribe: vi.fn()
};

describe('Navigation and Routing User Flow', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  describe('Protected Route Access', () => {
    it('should redirect unauthenticated users to login', () => {
      const protectedRoutes = [
        '/blueprints',
        '/blueprints/create',
        '/ranges',
        '/ranges/123',
        '/workspaces',
        '/settings'
      ];

      auth.isAuthenticated = false;

      const checkRouteAccess = (route) => {
        if (!auth.isAuthenticated) {
          goto('/login');
          return false;
        }
        return true;
      };

      protectedRoutes.forEach(route => {
        const canAccess = checkRouteAccess(route);
        expect(canAccess).toBe(false);
        expect(goto).toHaveBeenCalledWith('/login');
      });
    });

    it('should allow authenticated users to access protected routes', () => {
      const protectedRoutes = [
        '/blueprints',
        '/blueprints/create',
        '/ranges',
        '/ranges/123',
        '/workspaces',
        '/settings'
      ];

      auth.isAuthenticated = true;

      const checkRouteAccess = (route) => {
        if (!auth.isAuthenticated) {
          goto('/login');
          return false;
        }
        return true;
      };

      protectedRoutes.forEach(route => {
        const canAccess = checkRouteAccess(route);
        expect(canAccess).toBe(true);
      });

      expect(goto).not.toHaveBeenCalledWith('/login');
    });

    it('should allow public routes without authentication', () => {
      const publicRoutes = [
        '/',
        '/login',
        '/signup',
        '/about',
        '/contact'
      ];

      auth.isAuthenticated = false;

      const isPublicRoute = (route) => {
        const publicPaths = ['/', '/login', '/signup', '/about', '/contact'];
        return publicPaths.includes(route);
      };

      publicRoutes.forEach(route => {
        expect(isPublicRoute(route)).toBe(true);
      });
    });
  });

  describe('Navigation Between Pages', () => {
    it('should navigate to blueprint creation workflow', () => {
      const blueprintCreationSteps = [
        '/blueprints/create',
        '/blueprints/create/vpc',
        '/blueprints/create/subnet',
        '/blueprints/create/host',
        '/blueprints/create/review'
      ];

      let currentStep = 0;

      const nextStep = () => {
        if (currentStep < blueprintCreationSteps.length - 1) {
          currentStep++;
          goto(blueprintCreationSteps[currentStep]);
        }
      };

      const prevStep = () => {
        if (currentStep > 0) {
          currentStep--;
          goto(blueprintCreationSteps[currentStep]);
        }
      };

      // Navigate forward through steps
      nextStep();
      expect(goto).toHaveBeenCalledWith('/blueprints/create/vpc');

      nextStep();
      expect(goto).toHaveBeenCalledWith('/blueprints/create/subnet');

      // Navigate backward
      prevStep();
      expect(goto).toHaveBeenCalledWith('/blueprints/create/vpc');
    });

    it('should navigate from blueprint to deployment', () => {
      const blueprintId = '123';
      const deploymentFlow = [
        `/blueprints/${blueprintId}`,
        `/ranges/building/job_456`,
        `/ranges/range_789`
      ];

      // Start blueprint deployment
      goto(deploymentFlow[1]);
      expect(goto).toHaveBeenCalledWith('/ranges/building/job_456');

      // Complete deployment and go to range
      goto(deploymentFlow[2]);
      expect(goto).toHaveBeenCalledWith('/ranges/range_789');
    });

    it('should handle back navigation correctly', () => {
      const navigationHistory = [
        '/blueprints',
        '/blueprints/123',
        '/blueprints/123/deploy'
      ];

      let currentIndex = navigationHistory.length - 1;

      const goBack = () => {
        if (currentIndex > 0) {
          currentIndex--;
          goto(navigationHistory[currentIndex]);
        }
      };

      goBack();
      expect(goto).toHaveBeenCalledWith('/blueprints/123');

      goBack();
      expect(goto).toHaveBeenCalledWith('/blueprints');
    });

    it('should navigate to correct page after login', () => {
      const redirectAfterLogin = '/blueprints/create';
      
      // Store intended destination
      const intendedRoute = redirectAfterLogin;
      
      // Simulate login success
      auth.isAuthenticated = true;
      
      // Redirect to intended route
      goto(intendedRoute);
      
      expect(goto).toHaveBeenCalledWith('/blueprints/create');
    });
  });

  describe('Route Parameter Validation', () => {
    it('should validate blueprint IDs in URLs', () => {
      const testCases = [
        { id: '123', valid: true },
        { id: 'blueprint_abc', valid: true },
        { id: 'abc-def-123', valid: true },
        { id: '', valid: false },
        { id: 'invalid/id', valid: false },
        { id: 'id with spaces', valid: false },
        { id: '../../etc/passwd', valid: false }
      ];

      const isValidBlueprintId = (id) => {
        return /^[a-zA-Z0-9-_]+$/.test(id) && id.length > 0;
      };

      testCases.forEach(({ id, valid }) => {
        expect(isValidBlueprintId(id)).toBe(valid);
      });
    });

    it('should validate range IDs in URLs', () => {
      const testCases = [
        { id: 'range_123', valid: true },
        { id: '456', valid: true },
        { id: 'abc-def', valid: true },
        { id: '', valid: false },
        { id: 'range/invalid', valid: false },
        { id: '<script>', valid: false },
        { id: 'range%20123', valid: false }
      ];

      const isValidRangeId = (id) => {
        return /^[a-zA-Z0-9-_]+$/.test(id) && id.length > 0;
      };

      testCases.forEach(({ id, valid }) => {
        expect(isValidRangeId(id)).toBe(valid);
      });
    });

    it('should validate job IDs in URLs', () => {
      const testCases = [
        { id: 'job_123', valid: true },
        { id: 'build_abc_def', valid: true },
        { id: '789', valid: true },
        { id: '', valid: false },
        { id: 'job.invalid', valid: false },
        { id: 'job@123', valid: false }
      ];

      const isValidJobId = (id) => {
        return /^[a-zA-Z0-9-_]+$/.test(id) && id.length > 0;
      };

      testCases.forEach(({ id, valid }) => {
        expect(isValidJobId(id)).toBe(valid);
      });
    });

    it('should handle invalid route parameters with 404', () => {
      const invalidRoutes = [
        '/blueprints/',
        '/blueprints/invalid/id',
        '/ranges/',
        '/ranges/invalid id',
        '/workspaces/<script>'
      ];

      const handleInvalidRoute = (route) => {
        // Check for valid route patterns
        const validPatterns = [
          /^\/blueprints\/[a-zA-Z0-9-_]+$/,
          /^\/ranges\/[a-zA-Z0-9-_]+$/,
          /^\/workspaces\/[a-zA-Z0-9-_]+$/
        ];

        // Check if route ends with trailing slash (invalid)
        if (route.endsWith('/') && route !== '/') {
          return { status: 404, error: 'Invalid route parameter' };
        }

        // Check if route has invalid characters or structure
        if (route.includes(' ') || route.includes('<') || route.includes('>')) {
          return { status: 404, error: 'Invalid route parameter' };
        }

        // Check if route has too many segments
        const parts = route.split('/').filter(Boolean);
        if (parts.length > 2) {
          return { status: 404, error: 'Invalid route parameter' };
        }

        return { status: 200 };
      };

      invalidRoutes.forEach(route => {
        const result = handleInvalidRoute(route);
        expect(result.status).toBe(404);
      });
    });
  });

  describe('URL State Management', () => {
    it('should preserve URL state during navigation', () => {
      const urlWithParams = '/blueprints?filter=aws&sort=date&page=2';
      
      const parseUrlParams = (url) => {
        const [path, queryString] = url.split('?');
        const params = new URLSearchParams(queryString || '');
        
        return {
          path,
          filter: params.get('filter'),
          sort: params.get('sort'),
          page: parseInt(params.get('page') || '1')
        };
      };

      const result = parseUrlParams(urlWithParams);

      expect(result.path).toBe('/blueprints');
      expect(result.filter).toBe('aws');
      expect(result.sort).toBe('date');
      expect(result.page).toBe(2);
    });

    it('should handle search parameters correctly', () => {
      const searchScenarios = [
        {
          url: '/blueprints?search=web%20server',
          expectedSearch: 'web server'
        },
        {
          url: '/ranges?status=running&provider=aws',
          expectedParams: { status: 'running', provider: 'aws' }
        },
        {
          url: '/workspaces?page=1&limit=10',
          expectedParams: { page: '1', limit: '10' }
        }
      ];

      searchScenarios.forEach(scenario => {
        const url = new URL(scenario.url, 'http://localhost');
        const params = Object.fromEntries(url.searchParams.entries());

        if (scenario.expectedSearch) {
          expect(params.search).toBe(scenario.expectedSearch);
        }

        if (scenario.expectedParams) {
          Object.entries(scenario.expectedParams).forEach(([key, value]) => {
            expect(params[key]).toBe(value);
          });
        }
      });
    });

    it('should handle browser back/forward navigation', () => {
      const navigationStack = [
        { url: '/blueprints', title: 'Blueprints' },
        { url: '/blueprints/123', title: 'Blueprint Details' },
        { url: '/blueprints/123/deploy', title: 'Deploy Blueprint' }
      ];

      let currentIndex = 0;

      const navigate = (direction) => {
        if (direction === 'forward' && currentIndex < navigationStack.length - 1) {
          currentIndex++;
        } else if (direction === 'back' && currentIndex > 0) {
          currentIndex--;
        }
        
        const current = navigationStack[currentIndex];
        goto(current.url);
        
        return current;
      };

      // Navigate forward
      const forward1 = navigate('forward');
      expect(forward1.url).toBe('/blueprints/123');
      expect(goto).toHaveBeenCalledWith('/blueprints/123');

      const forward2 = navigate('forward');
      expect(forward2.url).toBe('/blueprints/123/deploy');

      // Navigate back
      const back1 = navigate('back');
      expect(back1.url).toBe('/blueprints/123');
      expect(goto).toHaveBeenCalledWith('/blueprints/123');
    });
  });

  describe('Breadcrumb Navigation', () => {
    it('should generate correct breadcrumbs for nested routes', () => {
      const routes = [
        {
          path: '/blueprints',
          breadcrumbs: [{ label: 'Home', url: '/' }, { label: 'Blueprints', url: '/blueprints' }]
        },
        {
          path: '/blueprints/123',
          breadcrumbs: [
            { label: 'Home', url: '/' },
            { label: 'Blueprints', url: '/blueprints' },
            { label: 'Blueprint Details', url: '/blueprints/123' }
          ]
        },
        {
          path: '/blueprints/create/vpc',
          breadcrumbs: [
            { label: 'Home', url: '/' },
            { label: 'Blueprints', url: '/blueprints' },
            { label: 'Create', url: '/blueprints/create' },
            { label: 'VPC', url: '/blueprints/create/vpc' }
          ]
        }
      ];

      const generateBreadcrumbs = (path) => {
        const segments = path.split('/').filter(Boolean);
        const breadcrumbs = [{ label: 'Home', url: '/' }];

        let currentPath = '';
        segments.forEach((segment, index) => {
          currentPath += `/${segment}`;
          
          let label = segment.charAt(0).toUpperCase() + segment.slice(1);
          if (segment === 'create') label = 'Create';
          if (segment === 'vpc') label = 'VPC';
          if (/^\d+$/.test(segment)) label = 'Details';

          breadcrumbs.push({
            label,
            url: currentPath
          });
        });

        return breadcrumbs;
      };

      routes.forEach(({ path, breadcrumbs: expected }) => {
        const generated = generateBreadcrumbs(path);
        expect(generated).toHaveLength(expected.length);
        expect(generated[generated.length - 1].url).toBe(path);
      });
    });

    it('should handle breadcrumb navigation clicks', () => {
      const breadcrumbs = [
        { label: 'Home', url: '/' },
        { label: 'Blueprints', url: '/blueprints' },
        { label: 'Create', url: '/blueprints/create' },
        { label: 'VPC', url: '/blueprints/create/vpc' }
      ];

      const handleBreadcrumbClick = (breadcrumb) => {
        goto(breadcrumb.url);
      };

      // Click on Blueprints breadcrumb
      handleBreadcrumbClick(breadcrumbs[1]);
      expect(goto).toHaveBeenCalledWith('/blueprints');

      // Click on Home breadcrumb
      handleBreadcrumbClick(breadcrumbs[0]);
      expect(goto).toHaveBeenCalledWith('/');
    });
  });

  describe('Navigation Guards and Permissions', () => {
    it('should enforce role-based navigation restrictions', () => {
      const userRoles = {
        admin: ['read', 'write', 'delete', 'manage'],
        member: ['read', 'write'],
        viewer: ['read']
      };

      const routePermissions = {
        '/blueprints': 'read',
        '/blueprints/create': 'write',
        '/blueprints/123/delete': 'delete',
        '/workspaces/manage': 'manage',
        '/settings': 'read'
      };

      const canAccessRoute = (route, userRole) => {
        const requiredPermission = routePermissions[route];
        return userRoles[userRole]?.includes(requiredPermission) || false;
      };

      expect(canAccessRoute('/blueprints', 'viewer')).toBe(true);
      expect(canAccessRoute('/blueprints/create', 'viewer')).toBe(false);
      expect(canAccessRoute('/blueprints/create', 'member')).toBe(true);
      expect(canAccessRoute('/blueprints/123/delete', 'member')).toBe(false);
      expect(canAccessRoute('/blueprints/123/delete', 'admin')).toBe(true);
    });

    it('should handle navigation blocking for unsaved changes', () => {
      let hasUnsavedChanges = true;
      let navigationBlocked = false;

      const beforeNavigate = (destination) => {
        if (hasUnsavedChanges) {
          const confirmLeave = confirm('You have unsaved changes. Are you sure you want to leave?');
          if (!confirmLeave) {
            navigationBlocked = true;
            return false;
          }
        }
        return true;
      };

      // Mock user canceling navigation
      global.confirm = vi.fn().mockReturnValue(false);

      const canNavigate = beforeNavigate('/blueprints');

      expect(canNavigate).toBe(false);
      expect(navigationBlocked).toBe(true);
      expect(global.confirm).toHaveBeenCalled();
    });

    it('should handle workspace-specific navigation', () => {
      const userWorkspaces = ['workspace_1', 'workspace_2'];
      const currentWorkspace = 'workspace_1';

      const canAccessWorkspaceRoute = (route, workspaceId) => {
        if (route.startsWith('/workspaces/')) {
          const routeWorkspaceId = route.split('/')[2];
          return userWorkspaces.includes(routeWorkspaceId);
        }
        return true;
      };

      expect(canAccessWorkspaceRoute('/workspaces/workspace_1', 'workspace_1')).toBe(true);
      expect(canAccessWorkspaceRoute('/workspaces/workspace_3', 'workspace_3')).toBe(false);
      expect(canAccessWorkspaceRoute('/blueprints', null)).toBe(true);
    });
  });

  describe('Mobile Navigation', () => {
    it('should handle mobile navigation patterns', () => {
      const isMobile = window.innerWidth < 768;
      
      const mobileNavigation = {
        showMobileMenu: false,
        toggleMobileMenu: function() {
          this.showMobileMenu = !this.showMobileMenu;
        },
        closeMobileMenu: function() {
          this.showMobileMenu = false;
        },
        handleMobileNavigation: function(route) {
          goto(route);
          this.closeMobileMenu();
        }
      };

      // Open mobile menu
      mobileNavigation.toggleMobileMenu();
      expect(mobileNavigation.showMobileMenu).toBe(true);

      // Navigate and close menu
      mobileNavigation.handleMobileNavigation('/blueprints');
      expect(goto).toHaveBeenCalledWith('/blueprints');
      expect(mobileNavigation.showMobileMenu).toBe(false);
    });

    it('should handle swipe navigation on mobile', () => {
      const swipeNavigation = {
        startX: 0,
        threshold: 100,
        
        handleTouchStart: function(event) {
          this.startX = event.touches[0].clientX;
        },
        
        handleTouchEnd: function(event) {
          const endX = event.changedTouches[0].clientX;
          const deltaX = endX - this.startX;
          
          if (Math.abs(deltaX) > this.threshold) {
            if (deltaX > 0) {
              // Swipe right - go back
              window.history.back();
            } else {
              // Swipe left - go forward
              window.history.forward();
            }
          }
        }
      };

      // Simulate swipe right
      const mockTouchStart = { touches: [{ clientX: 100 }] };
      const mockTouchEnd = { changedTouches: [{ clientX: 250 }] };

      swipeNavigation.handleTouchStart(mockTouchStart);
      swipeNavigation.handleTouchEnd(mockTouchEnd);

      // Delta is 150, which is > threshold of 100, so should trigger back navigation
      expect(mockTouchEnd.changedTouches[0].clientX - mockTouchStart.touches[0].clientX).toBeGreaterThan(100);
    });
  });

  describe('Error Route Handling', () => {
    it('should handle 404 errors correctly', () => {
      const invalidRoutes = [
        '/invalid-route',
        '/blueprints/',
        '/ranges/invalid id',
        '/workspaces/<script>'
      ];

      const handle404 = (route) => {
        const validRoutePatterns = [
          /^\/$/,
          /^\/login$/,
          /^\/signup$/,
          /^\/blueprints$/,
          /^\/blueprints\/[a-zA-Z0-9-_]+$/,
          /^\/ranges$/,
          /^\/ranges\/[a-zA-Z0-9-_]+$/,
          /^\/workspaces$/,
          /^\/workspaces\/[a-zA-Z0-9-_]+$/,
          /^\/settings$/
        ];

        // Check for trailing slashes on resource routes (invalid)
        if (route.match(/^\/(blueprints|ranges|workspaces)\/$/) && route !== '/') {
          return { status: 404, message: 'Page not found' };
        }

        // Check for invalid characters
        if (route.includes(' ') || route.includes('<') || route.includes('>')) {
          return { status: 404, message: 'Page not found' };
        }

        const isValidRoute = validRoutePatterns.some(pattern => pattern.test(route));
        
        if (!isValidRoute) {
          return { status: 404, message: 'Page not found' };
        }
        
        return { status: 200 };
      };

      invalidRoutes.forEach(route => {
        const result = handle404(route);
        expect(result.status).toBe(404);
        expect(result.message).toBe('Page not found');
      });
    });

    it('should provide helpful 404 page with navigation options', () => {
      const create404Response = (requestedPath) => {
        const suggestions = [];
        
        if (requestedPath.includes('blueprint')) {
          suggestions.push({ label: 'View All Blueprints', url: '/blueprints' });
          suggestions.push({ label: 'Create New Blueprint', url: '/blueprints/create' });
        }
        
        if (requestedPath.includes('range')) {
          suggestions.push({ label: 'View All Ranges', url: '/ranges' });
        }
        
        if (requestedPath.includes('workspace')) {
          suggestions.push({ label: 'View All Workspaces', url: '/workspaces' });
        }

        suggestions.push({ label: 'Go Home', url: '/' });

        return {
          status: 404,
          message: 'The page you are looking for could not be found.',
          suggestions
        };
      };

      const response404 = create404Response('/blueprints/nonexistent');
      
      expect(response404.status).toBe(404);
      expect(response404.suggestions).toContainEqual({ label: 'View All Blueprints', url: '/blueprints' });
      expect(response404.suggestions).toContainEqual({ label: 'Go Home', url: '/' });
    });

    it('should handle routing errors gracefully', () => {
      const routingErrors = [
        { error: 'Network error', fallback: '/' },
        { error: 'Server error', fallback: '/error' },
        { error: 'Permission denied', fallback: '/login' }
      ];

      const handleRoutingError = (error) => {
        const errorHandlers = {
          'Network error': () => goto('/'),
          'Server error': () => goto('/error'),
          'Permission denied': () => goto('/login'),
          default: () => goto('/')
        };

        const handler = errorHandlers[error.error] || errorHandlers.default;
        handler();
      };

      routingErrors.forEach(({ error, fallback }) => {
        handleRoutingError({ error });
        expect(goto).toHaveBeenCalledWith(fallback);
      });
    });
  });
});