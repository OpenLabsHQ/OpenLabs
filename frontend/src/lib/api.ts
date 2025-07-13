import { config } from '$lib/config'
import logger from '$lib/utils/logger'
import type {
  ApiResponse,
  User,
  UserSecrets,
  LoginResponse,
  RegisterResponse,
  Job,
  JobSubmissionResponse,
  DeployedRange,
  RangeSSHKey,
  NetworkGraphData,
  BlueprintRange,
  PasswordUpdateRequest,
  PasswordUpdateResponse,
  AWSSecretsRequest,
  AWSSecretsResponse,
  AzureSecretsRequest,
  AzureSecretsResponse,
  DeployRangeRequest
} from '$lib/types/api'

// Get the API URL from our config
const API_URL = config.apiUrl

interface LoginCredentials {
  email: string
  password: string
}

interface RegisterData {
  name: string
  email: string
  password: string
}

async function apiRequest<T>(
  endpoint: string,
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' = 'GET',
  data?: Record<string, unknown>
): Promise<ApiResponse<T>> {
  try {
    // These headers will trigger a preflight request, but that's okay
    // since we'll configure the API server to handle CORS
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    }

    const options: RequestInit = {
      method,
      headers,
      // Include credentials to send cookies with cross-origin requests
      credentials: 'include',
    }

    if (data && (method === 'POST' || method === 'PUT')) {
      options.body = JSON.stringify(data)
    }

    const response = await fetch(`${API_URL}${endpoint}`, options)

    let result
    const contentType = response.headers.get('content-type')
    if (contentType && contentType.includes('application/json')) {
      result = await response.json()
    } else {
      const text = await response.text()
      result = text ? { message: text } : {}
    }

    if (!response.ok) {
      logger.error('API error', 'apiRequest', result)

      let errorMessage = ''
      let isAuthError = false

      switch (response.status) {
        case 401:
          errorMessage = 'Your session has expired. Please log in again.'
          isAuthError = true
          break
        case 403:
          errorMessage = "You don't have permission to access this resource."
          isAuthError = true
          break
        case 404:
          errorMessage = 'The requested information could not be found.'
          break
        case 500:
        case 502:
        case 503:
        case 504:
          errorMessage =
            'The server is currently unavailable. Please try again later.'
          break
        default:
          errorMessage =
            result.detail ||
            result.message ||
            `Something went wrong (${response.status})`
      }

      return {
        error: errorMessage,
        status: response.status,
        isAuthError,
      }
    }

    return { data: result }
  } catch (error) {
    logger.error('API request failed', 'apiRequest', error)

    let errorMessage = 'Unable to connect to the server.'

    if (error instanceof Error) {
      if (
        error.message.includes('Failed to fetch') ||
        error.message.includes('NetworkError')
      ) {
        errorMessage = 'Network error: Please check your internet connection.'
      } else if (
        error.message.includes('timeout') ||
        error.message.includes('Timeout')
      ) {
        errorMessage = 'Request timed out. Please try again later.'
      } else {
        errorMessage =
          'Something went wrong while connecting to the server. Please try again.'
      }
    }

    return { error: errorMessage }
  }
}

// Auth API
// Import auth store
import { auth } from '$lib/stores/auth'

// User API for managing user settings
export const userApi = {
  // Get user secrets status
  getUserSecrets: async (): Promise<ApiResponse<UserSecrets>> => {
    return await apiRequest<UserSecrets>(
      '/api/v1/users/me/secrets',
      'GET'
    )
  },

  // Update user password
  updatePassword: async (currentPassword: string, newPassword: string): Promise<ApiResponse<PasswordUpdateResponse>> => {
    const request: PasswordUpdateRequest = {
      current_password: currentPassword,
      new_password: newPassword,
    }
    return await apiRequest<PasswordUpdateResponse>(
      '/api/v1/users/me/password',
      'POST',
      request
    )
  },

  // Set AWS secrets
  setAwsSecrets: async (accessKey: string, secretKey: string): Promise<ApiResponse<AWSSecretsResponse>> => {
    const request: AWSSecretsRequest = {
      aws_access_key: accessKey,
      aws_secret_key: secretKey,
    }
    return await apiRequest<AWSSecretsResponse>(
      '/api/v1/users/me/secrets/aws',
      'POST',
      request
    )
  },

  // Set Azure secrets
  setAzureSecrets: async (
    clientId: string,
    clientSecret: string,
    tenantId: string,
    subscriptionId: string
  ): Promise<ApiResponse<AzureSecretsResponse>> => {
    const request: AzureSecretsRequest = {
      azure_client_id: clientId,
      azure_client_secret: clientSecret,
      azure_tenant_id: tenantId,
      azure_subscription_id: subscriptionId,
    }
    return await apiRequest<AzureSecretsResponse>(
      '/api/v1/users/me/secrets/azure',
      'POST',
      request
    )
  },
}

export const authApi = {
  login: async (credentials: LoginCredentials): Promise<ApiResponse<LoginResponse>> => {
    try {
      const loginData = {
        email: credentials.email,
        password: credentials.password,
      }

      // Clear previous auth state but don't redirect
      // This was calling auth.logout() which might trigger a redirect
      auth.updateUser({})

      // Set authenticated to false without triggering navigation
      auth.updateAuthState(false)

      const response = await fetch(`${API_URL}/api/v1/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(loginData),
        // Use include to allow cookie setting in cross-origin requests
        credentials: 'include',
      })

      if (!response.ok) {
        let errorMsg = `Login failed with status ${response.status}`
        try {
          const errorData = await response.json()
          logger.error('Login error response', 'authApi.login', errorData)
          errorMsg = errorData.detail || errorMsg

          // Improved error messages for common login failures
          if (response.status === 401) {
            errorMsg = 'Invalid email or password. Please try again.'
          } else if (response.status === 403) {
            errorMsg = 'Your account is locked. Please contact support.'
          } else if (errorData.detail) {
            errorMsg = errorData.detail
          }
        } catch {
          const errorText = await response.text()
          if (errorText) errorMsg = errorText
        }
        return { error: errorMsg }
      }

      const data = await response.json()
      return { data }
    } catch (error) {
      return {
        error: error instanceof Error ? error.message : 'Login failed',
      }
    }
  },

  register: async (userData: RegisterData): Promise<ApiResponse<RegisterResponse>> => {
    try {
      const response = await fetch(`${API_URL}/api/v1/auth/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: userData.email,
          password: userData.password,
          name: userData.name,
        }),
        // Use include to allow cookie setting in cross-origin requests
        credentials: 'include',
      })

      if (!response.ok) {
        try {
          const errorData = await response.json()

          // For 422 validation errors, FastAPI returns detailed validation error objects
          if (
            response.status === 422 &&
            errorData.detail &&
            Array.isArray(errorData.detail)
          ) {
            // Extract the validation message from the detail array
            const validationErrors = errorData.detail.map(
              (error: { msg: string }) => error.msg
            )
            return { error: validationErrors.join(', ') }
          }

          // For other errors, use the detail field or default message
          return {
            error:
              errorData.detail ||
              `Registration failed with status ${response.status}`,
          }
        } catch {
          // Use the status message if we can't parse the response
          return { error: `Registration failed with status ${response.status}` }
        }
      }

      const data = await response.json()
      return { data }
    } catch (error) {
      logger.error('Registration error', 'authApi.register', error)
      return {
        error: error instanceof Error ? error.message : 'Registration failed',
      }
    }
  },

  // Get current user information or verify authentication
  getCurrentUser: async (): Promise<ApiResponse<{ user: User }>> => {
    try {
      // Get user information from the /api/v1/users/me endpoint
      const userResponse = await apiRequest<User>(
        '/api/v1/users/me',
        'GET'
      )

      // If we get data back, we're authenticated and have user info
      if (userResponse.data) {
        return {
          data: { user: { ...userResponse.data, authenticated: true } },
          status: 200,
        }
      }

      // If we get an auth error, pass it through
      if (
        userResponse.isAuthError ||
        userResponse.status === 401 ||
        userResponse.status === 403
      ) {
        return {
          error: 'Authentication failed',
          isAuthError: true,
          status: userResponse.status || 401,
        }
      }

      // For other errors, we'll assume auth is OK if there's a non-auth error
      // like 404 or 500 - this prevents logout on API issues
      return {
        data: { user: { authenticated: true } },
        status: 200,
      }
    } catch (error) {
      logger.error('Error during authentication check', 'authApi.getCurrentUser', error)
      // Don't treat exceptions as auth failures
      return {
        data: { user: { authenticated: true } },
        error:
          error instanceof Error
            ? error.message
            : 'Error during authentication check',
        status: 200,
      }
    }
  },

  // Logout by making a request to the server to clear the auth cookie
  logout: async () => {
    try {
      const response = await fetch(`${API_URL}/api/v1/auth/logout`, {
        method: 'POST',
        credentials: 'include',
      })

      return { success: response.ok }
    } catch (error) {
      logger.error('Logout error', 'authApi.logout', error)
      return { error: error instanceof Error ? error.message : 'Logout failed' }
    }
  },
}

export const rangesApi = {
  getRanges: async (): Promise<ApiResponse<DeployedRange[]>> => {
    return await apiRequest<DeployedRange[]>('/api/v1/ranges', 'GET')
  },

  // Get a specific range by ID
  getRangeById: async (id: string): Promise<ApiResponse<DeployedRange>> => {
    return await apiRequest<DeployedRange>(`/api/v1/ranges/${id}`, 'GET')
  },

  // Get SSH key for a range
  getRangeSSHKey: async (id: string): Promise<ApiResponse<RangeSSHKey>> => {
    return await apiRequest<RangeSSHKey>(`/api/v1/ranges/${id}/key`, 'GET')
  },

  // Get network graph data for a range
  getRangeNetworkGraph: async (id: string): Promise<ApiResponse<NetworkGraphData>> => {
    return await apiRequest<NetworkGraphData>(`/api/v1/ranges/${id}/network-graph`, 'GET')
  },

  // Delete a range by ID (returns job submission response)
  deleteRange: async (id: string): Promise<ApiResponse<JobSubmissionResponse>> => {
    return await apiRequest<JobSubmissionResponse>(`/api/v1/ranges/${id}`, 'DELETE')
  },

  // Get job status by ID
  getJobStatus: async (jobId: string): Promise<ApiResponse<Job>> => {
    return await apiRequest<Job>(`/api/v1/jobs/${jobId}`, 'GET')
  },

  // Get all jobs with optional status filter
  getJobs: async (status?: string): Promise<ApiResponse<Job[]>> => {
    const query = status ? `?job_status=${status}` : ''
    return await apiRequest<Job[]>(`/api/v1/jobs${query}`, 'GET')
  },

  getBlueprints: async (): Promise<ApiResponse<BlueprintRange[]>> => {
    return await apiRequest<BlueprintRange[]>(
      '/api/v1/blueprints/ranges',
      'GET'
    )
  },

  getBlueprintById: async (id: string): Promise<ApiResponse<BlueprintRange>> => {
    return await apiRequest<BlueprintRange>(
      `/api/v1/blueprints/ranges/${id}`,
      'GET'
    )
  },

  createBlueprint: async (blueprintData: BlueprintRange): Promise<ApiResponse<BlueprintRange>> => {
    return await apiRequest<BlueprintRange>(
      '/api/v1/blueprints/ranges',
      'POST',
      blueprintData
    )
  },

  // Deploy a range from a blueprint (returns job submission response)
  deployBlueprint: async (
    blueprintId: string,
    name: string,
    description: string,
    region: 'us_east_1' | 'us_east_2',
    readme?: string
  ): Promise<ApiResponse<JobSubmissionResponse>> => {
    const request: DeployRangeRequest = {
      blueprint_id: parseInt(blueprintId), // Convert to int as IDs are now integers
      name,
      description,
      region,
      readme: readme || null
    }
    return await apiRequest<JobSubmissionResponse>(
      '/api/v1/ranges/deploy',
      'POST',
      request
    )
  },

  // Delete a blueprint by ID
  deleteBlueprint: async (blueprintId: string): Promise<ApiResponse<{ success: boolean }>> => {
    return await apiRequest<{ success: boolean }>(
      `/api/v1/blueprints/ranges/${blueprintId}`,
      'DELETE'
    )
  },
}

// Job polling utility function
export async function pollJobUntilComplete(
  jobId: string, 
  onProgress?: (job: Job) => void,
  interval: number = 30000, // 30 seconds default
  maxDuration: number = 1800000 // 30 minutes timeout
): Promise<ApiResponse<Job>> {
  const startTime = Date.now()
  
  const poll = async (): Promise<ApiResponse<Job>> => {
    try {
      const response = await rangesApi.getJobStatus(jobId)
      
      if (response.error) {
        return response
      }
      
      const job = response.data as Job
      
      // Call progress callback if provided
      if (onProgress) {
        onProgress(job)
      }
      
      // Check if job is complete
      if (job.status === 'complete' || job.status === 'failed') {
        return { data: job }
      }
      
      // Check timeout
      if (Date.now() - startTime > maxDuration) {
        return { error: 'Job polling timeout after 30 minutes' }
      }
      
      // Continue polling
      await new Promise(resolve => setTimeout(resolve, interval))
      return poll()
      
    } catch (error) {
      return { error: error instanceof Error ? error.message : 'Polling failed' }
    }
  }
  
  return poll()
}

export const blueprintsApi = {
  getVpcBlueprints: async () => {
    return await rangesApi.getRanges()
  },
}

// Import workspace types
import type {
  Workspace,
  WorkspaceUser,
  WorkspaceCreate,
  WorkspaceUpdate,
  WorkspaceUserCreate,
  AvailableUser
} from './types/workspaces';

export const workspacesApi = {
  // Get all workspaces the user has access to
  getWorkspaces: async () => {
    return await apiRequest<Workspace[]>('/api/v1/workspaces', 'GET')
  },

  // Create a new workspace
  createWorkspace: async (data: WorkspaceCreate) => {
    return await apiRequest<Workspace>('/api/v1/workspaces', 'POST', data)
  },

  // Get a specific workspace by ID
  getWorkspaceById: async (id: string) => {
    return await apiRequest<Workspace>(`/api/v1/workspaces/${id}`, 'GET')
  },

  // Update a workspace
  updateWorkspace: async (id: string, data: WorkspaceUpdate) => {
    return await apiRequest<Workspace>(`/api/v1/workspaces/${id}`, 'PUT', data)
  },

  // Delete a workspace
  deleteWorkspace: async (id: string) => {
    return await apiRequest<{success: boolean}>(`/api/v1/workspaces/${id}`, 'DELETE')
  },

  // Get all users in a workspace
  getWorkspaceUsers: async (workspaceId: string) => {
    return await apiRequest<WorkspaceUser[]>(
      `/api/v1/workspaces/${workspaceId}/users`,
      'GET'
    )
  },

  // Add a user to a workspace
  addWorkspaceUser: async (workspaceId: string, data: WorkspaceUserCreate) => {
    return await apiRequest<WorkspaceUser>(
      `/api/v1/workspaces/${workspaceId}/users`,
      'POST',
      data
    )
  },

  // Remove a user from a workspace
  removeWorkspaceUser: async (workspaceId: string, userId: string) => {
    return await apiRequest<{success: boolean}>(
      `/api/v1/workspaces/${workspaceId}/users/${userId}`,
      'DELETE'
    )
  },

  // Update user role in workspace (promote/demote)
  updateWorkspaceUserRole: async (workspaceId: string, userId: string, role: 'admin' | 'member') => {
    return await apiRequest<WorkspaceUser>(
      `/api/v1/workspaces/${workspaceId}/users/${userId}`,
      'PUT',
      { role }
    )
  },

  // Get users not yet in the workspace
  getAvailableUsers: async (workspaceId: string) => {
    return await apiRequest<AvailableUser[]>(
      `/api/v1/workspaces/${workspaceId}/available-users`,
      'GET'
    )
  },
  
  // Get all users in the system
  getAllUsers: async () => {
    return await apiRequest<AvailableUser[]>(
      '/api/v1/users',
      'GET'
    )
  },

  // Get blueprints shared in a workspace
  getWorkspaceBlueprints: async (workspaceId: string) => {
    return await apiRequest<BlueprintRange[]>(
      `/api/v1/workspaces/${workspaceId}/blueprints`,
      'GET'
    )
  },

  // Share a blueprint with a workspace
  shareBlueprintWithWorkspace: async (workspaceId: string, blueprintId: string) => {
    return await apiRequest<{success: boolean}>(
      `/api/v1/workspaces/${workspaceId}/blueprints`,
      'POST',
      { 
        blueprint_id: parseInt(blueprintId)
      }
    )
  },

  // Remove a blueprint from a workspace
  // Note: blueprintId should be the actual blueprint ID (not the sharing record ID)
  removeBlueprintFromWorkspace: async (workspaceId: string, blueprintId: string) => {
    return await apiRequest<{success: boolean}>(
      `/api/v1/workspaces/${workspaceId}/blueprints/${blueprintId}`,
      'DELETE'
    )
  },
}

export default {
  auth: authApi,
  user: userApi,
  ranges: rangesApi,
  blueprints: blueprintsApi,
  workspaces: workspacesApi,
}
