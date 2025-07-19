<script lang="ts">
  import { auth } from '$lib/stores/auth'
  import { onMount } from 'svelte'

  // For easier access to user data in the blueprint
  $: userName = $auth.user?.name || 'Account'

  // Fetch user data on component mount
  onMount(async () => {
    // Import API dynamically to avoid circular dependencies
    const { authApi } = await import('$lib/api')
    const response = await authApi.getCurrentUser()

    if (response.data?.user) {
      // Update the auth store with user data
      auth.updateUser(response.data.user)
    }
  })

  function handleLogout() {
    auth.logout()
  }
</script>

<div
  class="relative flex h-full w-full flex-col items-center space-y-4 bg-gray-800 text-white"
>
  <h2 class="flex flex-col items-center pt-5 text-xl font-bold">OpenLabs</h2>
  <div class="flex flex-col items-center pt-0">
    <img
      class="mx-auto w-32"
      src="https://avatars.githubusercontent.com/u/196604745?s=200&v=4"
      alt="OpenLabs Logo"
    />
  </div>
  <a
    href="/ranges"
    class="w-7/8 flex items-center rounded-full bg-blue-500 px-6 py-3 text-left font-bold text-white hover:bg-blue-700"
  >
    <svg 
      xmlns="http://www.w3.org/2000/svg"
      class="mr-2 h-5 w-5 flex-shrink-0" 
      fill="none" 
      viewBox="0 0 24 24" 
      stroke="currentColor"
      stroke-width="2"
    >
      <path
        stroke-linecap="round"
        stroke-linejoin="round"
        d="M2 18C2 17.0681 2 16.6022 2.15224 16.2346C2.35523 15.7446 2.74458 15.3552 3.23463 15.1522C3.60218 15 4.06812 15 5 15H19C19.9319 15 20.3978 15 20.7654 15.1522C21.2554 15.3552 21.6448 15.7446 21.8478 16.2346C22 16.6022 22 17.0681 22 18C22 18.9319 22 19.3978 21.8478 19.7654C21.6448 20.2554 21.2554 20.6448 20.7654 20.8478C20.3978 21 19.9319 21 19 21H5C4.06812 21 3.60218 21 3.23463 20.8478C2.74458 20.6448 2.35523 20.2554 2.15224 19.7654C2 19.3978 2 18.9319 2 18Z"
      />
      <path
        stroke-linecap="round"
        stroke-linejoin="round"
        d="M2 12C2 11.0681 2 10.6022 2.15224 10.2346C2.35523 9.74458 2.74458 9.35523 3.23463 9.15224C3.60218 9 4.06812 9 5 9H19C19.9319 9 20.3978 9 20.7654 9.15224C21.2554 9.35523 21.6448 9.74458 21.8478 10.2346C22 10.6022 22 11.0681 22 12C22 12.9319 22 13.3978 21.8478 13.7654C21.6448 14.2554 21.2554 14.6448 20.7654 14.8478C20.3978 15 19.9319 15 19 15H5C4.06812 15 3.60218 15 3.23463 14.8478C2.74458 14.6448 2.35523 14.2554 2.15224 13.7654C2 13.3978 2 12.9319 2 12Z"
      />
      <path
        stroke-linecap="round"
        stroke-linejoin="round"
        d="M2 6C2 5.06812 2 4.60218 2.15224 4.23463C2.35523 3.74458 2.74458 3.35523 3.23463 3.15224C3.60218 3 4.06812 3 5 3H19C19.9319 3 20.3978 3 20.7654 3.15224C21.2554 3.35523 21.6448 3.74458 21.8478 4.23463C22 4.60218 22 5.06812 22 6C22 6.93188 22 7.39782 21.8478 7.76537C21.6448 8.25542 21.2554 8.64477 20.7654 8.84776C20.3978 9 19.9319 9 19 9H5C4.06812 9 3.60218 9 3.23463 8.84776C2.74458 8.64477 2.35523 8.25542 2.15224 7.76537C2 7.39782 2 6.93188 2 6Z"
      />
    </svg>
    Ranges
  </a>
  <a
    href="/blueprints"
    class="w-7/8 flex items-center rounded-full bg-blue-500 px-6 py-3 text-left font-bold text-white hover:bg-blue-700"
  >
    <svg 
      xmlns="http://www.w3.org/2000/svg"
      class="mr-2 h-5 w-5 flex-shrink-0" 
      fill="none" 
      viewBox="0 0 24 24" 
      stroke="currentColor"
      stroke-width="2"
    >
      <path
        stroke-linecap="round"
        stroke-linejoin="round"
        d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
      />
    </svg>
    Blueprints
  </a>
  <a
    href="/workspaces"
    class="w-7/8 flex items-center rounded-full bg-blue-500 px-6 py-3 text-left font-bold text-white hover:bg-blue-700"
  >
    <svg 
      xmlns="http://www.w3.org/2000/svg"
      class="mr-2 h-5 w-5 flex-shrink-0" 
      fill="none" 
      viewBox="0 0 24 24" 
      stroke="currentColor"
      stroke-width="2"
    >
      <path 
        stroke-linecap="round" 
        stroke-linejoin="round" 
        d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" 
      />
    </svg>
    Workspaces
  </a>
  <a
    href="https://docs.openlabs.sh/"
    target="_blank"
    rel="noopener noreferrer"
    class="w-7/8 flex items-center rounded-full bg-blue-500 px-6 py-3 text-left font-bold text-white hover:bg-blue-700"
  >
    <svg 
      xmlns="http://www.w3.org/2000/svg" 
      class="mr-2 h-5 w-5 flex-shrink-0" 
      viewBox="0 0 24 24" 
      fill="none" 
      stroke="currentColor" 
      stroke-width="2" 
      stroke-linecap="round" 
      stroke-linejoin="round"
    >
      <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"></path>
      <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"></path>
    </svg>
    Documentation
  </a>

  <div class="absolute bottom-0 flex w-full flex-col items-center p-4">
    <img
      class="mb-2 h-12 w-12 rounded-full"
      src="https://cdn.pixabay.com/photo/2015/10/05/22/37/blank-profile-picture-973460_960_720.png"
      alt="User Avatar"
    />
    <p class="mb-2">{userName}</p>
    <div class="flex w-full flex-col items-center space-y-2">
      <a
        href="/settings"
        class="w-4/5 rounded-full bg-gray-700 px-4 py-1.5 text-center text-sm text-gray-300 transition-colors hover:bg-gray-600 hover:text-white"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          class="mr-1 inline-block h-4 w-4"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
          />
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
          />
        </svg>
        Settings
      </a>
      <button
        on:click={handleLogout}
        class="w-4/5 rounded-full bg-gray-700 px-4 py-1.5 text-center text-sm text-gray-300 transition-colors hover:bg-gray-600 hover:text-white"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          class="mr-1 inline-block h-4 w-4"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
          />
        </svg>
        Sign Out
      </button>
    </div>
  </div>
</div>
