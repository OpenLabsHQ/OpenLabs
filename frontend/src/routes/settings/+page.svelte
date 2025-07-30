<script lang="ts">
  import { onMount } from 'svelte'
  import { userApi } from '$lib/api'
  import { auth } from '$lib/stores/auth'
  import AuthGuard from '$lib/components/AuthGuard.svelte'
  import LoadingSpinner from '$lib/components/LoadingSpinner.svelte'
  import { fade } from 'svelte/transition'
  import logger from '$lib/utils/logger'

  // Active tab state
  let activeTab: 'aws' | 'azure' = 'aws'

  // Password form
  let currentPassword = ''
  let newPassword = ''
  let confirmPassword = ''
  let passwordError = ''
  let passwordSuccess = ''
  let isPasswordLoading = false

  // AWS secrets form
  let awsAccessKey = ''
  let awsSecretKey = ''
  let awsError = ''
  let awsSuccess = ''
  let isAwsLoading = false

  // Azure secrets form
  let azureClientId = ''
  let azureClientSecret = ''
  let azureTenantId = ''
  let azureSubscriptionId = ''
  let azureError = ''
  let azureSuccess = ''
  let isAzureLoading = false

  // User data
  let userData = {
    name: '',
    email: '',
  }

  // Secrets status
  let secretsStatus = {
    aws: {
      configured: false,
      createdAt: null as string | null,
    },
    azure: {
      configured: false,
      createdAt: null as string | null,
    },
  }
  let loadingSecrets = true
  let loadingUserData = true

  // Format date for tooltip display
  function formatDateForTooltip(dateString: string | null) {
    if (!dateString) return 'Date unavailable'
    try {
      return `Configured on ${new Date(dateString).toLocaleString()}`
    } catch (e) {
      logger.error('Error formatting date', 'settings', e)
      return 'Configured (date format error)'
    }
  }

  // Helper for tab styling
  function getTabClass(tabName: 'aws' | 'azure') {
    const baseClasses = 'whitespace-nowrap border-b-2 px-1 py-4 text-sm font-medium'
    const inactiveClasses = 'border-transparent text-gray-400 hover:border-gray-500 hover:text-gray-300'
    
    if (activeTab === tabName) {
      const activeClasses = tabName === 'aws' 
        ? 'border-yellow-500 text-yellow-500' 
        : 'border-blue-500 text-blue-500'
      return `${baseClasses} ${activeClasses}`
    }
    
    return `${baseClasses} ${inactiveClasses}`
  }

  // Custom tooltip management
  let showTooltip = false
  let tooltipPosition = { x: 0, y: 0 }

  function handleMouseEnter(event: MouseEvent) {
    const rect = (event.target as HTMLElement).getBoundingClientRect()
    tooltipPosition = {
      x: rect.left + window.scrollX + rect.width / 2,
      y: rect.top + window.scrollY - 10,
    }
    showTooltip = true
  }

  function handleMouseLeave() {
    showTooltip = false
  }

  // Load user data and secrets status
  onMount(async () => {
    loadingUserData = true
    try {
      const { authApi } = await import('$lib/api')
      const userResponse = await authApi.getCurrentUser()
      if (userResponse.data?.user) {
        userData = {
          name: userResponse.data.user.name || '',
          email: userResponse.data.user.email || '',
        }
        auth.updateUser(userResponse.data.user)
      }
    } catch (error) {
      logger.error('Failed to load user data', 'settings', error)
    } finally {
      loadingUserData = false
    }

    loadingSecrets = true
    try {
      const result = await userApi.getUserSecrets()
      if (result.data) {
        secretsStatus = {
          aws: {
            configured: result.data.aws?.has_credentials || false,
            createdAt: result.data.aws?.created_at || null,
          },
          azure: {
            configured: result.data.azure?.has_credentials || false,
            createdAt: result.data.azure?.created_at || null,
          },
        }
      }
    } catch (error) {
      logger.error('Failed to load secrets status', 'settings', error)
    } finally {
      loadingSecrets = false
    }
  })

  // Handle password update
  async function handlePasswordUpdate() {
    passwordError = ''
    passwordSuccess = ''
    if (!currentPassword || !newPassword) {
      passwordError = 'All password fields are required'
      return
    }
    if (newPassword !== confirmPassword) {
      passwordError = 'New passwords do not match'
      return
    }
    if (newPassword.length < 8) {
      passwordError = 'Password must be at least 8 characters long'
      return
    }
    isPasswordLoading = true
    try {
      const result = await userApi.updatePassword(currentPassword, newPassword)
      if (result.error) {
        passwordError = result.error
        return
      }
      passwordSuccess = 'Password updated successfully'
      currentPassword = ''
      newPassword = ''
      confirmPassword = ''
    } catch (error) {
      passwordError =
        error instanceof Error ? error.message : 'Failed to update password'
    } finally {
      isPasswordLoading = false
    }
  }

  // Shared function to call the single endpoint
  async function updateSecrets(provider: 'aws' | 'azure', payload: any) {
    // Set loading state based on provider
    if (provider === 'aws') {
      isAwsLoading = true
    } else {
      isAzureLoading = true
    }

    try {
      // Call single, common endpoint
      const result = await userApi.updateSecrets(provider, payload)

      if (result.error) {
        if (provider === 'aws') awsError = result.error
        else azureError = result.error
        return
      }

      // Handle success based on provider
      if (provider === 'aws') {
        awsSuccess = 'AWS credentials updated successfully'
        secretsStatus.aws = { configured: true, createdAt: new Date().toISOString() }
        awsAccessKey = ''
        awsSecretKey = ''
      } else {
        azureSuccess = 'Azure credentials updated successfully'
        secretsStatus.azure = { configured: true, createdAt: new Date().toISOString() }
        azureClientId = ''
        azureClientSecret = ''
        azureTenantId = ''
        azureSubscriptionId = ''
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to update credentials'
      if (provider === 'aws') awsError = errorMessage
      else azureError = errorMessage
    } finally {
      // Reset loading state based on provider
      if (provider === 'aws') isAwsLoading = false
      else isAzureLoading = false
    }
  }

  // Handle AWS secrets update
  async function handleAwsSecretsUpdate() {
    awsError = ''
    awsSuccess = ''
    if (!awsAccessKey || !awsSecretKey) {
      awsError = 'Both AWS Access Key and Secret Key are required'
      return
    }
    
    // Construct the AWS-specific payload
    const payload = {
        aws_access_key: awsAccessKey,
        aws_secret_key: awsSecretKey,
    }

    // Call the shared update function
    await updateSecrets('aws', payload)
  }

  // Handle Azure secrets update
  async function handleAzureSecretsUpdate() {
    azureError = ''
    azureSuccess = ''
    if (
      !azureClientId ||
      !azureClientSecret ||
      !azureTenantId ||
      !azureSubscriptionId
    ) {
      azureError = 'All Azure fields are required'
      return
    }
    
    // Construct the Azure-specific payload
    const payload = {
        azure_client_id: azureClientId,
        azure_client_secret: azureClientSecret,
        azure_tenant_id: azureTenantId,
        azure_subscription_id: azureSubscriptionId,
    }
    
    // Call the shared update function
    await updateSecrets('azure', payload)
  }
</script>

<AuthGuard requireAuth={true} redirectTo="/login">
  <div class="relative min-h-screen bg-gray-900 p-4 sm:p-8 text-white">
    <div class="mx-auto max-w-4xl">
      <div class="mb-8">
        <div class="mb-4">
          <button
            on:click={() => window.history.back()}
            class="flex w-fit cursor-pointer items-center border-none bg-transparent text-blue-500 hover:text-blue-700"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="mr-1 h-5 w-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M10 19l-7-7m0 0l7-7m-7 7h18"
              />
            </svg>
            Back
          </button>
        </div>
        <h1 class="text-3xl font-bold">Account Settings</h1>
      </div>

      <!-- User info -->
      <div class="mb-8 rounded-lg bg-gray-800 p-6">
        <h2 class="mb-4 text-2xl font-semibold">User Information</h2>
        {#if loadingUserData}
          <div class="flex justify-center py-4">
            <LoadingSpinner size="md" />
          </div>
        {:else}
          <div class="flex items-center space-x-4">
            <div
              class="flex h-16 w-16 items-center justify-center rounded-full bg-gray-700 text-2xl"
            >
              {userData.name?.[0]?.toUpperCase() || 'U'}
            </div>
            <div>
              <p class="text-xl font-medium">{userData.name || 'User'}</p>
              <p class="text-gray-400">
                {userData.email || 'email@example.com'}
              </p>
            </div>
          </div>
        {/if}
      </div>

      <!-- Password change -->
      <div class="mb-8 rounded-lg bg-gray-800 p-6">
        <h2 class="mb-4 text-2xl font-semibold">Change Password</h2>
        <form on:submit|preventDefault={handlePasswordUpdate} class="space-y-4">
          <div>
            <label
              for="current-password"
              class="mb-1 block text-sm font-medium text-gray-300"
            >
              Current Password
            </label>
            <input
              id="current-password"
              type="password"
              bind:value={currentPassword}
              class="w-full rounded-md border border-gray-700 bg-gray-900 px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Enter current password"
            />
          </div>
          <div>
            <label
              for="new-password"
              class="mb-1 block text-sm font-medium text-gray-300"
            >
              New Password
            </label>
            <input
              id="new-password"
              type="password"
              bind:value={newPassword}
              class="w-full rounded-md border border-gray-700 bg-gray-900 px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Enter new password"
            />
          </div>
          <div>
            <label
              for="confirm-password"
              class="mb-1 block text-sm font-medium text-gray-300"
            >
              Confirm New Password
            </label>
            <input
              id="confirm-password"
              type="password"
              bind:value={confirmPassword}
              class="w-full rounded-md border border-gray-700 bg-gray-900 px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Confirm new password"
            />
          </div>
          {#if passwordError}
            <div class="text-sm text-red-500">{passwordError}</div>
          {/if}
          {#if passwordSuccess}
            <div class="text-sm text-green-500">{passwordSuccess}</div>
          {/if}
          <button
            type="submit"
            disabled={isPasswordLoading}
            class="rounded-md bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-gray-900 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {#if isPasswordLoading}
              <span class="mr-2 inline-block">
                <LoadingSpinner size="sm" color="white" />
              </span>
              Updating...
            {:else}
              Update Password
            {/if}
          </button>
        </form>
      </div>

      <!-- Cloud Provider Credentials with Tabs -->
      <div class="rounded-lg bg-gray-800 p-6">
        <div class="mb-4 flex items-center justify-between">
            <h2 class="text-2xl font-semibold">Cloud Provider Credentials</h2>
            <div class="group relative">
              <button class="flex h-6 w-6 items-center justify-center rounded-full bg-gray-700 text-gray-300 hover:bg-gray-600 focus:outline-none" aria-label="Encryption information">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
              </button>
              <div class="pointer-events-none absolute right-0 z-50 mt-2 w-72 rounded-md bg-gray-900 px-4 py-3 text-sm text-white opacity-0 shadow-lg transition-opacity duration-200 group-hover:opacity-100">
                <div class="mb-2 flex items-center text-green-400">
                  <svg xmlns="http://www.w3.org/2000/svg" class="mr-2 h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" /></svg>
                  <span class="font-semibold">End-to-End Encrypted</span>
                </div>
                <p>Your credentials are encrypted before being stored and are only decrypted when needed for a range. We cannot access your cloud provider credentials.</p>
                <div class="tooltip-arrow absolute h-2 w-2 rotate-45 transform bg-gray-900" style="top: -4px; right: 10px;"></div>
              </div>
            </div>
        </div>

        {#if loadingSecrets}
          <div class="flex justify-center py-8">
            <LoadingSpinner size="md" />
          </div>
        {:else}
          <div>
            <!-- Tab Navigation -->
            <div class="mb-4 border-b border-gray-700">
              <nav class="-mb-px flex space-x-4" aria-label="Tabs">
                <button
                  on:click={() => (activeTab = 'aws')}
                  class={getTabClass('aws')}
                >
                  AWS
                </button>
                <button
                  on:click={() => (activeTab = 'azure')}
                  class={getTabClass('azure')}
                >
                  Azure
                </button>
              </nav>
            </div>

            <!-- Tab Content -->
            <div class="pt-4" style="min-height: 380px;">
              {#if activeTab === 'aws'}
                <div transition:fade={{ duration: 150, delay: 100 }}>
                  <div class="mb-4 flex items-center justify-between">
                    <h3 class="text-xl font-medium">AWS Credentials</h3>
                    <span
                      role="status"
                      aria-label={secretsStatus.aws.configured ? formatDateForTooltip(secretsStatus.aws.createdAt) : 'AWS credentials not configured'}
                      class={`${secretsStatus.aws.configured ? 'bg-green-500' : 'bg-gray-500'} relative cursor-pointer rounded-full px-2 py-1 text-xs font-semibold`}
                      on:mouseenter={handleMouseEnter}
                      on:mouseleave={handleMouseLeave}
                    >
                      {secretsStatus.aws.configured ? 'Configured' : 'Not Configured'}
                    </span>
                  </div>
                  <form on:submit|preventDefault={handleAwsSecretsUpdate} class="space-y-4">
                    <div>
                      <label for="aws-access-key" class="mb-1 block text-sm font-medium text-gray-300">Access Key</label>
                      <input id="aws-access-key" type="text" bind:value={awsAccessKey} class="w-full rounded-md border border-gray-600 bg-gray-800 px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-yellow-500" placeholder="Enter AWS Access Key" />
                    </div>
                    <div>
                      <label for="aws-secret-key" class="mb-1 block text-sm font-medium text-gray-300">Secret Key</label>
                      <input id="aws-secret-key" type="password" bind:value={awsSecretKey} class="w-full rounded-md border border-gray-600 bg-gray-800 px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-yellow-500" placeholder="Enter AWS Secret Key" />
                    </div>
                    {#if awsError}<div class="text-sm text-red-500">{awsError}</div>{/if}
                    {#if awsSuccess}<div class="text-sm text-green-500">{awsSuccess}</div>{/if}
                    <div class="pt-4">
                      <button type="submit" disabled={isAwsLoading} class="w-full rounded-md bg-yellow-600 px-4 py-2 font-medium text-white hover:bg-yellow-700 focus:outline-none focus:ring-2 focus:ring-yellow-500 focus:ring-offset-2 focus:ring-offset-gray-900 disabled:cursor-not-allowed disabled:opacity-50">
                        {#if isAwsLoading}<span class="mr-2 inline-block"><LoadingSpinner size="sm" color="white" /></span>Updating...{:else}{secretsStatus.aws.configured ? 'Update' : 'Set'} AWS Credentials{/if}
                      </button>
                    </div>
                  </form>
                </div>
              {:else if activeTab === 'azure'}
                <div transition:fade={{ duration: 150, delay: 100 }}>
                   <div class="mb-4 flex items-center justify-between">
                    <h3 class="text-xl font-medium">Azure Credentials</h3>
                    <span
                      role="status"
                      aria-label={secretsStatus.azure.configured ? formatDateForTooltip(secretsStatus.azure.createdAt) : 'Azure credentials not configured'}
                      class={`${secretsStatus.azure.configured ? 'bg-green-500' : 'bg-gray-500'} relative cursor-pointer rounded-full px-2 py-1 text-xs font-semibold`}
                      on:mouseenter={handleMouseEnter}
                      on:mouseleave={handleMouseLeave}
                    >
                      {secretsStatus.azure.configured ? 'Configured' : 'Not Configured'}
                    </span>
                  </div>
                  <form on:submit|preventDefault={handleAzureSecretsUpdate} class="space-y-4">
                     <div>
                      <label for="azure-client-id" class="mb-1 block text-sm font-medium text-gray-300">Client ID</label>
                      <input id="azure-client-id" type="text" bind:value={azureClientId} class="w-full rounded-md border border-gray-600 bg-gray-800 px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500" placeholder="Enter Azure Client ID" />
                    </div>
                    <div>
                      <label for="azure-client-secret" class="mb-1 block text-sm font-medium text-gray-300">Client Secret</label>
                      <input id="azure-client-secret" type="password" bind:value={azureClientSecret} class="w-full rounded-md border border-gray-600 bg-gray-800 px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500" placeholder="Enter Azure Client Secret" />
                    </div>
                    <div>
                      <label for="azure-tenant-id" class="mb-1 block text-sm font-medium text-gray-300">Tenant ID</label>
                      <input id="azure-tenant-id" type="text" bind:value={azureTenantId} class="w-full rounded-md border border-gray-600 bg-gray-800 px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500" placeholder="Enter Azure Tenant ID" />
                    </div>
                    <div>
                      <label for="azure-subscription-id" class="mb-1 block text-sm font-medium text-gray-300">Subscription ID</label>
                      <input id="azure-subscription-id" type="text" bind:value={azureSubscriptionId} class="w-full rounded-md border border-gray-600 bg-gray-800 px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500" placeholder="Enter Azure Subscription ID" />
                    </div>
                    {#if azureError}<div class="text-sm text-red-500">{azureError}</div>{/if}
                    {#if azureSuccess}<div class="text-sm text-green-500">{azureSuccess}</div>{/if}
                    <div class="pt-4">
                       <button type="submit" disabled={isAzureLoading} class="w-full rounded-md bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-gray-900 disabled:cursor-not-allowed disabled:opacity-50">
                        {#if isAzureLoading}<span class="mr-2 inline-block"><LoadingSpinner size="sm" color="white" /></span>Updating...{:else}{secretsStatus.azure.configured ? 'Update' : 'Set'} Azure Credentials{/if}
                      </button>
                    </div>
                  </form>
                </div>
              {/if}
            </div>
          </div>
        {/if}
      </div>
    </div>

    <!-- Tooltip -->
    {#if showTooltip}
      {@const status = activeTab === 'aws' ? secretsStatus.aws : secretsStatus.azure}
      {#if status.configured}
        <div
          transition:fade={{ duration: 150 }}
          class="absolute z-50 -translate-x-1/2 transform rounded-md bg-gray-900 px-3 py-2 pb-3 text-sm text-white shadow-lg"
          style="left: {tooltipPosition.x}px; top: {tooltipPosition.y}px; pointer-events: none;"
        >
          {formatDateForTooltip(status.createdAt)}
          <div
            class="tooltip-arrow absolute h-2 w-2 rotate-45 transform bg-gray-900"
            style="left: 50%; bottom: -4px; margin-left: -4px;"
          ></div>
        </div>
      {/if}
    {/if}
  </div>
</AuthGuard>
