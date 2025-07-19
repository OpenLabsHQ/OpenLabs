<script lang="ts">
  import { onMount } from 'svelte'
  import { userApi } from '$lib/api'
  import { auth } from '$lib/stores/auth'
  import AuthGuard from '$lib/components/AuthGuard.svelte'
  import LoadingSpinner from '$lib/components/LoadingSpinner.svelte'
  import { fade } from 'svelte/transition'
  import logger from '$lib/utils/logger'

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
      createdAt: null,
    },
    azure: {
      configured: false,
      createdAt: null,
    },
  }
  let loadingSecrets = true
  let loadingUserData = true

  // Format date for tooltip display
  function formatDateForTooltip(dateString) {
    if (!dateString) return 'Date unavailable'
    try {
      return `Configured on ${new Date(dateString).toLocaleString()}`
    } catch (e) {
      logger.error('Error formatting date', 'settings', e)
      return 'Configured (date format error)'
    }
  }

  // Custom tooltip management
  let showAwsTooltip = false
  let showAzureTooltip = false

  // Position tracking for tooltips
  let awsTooltipPosition = { x: 0, y: 0 }
  let azureTooltipPosition = { x: 0, y: 0 }

  function handleMouseEnter(event, tooltipType) {
    // Calculate position for tooltip
    const rect = event.target.getBoundingClientRect()
    const position = {
      x: rect.left + window.scrollX + rect.width / 2, // Center horizontally
      y: rect.top + window.scrollY - 40, // Position higher above the element
    }

    // Set position and show appropriate tooltip
    if (tooltipType === 'aws') {
      awsTooltipPosition = position
      showAwsTooltip = true
    } else if (tooltipType === 'azure') {
      azureTooltipPosition = position
      showAzureTooltip = true
    }
  }

  function handleMouseLeave(tooltipType) {
    if (tooltipType === 'aws') {
      showAwsTooltip = false
    } else if (tooltipType === 'azure') {
      showAzureTooltip = false
    }
  }

  // Load user data and secrets status
  onMount(async () => {
    try {
      // Load user data first
      const { authApi } = await import('$lib/api')
      const userResponse = await authApi.getCurrentUser()

      if (userResponse.data?.user) {
        userData = {
          name: userResponse.data.user.name || '',
          email: userResponse.data.user.email || '',
        }

        // Update auth store
        auth.updateUser(userResponse.data.user)
      }
    } catch (error) {
      logger.error('Failed to load user data', 'settings', error)
    } finally {
      loadingUserData = false
    }

    try {
      // Then load secrets status
      const result = await userApi.getUserSecrets()

      if (result.data) {
        const awsDate = result.data.aws?.created_at
        const azureDate = result.data.azure?.created_at

        secretsStatus = {
          aws: {
            configured: result.data.aws?.has_credentials || false,
            createdAt: awsDate,
          },
          azure: {
            configured: result.data.azure?.has_credentials || false,
            createdAt: azureDate,
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
    // Reset messages
    passwordError = ''
    passwordSuccess = ''

    // Validate input
    if (!currentPassword) {
      passwordError = 'Current password is required'
      return
    }

    if (!newPassword) {
      passwordError = 'New password is required'
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

      // Success
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

  // Handle AWS secrets update
  async function handleAwsSecretsUpdate() {
    // Reset messages
    awsError = ''
    awsSuccess = ''

    // Validate input
    if (!awsAccessKey) {
      awsError = 'AWS Access Key is required'
      return
    }

    if (!awsSecretKey) {
      awsError = 'AWS Secret Key is required'
      return
    }

    isAwsLoading = true

    try {
      const result = await userApi.setAwsSecrets(awsAccessKey, awsSecretKey)

      if (result.error) {
        awsError = result.error
        return
      }

      // Success
      awsSuccess = 'AWS credentials updated successfully'
      secretsStatus.aws.configured = true // Update local status
      secretsStatus.aws.createdAt = new Date().toISOString()
      awsAccessKey = ''
      awsSecretKey = ''
    } catch (error) {
      awsError =
        error instanceof Error
          ? error.message
          : 'Failed to update AWS credentials'
    } finally {
      isAwsLoading = false
    }
  }

  // Handle Azure secrets update
  async function handleAzureSecretsUpdate() {
    // Reset messages
    azureError = ''
    azureSuccess = ''

    // Validate input
    if (!azureClientId) {
      azureError = 'Azure Client ID is required'
      return
    }

    if (!azureClientSecret) {
      azureError = 'Azure Client Secret is required'
      return
    }

    if (!azureTenantId) {
      azureError = 'Azure Tenant ID is required'
      return
    }

    if (!azureSubscriptionId) {
      azureError = 'Azure Subscription ID is required'
      return
    }

    isAzureLoading = true

    try {
      const result = await userApi.setAzureSecrets(
        azureClientId,
        azureClientSecret,
        azureTenantId,
        azureSubscriptionId
      )

      if (result.error) {
        azureError = result.error
        return
      }

      // Success
      azureSuccess = 'Azure credentials updated successfully'
      secretsStatus.azure.configured = true // Update local status
      secretsStatus.azure.createdAt = new Date().toISOString()
      azureClientId = ''
      azureClientSecret = ''
      azureTenantId = ''
      azureSubscriptionId = ''
    } catch (error) {
      azureError =
        error instanceof Error
          ? error.message
          : 'Failed to update Azure credentials'
    } finally {
      isAzureLoading = false
    }
  }
</script>

<AuthGuard requireAuth={true} redirectTo="/login">
  <div class="relative min-h-screen bg-gray-900 p-8 text-white">
    <div class="mx-auto max-w-4xl">
      <div class="mb-8">
        <div class="mb-4">
          <button
            on:click={() => {
              // Track if we've recently submitted a form, go back twice
              if (awsSuccess || azureSuccess || passwordSuccess) {
                window.history.go(-2);
              } else {
                window.history.back();
              }
            }}
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
          <div class="mb-4 flex items-center space-x-4">
            <div
              class="flex h-16 w-16 items-center justify-center rounded-full bg-gray-700"
            >
              <span class="text-2xl">{userData.name?.[0] || 'U'}</span>
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
              class="w-full rounded-md border border-gray-700 bg-gray-900 px-3 py-2 text-white focus:ring-2 focus:ring-blue-500 focus:outline-none"
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
              class="w-full rounded-md border border-gray-700 bg-gray-900 px-3 py-2 text-white focus:ring-2 focus:ring-blue-500 focus:outline-none"
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
              class="w-full rounded-md border border-gray-700 bg-gray-900 px-3 py-2 text-white focus:ring-2 focus:ring-blue-500 focus:outline-none"
              placeholder="Confirm new password"
            />
          </div>

          {#if passwordError}
            <div class="text-sm text-red-500">
              {passwordError}
            </div>
          {/if}

          {#if passwordSuccess}
            <div class="text-sm text-green-500">
              {passwordSuccess}
            </div>
          {/if}

          <button
            type="submit"
            disabled={isPasswordLoading}
            class="rounded-md bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-gray-900 focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
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

      <!-- Cloud Provider Credentials -->
      <div class="mb-8 rounded-lg bg-gray-800 p-6">
        <div class="mb-4 flex items-center justify-between">
          <div class="flex items-center">
            <h2 class="text-2xl font-semibold">Cloud Provider Credentials</h2>
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="ml-2 h-5 w-5 text-green-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
              />
            </svg>
          </div>
          <div class="group relative">
            <button
              class="flex h-6 w-6 items-center justify-center rounded-full bg-gray-700 text-gray-300 hover:bg-gray-600 focus:outline-none"
              aria-label="Encryption information"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="h-4 w-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </button>
            <div
              class="pointer-events-none absolute right-0 z-50 mt-2 w-72 rounded-md bg-gray-900 px-4 py-3 text-sm text-white opacity-0 shadow-lg transition-opacity duration-200 group-hover:opacity-100"
            >
              <div class="mb-2 flex items-center text-green-400">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  class="mr-2 h-5 w-5"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
                  />
                </svg>
                <span class="font-semibold">End-to-End Encrypted</span>
              </div>
              <p>
                Your credentials are encrypted before entering the database and
                are only decrypted when needed for a range. Even the person
                hosting OpenLabs cannot access your cloud provider credentials.
              </p>
              <div
                class="tooltip-arrow absolute h-2 w-2 rotate-45 transform bg-gray-900"
                style="top: -4px; right: 10px;"
              ></div>
            </div>
          </div>
        </div>

        {#if loadingSecrets}
          <div class="flex justify-center py-8">
            <LoadingSpinner size="md" />
          </div>
        {:else}
          <div class="grid grid-cols-1 gap-8 md:grid-cols-2">
            <!-- AWS Credentials -->
            <div
              class="flex h-full flex-col rounded-lg bg-gray-700 p-5"
              style="min-height: 350px;"
            >
              <div class="mb-4 flex items-center justify-between">
                <h3 class="text-xl font-medium">AWS Credentials</h3>
                <span
                  role="status"
                  aria-label={secretsStatus.aws.configured
                    ? formatDateForTooltip(secretsStatus.aws.createdAt)
                    : 'AWS credentials not configured'}
                  class={`${secretsStatus.aws.configured ? 'bg-green-500' : 'bg-gray-500'} relative cursor-pointer rounded-full px-2 py-1 text-xs font-semibold`}
                  on:mouseenter={(e) => handleMouseEnter(e, 'aws')}
                  on:mouseleave={() => handleMouseLeave('aws')}
                >
                  {secretsStatus.aws.configured
                    ? 'Configured'
                    : 'Not Configured'}
                </span>

                {#if showAwsTooltip && secretsStatus.aws.configured}
                  <div
                    transition:fade={{ duration: 150 }}
                    class="absolute z-50 -translate-x-1/2 transform rounded-md bg-gray-900 px-3 py-2 pb-3 text-sm text-white shadow-lg"
                    style="left: {awsTooltipPosition.x}px; top: {awsTooltipPosition.y}px; pointer-events: none;"
                  >
                    {formatDateForTooltip(secretsStatus.aws.createdAt)}
                    <div
                      class="tooltip-arrow absolute h-2 w-2 rotate-45 transform bg-gray-900"
                      style="left: 50%; bottom: -4px; margin-left: -4px;"
                    ></div>
                  </div>
                {/if}
              </div>

              <form
                on:submit|preventDefault={handleAwsSecretsUpdate}
                class="flex flex-grow flex-col"
              >
                <div class="flex-grow space-y-4">
                  <div>
                    <label
                      for="aws-access-key"
                      class="mb-1 block text-sm font-medium text-gray-300"
                    >
                      Access Key
                    </label>
                    <input
                      id="aws-access-key"
                      type="text"
                      bind:value={awsAccessKey}
                      class="w-full rounded-md border border-gray-600 bg-gray-800 px-3 py-2 text-white focus:ring-2 focus:ring-blue-500 focus:outline-none"
                      placeholder="Enter AWS Access Key"
                    />
                  </div>

                  <div>
                    <label
                      for="aws-secret-key"
                      class="mb-1 block text-sm font-medium text-gray-300"
                    >
                      Secret Key
                    </label>
                    <input
                      id="aws-secret-key"
                      type="password"
                      bind:value={awsSecretKey}
                      class="w-full rounded-md border border-gray-600 bg-gray-800 px-3 py-2 text-white focus:ring-2 focus:ring-blue-500 focus:outline-none"
                      placeholder="Enter AWS Secret Key"
                    />
                  </div>

                  {#if awsError}
                    <div class="text-sm text-red-500">
                      {awsError}
                    </div>
                  {/if}

                  {#if awsSuccess}
                    <div class="text-sm text-green-500">
                      {awsSuccess}
                    </div>
                  {/if}
                </div>

                <div class="mt-auto pt-4">
                  <button
                    type="submit"
                    disabled={isAwsLoading}
                    class="w-full rounded-md bg-yellow-600 px-4 py-2 font-medium text-white hover:bg-yellow-700 focus:ring-2 focus:ring-yellow-500 focus:ring-offset-2 focus:ring-offset-gray-900 focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {#if isAwsLoading}
                      <span class="mr-2 inline-block">
                        <LoadingSpinner size="sm" color="white" />
                      </span>
                      Updating...
                    {:else}
                      {secretsStatus.aws.configured
                        ? 'Update AWS Credentials'
                        : 'Set AWS Credentials'}
                    {/if}
                  </button>
                </div>
              </form>
            </div>

            <!-- Azure Credentials -->
            <div
              class="flex h-full flex-col rounded-lg bg-gray-700 p-5"
              style="min-height: 350px;"
            >
              <div class="mb-4 flex items-center justify-between">
                <h3 class="text-xl font-medium">Azure Credentials</h3>
                <span
                  role="status"
                  aria-label={secretsStatus.azure.configured
                    ? formatDateForTooltip(secretsStatus.azure.createdAt)
                    : 'Azure credentials not configured'}
                  class={`${secretsStatus.azure.configured ? 'bg-green-500' : 'bg-gray-500'} relative cursor-pointer rounded-full px-2 py-1 text-xs font-semibold`}
                  on:mouseenter={(e) => handleMouseEnter(e, 'azure')}
                  on:mouseleave={() => handleMouseLeave('azure')}
                >
                  {secretsStatus.azure.configured
                    ? 'Configured'
                    : 'Not Configured'}
                </span>

                {#if showAzureTooltip && secretsStatus.azure.configured}
                  <div
                    transition:fade={{ duration: 150 }}
                    class="absolute z-50 -translate-x-1/2 transform rounded-md bg-gray-900 px-3 py-2 pb-3 text-sm text-white shadow-lg"
                    style="left: {azureTooltipPosition.x}px; top: {azureTooltipPosition.y}px; pointer-events: none;"
                  >
                    {formatDateForTooltip(secretsStatus.azure.createdAt)}
                    <div
                      class="tooltip-arrow absolute h-2 w-2 rotate-45 transform bg-gray-900"
                      style="left: 50%; bottom: -4px; margin-left: -4px;"
                    ></div>
                  </div>
                {/if}
              </div>

              <form
                on:submit|preventDefault={handleAzureSecretsUpdate}
                class="flex flex-grow flex-col"
              >
                <div class="flex-grow space-y-4">
                  <div>
                    <label
                      for="azure-client-id"
                      class="mb-1 block text-sm font-medium text-gray-300"
                    >
                      Client ID
                    </label>
                    <input
                      id="azure-client-id"
                      type="text"
                      bind:value={azureClientId}
                      class="w-full rounded-md border border-gray-600 bg-gray-800 px-3 py-2 text-white focus:ring-2 focus:ring-blue-500 focus:outline-none"
                      placeholder="Enter Azure Client ID"
                    />
                  </div>

                  <div>
                    <label
                      for="azure-client-secret"
                      class="mb-1 block text-sm font-medium text-gray-300"
                    >
                      Client Secret
                    </label>
                    <input
                      id="azure-client-secret"
                      type="password"
                      bind:value={azureClientSecret}
                      class="w-full rounded-md border border-gray-600 bg-gray-800 px-3 py-2 text-white focus:ring-2 focus:ring-blue-500 focus:outline-none"
                      placeholder="Enter Azure Client Secret"
                    />
                  </div>

                  <div>
                    <label
                      for="azure-tenant-id"
                      class="mb-1 block text-sm font-medium text-gray-300"
                    >
                      Tenant ID
                    </label>
                    <input
                      id="azure-tenant-id"
                      type="text"
                      bind:value={azureTenantId}
                      class="w-full rounded-md border border-gray-600 bg-gray-800 px-3 py-2 text-white focus:ring-2 focus:ring-blue-500 focus:outline-none"
                      placeholder="Enter Azure Tenant ID"
                    />
                  </div>

                  <div>
                    <label
                      for="azure-subscription-id"
                      class="mb-1 block text-sm font-medium text-gray-300"
                    >
                      Subscription ID
                    </label>
                    <input
                      id="azure-subscription-id"
                      type="text"
                      bind:value={azureSubscriptionId}
                      class="w-full rounded-md border border-gray-600 bg-gray-800 px-3 py-2 text-white focus:ring-2 focus:ring-blue-500 focus:outline-none"
                      placeholder="Enter Azure Subscription ID"
                    />
                  </div>

                  {#if azureError}
                    <div class="text-sm text-red-500">
                      {azureError}
                    </div>
                  {/if}

                  {#if azureSuccess}
                    <div class="text-sm text-green-500">
                      {azureSuccess}
                    </div>
                  {/if}
                </div>

                <div class="mt-auto pt-4">
                  <button
                    type="submit"
                    disabled={isAzureLoading}
                    class="w-full rounded-md bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-gray-900 focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {#if isAzureLoading}
                      <span class="mr-2 inline-block">
                        <LoadingSpinner size="sm" color="white" />
                      </span>
                      Updating...
                    {:else}
                      {secretsStatus.azure.configured
                        ? 'Update Azure Credentials'
                        : 'Set Azure Credentials'}
                    {/if}
                  </button>
                </div>
              </form>
            </div>
          </div>
        {/if}
      </div>
    </div>
  </div>
</AuthGuard>
