<style>
  @keyframes slideIn {
    from { transform: translateX(20px); opacity: 0; }
    to { transform: translateX(0); opacity: 1; }
  }
  
  .animate-slideIn {
    animation: slideIn 0.3s ease-out forwards;
  }
</style>

<script lang="ts">
  import { onMount, onDestroy } from 'svelte'
  import { goto } from '$app/navigation'
  import { workspacesApi, rangesApi } from '$lib/api'
  import { auth } from '$lib/stores/auth'
  import logger from '$lib/utils/logger'
  import { browser } from '$app/environment'
  import { fade } from 'svelte/transition'
  import Sidebar from '$lib/components/Sidebar.svelte'
  import LoadingSpinner from '$lib/components/LoadingSpinner.svelte'
  import type { Workspace, WorkspaceUser, AvailableUser, WorkspaceRole } from '$lib/types/workspaces'
  
  // Use the auth store to check if the current user is an admin
  
  // Debug log auth state
  const unsubscribe = auth.subscribe(authState => {
    logger.debug('Auth state updated', 'workspace', authState);
  });
  
  onDestroy(() => {
    unsubscribe();
  });
  
  // Get workspace ID from URL parameter
  export let data
  
  // Workspace and user state
  let workspace: Workspace | null = null
  let workspaceUsers: WorkspaceUser[] = []
  let availableUsers: AvailableUser[] = []
  let isLoading = true
  let isUserLoading = false
  let error = ''
  
  // Edit workspace state
  let isEditing = false
  let editedName = ''
  let editedDescription = ''
  let editedTimeLimit: number | undefined = undefined
  let isUpdating = false
  let updateError = ''
  
  // Add user state
  let showAddUserForm = false
  let selectedUserId = ''
  let selectedUserRole: WorkspaceRole = 'member'
  let userTimeLimit: number | undefined = undefined
  let isAddingUser = false
  let addUserError = ''
  
  // Debug initial state
  logger.debug('Initial state - selectedUserId', 'workspace', { selectedUserId })
  
  // Store all users for lookup purposes
  let allUsers: AvailableUser[] = []
  
  // Delete confirmation state
  let showDeleteConfirm = false
  let isDeleting = false
  let deleteError = ''
  
  // User removal confirmation state
  let showRemoveUserConfirm = false
  let userToRemove = null
  let isRemovingUser = false
  let removeUserError = ''
  
  // Floating alert state
  let showAlert = false
  let alertMessage = ''
  let alertType: 'success' | 'error' | 'warning' | 'info' = 'warning'
  let alertTimeout: any = null
  
  // Blueprint management state
  let workspaceBlueprints = []
  let availableBlueprints = []
  let isBlueprintLoading = false
  let isLoadingAvailableBlueprints = false
  let showShareBlueprintDialog = false
  let selectedBlueprintId = ''
  let isSharingBlueprint = false
  let shareBlueprintError = ''
  let showRemoveBlueprintConfirm = false
  let blueprintToRemove = null
  let isRemovingBlueprint = false
  let removeBlueprintError = ''
  
  // Initialize data when component mounts
  onMount(async () => {
    if (browser) {
      // Check authentication
      if (!$auth.isAuthenticated) {
        goto('/login')
        return
      }
      
      // First load all users for lookup purposes
      try {
        const usersResponse = await workspacesApi.getAllUsers()
        if (usersResponse.data) {
          allUsers = usersResponse.data
        }
      } catch (error) {
        logger.error('Failed to load users', 'workspace.loadUsers', error)
      }
      
      // Then load workspace data
      await loadWorkspaceData(data.workspaceId)
      
      // Also load workspace blueprints
      await loadWorkspaceBlueprints(data.workspaceId)
    }
  })
  
  // Load workspace data
  async function loadWorkspaceData(workspaceId: string) {
    try {
      isLoading = true
      error = ''
      
      const response = await workspacesApi.getWorkspaceById(workspaceId)
      
      if (response.error) {
        error = response.error
        return
      }
      
      if (!response.data) {
        error = 'No workspace data received from API'
        return
      }
      
      // Get the workspace data
      workspace = response.data
      
      // Process workspace data
      
      // Load workspace users
      await loadWorkspaceUsers(workspaceId)
      
      // Force admin status if user is global admin
      if ($auth.user?.admin === true) {
        logger.debug('Forcing admin status because user is a global admin', 'workspace');
        workspace.is_admin = true;
      }
      
      logger.debug('Final workspace state after loading', 'workspace', workspace);
      
      // Initialize edit form with current data
      editedName = workspace.name
      editedDescription = workspace.description
      editedTimeLimit = workspace.default_time_limit
      
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to load workspace'
    } finally {
      isLoading = false
    }
  }
  
  // Load workspace users
  async function loadWorkspaceUsers(workspaceId: string) {
    try {
      isUserLoading = true
      
      const usersResponse = await workspacesApi.getWorkspaceUsers(workspaceId)
      
      if (usersResponse.error) {
        error = usersResponse.error
        return
      }
      
      if (!usersResponse.data) {
        error = 'No user data received from API'
        return
      }
      
      workspaceUsers = usersResponse.data
      logger.debug('Workspace users loaded', 'workspace', workspaceUsers)
      
      // Check if the current user is the owner of the workspace or has admin role
      const currentUserId = $auth.user?.id
      const isGlobalAdmin = $auth.user?.admin === true
      
      logger.debug('Debug admin status', 'workspace', {
        currentUserId,
        authUser: $auth.user,
        isGlobalAdmin,
        workspace,
        workspaceUsers
      });
      
      if (currentUserId && workspace) {
        // Check if user is the workspace owner
        const isWorkspaceOwner = workspace.owner_id === currentUserId
        
        // Find current user in workspace users to check their role
        const currentUserInWorkspace = workspaceUsers.find(u => u.user_id === currentUserId)
        const isWorkspaceAdmin = currentUserInWorkspace?.role === 'admin'
        
        // Set admin status on the workspace object
        workspace.is_admin = isGlobalAdmin || isWorkspaceOwner || isWorkspaceAdmin || false
        
        logger.debug('Admin status details', 'workspace', {
          isGlobalAdmin,
          isWorkspaceOwner,
          workspace_owner_id: workspace.owner_id,
          currentUserInWorkspace,
          isWorkspaceAdmin,
          final_is_admin: workspace.is_admin
        });
      }
      
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to load workspace users'
    } finally {
      isUserLoading = false
    }
  }
  
  // Load available users for adding to workspace
  async function loadAvailableUsers() {
    if (!workspace) return
    
    try {
      // Use the getAllUsers endpoint instead of the workspace-specific one
      const response = await workspacesApi.getAllUsers()
      
      if (response.error) {
        addUserError = response.error
        return
      }
      
      if (!response.data) {
        addUserError = 'No users received from API'
        return
      }
      
      // Save all users for lookup
      allUsers = response.data;
      logger.debug('All users loaded', 'workspace', allUsers);
      
      // Check for users without IDs
      allUsers.forEach(user => {
        if (!user.id) {
          logger.warn('Found user with null or undefined ID', 'workspace', user);
        }
      });
      
      // Get the list of user IDs already in the workspace
      const existingUserIds = new Set(workspaceUsers.map(u => u.user_id));
      logger.debug('Existing user IDs', 'workspace', { existingUserIds: [...existingUserIds] });
      
      // Filter out users already in the workspace
      availableUsers = response.data.filter(user => 
        user.id && !existingUserIds.has(user.id)
      );
      logger.debug('Available users for adding', 'workspace', availableUsers);
      
      // Make sure selectedUserId is reset when loading available users
      selectedUserId = '';
      
    } catch (err) {
      addUserError = err instanceof Error ? err.message : 'Failed to load available users'
    }
  }
  
  // Update workspace
  async function updateWorkspace() {
    if (!workspace) return
    
    if (!editedName.trim()) {
      updateError = 'Workspace name is required'
      return
    }
    
    try {
      isUpdating = true
      updateError = ''
      
      const workspaceData = {
        name: editedName.trim(),
        description: editedDescription.trim(),
        ...(editedTimeLimit && { default_time_limit: editedTimeLimit })
      }
      
      const response = await workspacesApi.updateWorkspace(workspace.id, workspaceData)
      
      if (response.error) {
        updateError = response.error
        return
      }
      
      // Update successful, refresh data
      await loadWorkspaceData(workspace.id)
      
      // Exit edit mode
      isEditing = false
      
    } catch (err) {
      updateError = err instanceof Error ? err.message : 'Failed to update workspace'
    } finally {
      isUpdating = false
    }
  }
  
  // Add user to workspace
  async function addUserToWorkspace() {
    if (!workspace) return
    
    logger.debug('Adding user to workspace', 'workspace', { 
      selectedUserId, 
      availableUsers, 
      availableUserIds: availableUsers.map(u => u.id) 
    });
    
    // Validate user selection
    if (!selectedUserId || selectedUserId === "") {
      addUserError = 'Please select a user to add'
      return
    }
    
    try {
      isAddingUser = true
      addUserError = ''
      
      // Get the selected user based on ID
      logger.debug('Looking for user with ID', 'workspace', { selectedUserId });
      const selectedUser = availableUsers.find(user => user.id === selectedUserId);
      logger.debug('Found selected user', 'workspace', selectedUser);
      
      // Extra validation for the selected user
      if (!selectedUser) {
        addUserError = "Selected user not found in available users list"
        isAddingUser = false
        return
      }
      
      if (!selectedUser.id) {
        addUserError = "Selected user has an invalid ID"
        isAddingUser = false
        return
      }
      
      // Now we have the selected user with a valid UUID
      const userData = {
        user_id: selectedUser.id,
        role: selectedUserRole,
        ...(userTimeLimit && { time_limit: userTimeLimit })
      }
      
      logger.debug('Sending user data to API', 'workspace', userData);
      
      const response = await workspacesApi.addWorkspaceUser(workspace.id, userData)
      
      if (response.error) {
        addUserError = response.error
        return
      }
      
      // User added successfully, refresh users list and also refresh available users
      await loadWorkspaceUsers(workspace.id)
      
      // Also refresh all users to make sure user details are up to date
      const usersResponse = await workspacesApi.getAllUsers()
      if (usersResponse.data) {
        allUsers = usersResponse.data
        logger.debug('All users refreshed after adding user', 'workspace', allUsers)
      }
      
      // Reset form
      showAddUserForm = false
      selectedUserId = ''
      selectedUserRole = 'member'
      userTimeLimit = undefined
      
    } catch (err) {
      addUserError = err instanceof Error ? err.message : 'Failed to add user to workspace'
    } finally {
      isAddingUser = false
    }
  }
  
  // Show confirmation to remove a user from workspace
  function confirmRemoveUser(userId: string, userName: string) {
    userToRemove = { userId, userName };
    showRemoveUserConfirm = true;
    removeUserError = '';
  }
  
  // Remove user from workspace
  async function removeUser() {
    if (!workspace || !userToRemove) return
    
    try {
      isRemovingUser = true;
      removeUserError = '';
      
      const response = await workspacesApi.removeWorkspaceUser(workspace.id, userToRemove.userId)
      
      if (response.error) {
        removeUserError = response.error;
        return;
      }
      
      // User removed successfully, refresh users list
      await loadWorkspaceUsers(workspace.id);
      
      // Reset state and close confirmation dialog
      showRemoveUserConfirm = false;
      userToRemove = null;
      
    } catch (err) {
      removeUserError = err instanceof Error ? err.message : 'Failed to remove user from workspace';
    } finally {
      isRemovingUser = false;
    }
  }

  // Promote user to admin role
  async function promoteUser(userId: string) {
    if (!workspace) return
    
    try {
      const response = await workspacesApi.updateWorkspaceUserRole(workspace.id, userId, 'admin')
      
      if (response.error) {
        error = response.error
        return
      }
      
      // User promoted successfully, refresh users list
      await loadWorkspaceUsers(workspace.id)
      
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to promote user'
    }
  }

  // Show floating alert
  function showFloatingAlert(message: string, type: 'success' | 'error' | 'warning' | 'info' = 'info', duration = 4000) {
    // Clear existing timeout if any
    if (alertTimeout) {
      clearTimeout(alertTimeout);
    }
    
    // Set alert properties
    alertMessage = message;
    alertType = type;
    showAlert = true;
    
    // Auto-hide after duration
    alertTimeout = setTimeout(() => {
      showAlert = false;
    }, duration);
  }
  
  // Demote user to member role
  async function demoteUser(userId: string, userName: string) {
    if (!workspace) return
    
    // Check if user is the workspace owner
    if (userId === workspace.owner_id) {
      showFloatingAlert("Cannot demote the workspace owner. The owner must always have admin privileges.", "warning");
      return;
    }
    
    try {
      const response = await workspacesApi.updateWorkspaceUserRole(workspace.id, userId, 'member')
      
      if (response.error) {
        error = response.error
        return
      }
      
      // User demoted successfully, refresh users list
      await loadWorkspaceUsers(workspace.id)
      showFloatingAlert(`${userName} has been demoted to member.`, "success");
      
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to demote user'
      showFloatingAlert(`Failed to demote user: ${error}`, "error");
    }
  }
  
  // Handle showing add user form
  async function showAddUser() {
    showAddUserForm = true
    addUserError = ''
    
    // Make sure selectedUserId is set to an empty string to start
    selectedUserId = '';
    
    // Load available users
    await loadAvailableUsers()
    
    // If we have available users, select the first one
    if (availableUsers.length > 0) {
      logger.debug('Setting initial selected user to', 'workspace', availableUsers[0]);
      // Use the UUID as the ID
      selectedUserId = availableUsers[0].id;
    } else {
      logger.warn('No users available to add to the workspace', 'workspace');
    }
  }
  
  // Load blueprints shared with this workspace
  async function loadWorkspaceBlueprints(workspaceId: string) {
    if (!workspaceId) return;
    
    try {
      isBlueprintLoading = true;
      
      // Get blueprints shared with the workspace
      const response = await workspacesApi.getWorkspaceBlueprints(workspaceId);
      
      if (response.error) {
        error = response.error;
        workspaceBlueprints = [];
        return;
      }
      
      if (!response.data) {
        workspaceBlueprints = [];
        return;
      }
      
      const sharedBlueprints = response.data;
      logger.debug('Workspace blueprint records loaded', 'workspace', sharedBlueprints);
      
      // Now we need to fetch the actual blueprint details for each shared blueprint
      // Create a new array to hold the enhanced blueprints
      const enhancedBlueprints = [];
      
      // Fetch each blueprint's details individually using the specific endpoint
      for (const sharedBlueprint of sharedBlueprints) {
        try {
          // Get the specific blueprint by its ID
          const blueprintResponse = await rangesApi.getBlueprintById(sharedBlueprint.blueprint_id);
          
          // Store the original sharing record ID before we enhance
          const originalId = sharedBlueprint.id;
                
          if (blueprintResponse.error) {
            logger.warn(`Error fetching blueprint ${sharedBlueprint.blueprint_id}`, 'workspace', blueprintResponse.error);
            // Add a placeholder entry
            enhancedBlueprints.push({
              ...sharedBlueprint,
              // Keep the original ID for unsharing
              id: originalId,
              name: `Blueprint ${sharedBlueprint.blueprint_id.substring(0, 8)}`,
              provider: 'unknown',
              description: 'Blueprint details not available',
              vnc: false,
              vpn: false
            });
          } else if (blueprintResponse.data) {
            // Merge the blueprint details with the shared blueprint record
            enhancedBlueprints.push({
              ...sharedBlueprint,
              // Keep the original ID for unsharing
              id: originalId,
              name: blueprintResponse.data.name,
              provider: blueprintResponse.data.provider,
              description: blueprintResponse.data.description,
              vnc: blueprintResponse.data.vnc,
              vpn: blueprintResponse.data.vpn
            });
          } else {
            // Fallback if no data
            enhancedBlueprints.push({
              ...sharedBlueprint,
              // Keep the original ID for unsharing
              id: originalId,
              name: `Blueprint ${sharedBlueprint.blueprint_id.substring(0, 8)}`,
              provider: 'unknown',
              description: 'No blueprint data returned',
              vnc: false,
              vpn: false
            });
          }
        } catch (err) {
          logger.error(`Failed to fetch blueprint ${sharedBlueprint.blueprint_id}`, 'workspace', err);
          // Add placeholder on error
          const originalId = sharedBlueprint.id;
          enhancedBlueprints.push({
            ...sharedBlueprint,
            // Keep the original ID for unsharing
            id: originalId,
            name: `Blueprint ${sharedBlueprint.blueprint_id.substring(0, 8)}`,
            provider: 'unknown',
            description: 'Error loading blueprint details',
            vnc: false,
            vpn: false
          });
        }
      }
      
      workspaceBlueprints = enhancedBlueprints;
      logger.debug('Enhanced workspace blueprints', 'workspace', workspaceBlueprints);
    } catch (err) {
      logger.error('Failed to load workspace blueprints', 'workspace', err);
      workspaceBlueprints = [];
    } finally {
      isBlueprintLoading = false;
    }
  }
  
  // Load blueprints that can be shared with the workspace
  async function loadAvailableBlueprints() {
    if (!workspace) return;
    
    try {
      isLoadingAvailableBlueprints = true;
      shareBlueprintError = '';
      
      // Get all blueprints the user owns
      const response = await rangesApi.getBlueprints();
      
      if (response.error) {
        shareBlueprintError = response.error;
        availableBlueprints = [];
        return;
      }
      
      if (!response.data) {
        availableBlueprints = [];
        return;
      }
      
      logger.debug('Blueprints from API', 'workspace', response.data);
      
      // Get all blueprints already shared with workspace (use blueprint_id, not the sharing record id)
      const workspaceBlueprintIds = new Set(workspaceBlueprints.map(t => t.blueprint_id));
      logger.debug('Already shared blueprint IDs', 'workspace', { workspaceBlueprintIds: [...workspaceBlueprintIds] });
      
      // Filter out blueprints already shared with the workspace
      availableBlueprints = response.data.filter(blueprint => !workspaceBlueprintIds.has(blueprint.id));
      
    } catch (err) {
      shareBlueprintError = err instanceof Error ? err.message : 'Failed to load available blueprints';
      availableBlueprints = [];
    } finally {
      isLoadingAvailableBlueprints = false;
    }
  }
  
  // Show the blueprint sharing dialog
  async function showShareBlueprint() {
    showShareBlueprintDialog = true;
    shareBlueprintError = '';
    selectedBlueprintId = '';
    await loadAvailableBlueprints();
  }
  
  // Share a blueprint with the workspace
  async function shareBlueprint() {
    if (!workspace || !selectedBlueprintId) return;
    
    try {
      isSharingBlueprint = true;
      shareBlueprintError = '';
      
      logger.debug('Sharing blueprint ID', 'workspace', { selectedBlueprintId });
      
      // Find the selected blueprint to log details
      const selectedBlueprint = availableBlueprints.find(t => t.id === selectedBlueprintId);
      logger.debug('Selected blueprint for sharing', 'workspace', selectedBlueprint);
      
      const response = await workspacesApi.shareBlueprintWithWorkspace(workspace.id, selectedBlueprintId);
      logger.debug('Blueprint share API response', 'workspace', response);
      
      if (response.error) {
        shareBlueprintError = response.error;
        return;
      }
      
      // Blueprint shared successfully, reload blueprints
      await loadWorkspaceBlueprints(workspace.id);
      
      // Reset form and close dialog
      showShareBlueprintDialog = false;
      selectedBlueprintId = '';
      
    } catch (err) {
      shareBlueprintError = err instanceof Error ? err.message : 'Failed to share blueprint';
    } finally {
      isSharingBlueprint = false;
    }
  }
  
  // Show confirmation to remove a blueprint from workspace
  function confirmRemoveBlueprint(blueprint) {
    blueprintToRemove = blueprint;
    showRemoveBlueprintConfirm = true;
    removeBlueprintError = '';
  }
  
  // Remove a blueprint from the workspace
  async function removeBlueprint() {
    if (!workspace || !blueprintToRemove) return;
    
    try {
      isRemovingBlueprint = true;
      removeBlueprintError = '';
      
      logger.debug('Removing blueprint', 'workspace', blueprintToRemove);
      
      // IMPORTANT: We must use the blueprint_id for unsharing, not the sharing record ID
      // This should match the same ID used for viewing blueprint details
      const blueprintId = blueprintToRemove.blueprint_id;
      logger.debug('Using blueprint ID for removal', 'workspace', { blueprintId });
      
      const response = await workspacesApi.removeBlueprintFromWorkspace(workspace.id, blueprintId);
      
      if (response.error) {
        removeBlueprintError = response.error;
        return;
      }
      
      // Blueprint removed successfully, reload blueprints
      await loadWorkspaceBlueprints(workspace.id);
      
      // Reset state and close confirmation dialog
      showRemoveBlueprintConfirm = false;
      blueprintToRemove = null;
      
    } catch (err) {
      removeBlueprintError = err instanceof Error ? err.message : 'Failed to remove blueprint';
    } finally {
      isRemovingBlueprint = false;
    }
  }
  
  // Delete workspace
  async function deleteWorkspace() {
    if (!workspace) return;
    
    try {
      isDeleting = true;
      deleteError = '';
      
      const response = await workspacesApi.deleteWorkspace(workspace.id);
      
      if (response.error) {
        deleteError = response.error;
        return;
      }
      
      // Navigate back to workspaces page after successful deletion
      goto('/workspaces');
      
    } catch (err) {
      deleteError = err instanceof Error ? err.message : 'Failed to delete workspace';
    } finally {
      isDeleting = false;
      showDeleteConfirm = false;
    }
  }
  
  // Function to get user details by ID
  function getUserDetails(userId: string) {
    if (!userId) {
      return { name: 'Unknown User', email: 'No Email' };
    }
    
    // First, look for this user in the workspace users array
    const workspaceUser = workspaceUsers.find(u => u.user_id === userId);
    if (workspaceUser && workspaceUser.name) {
      return {
        name: workspaceUser.name,
        email: workspaceUser.email || ''
      };
    }
    
    // If not found in workspace users, check all users array
    const user = allUsers.find(u => u.id === userId);
    if (user) {
      return {
        name: user.name,
        email: user.email || ''
      };
    }
    
    // If the user is the current logged-in user
    if (userId === $auth.user?.id && $auth.user?.name) {
      return {
        name: $auth.user.name,
        email: $auth.user.email || ''
      };
    }
    
    // If we still don't have user info, try to load all users if not already loaded
    if (allUsers.length === 0) {
      workspacesApi.getAllUsers().then(response => {
        if (response.data) {
          allUsers = response.data;
        }
      });
    }
    
    // Return a more user-friendly unknown user format 
    return {
      name: 'User ' + userId.slice(0, 6),
      email: 'Unknown Email'
    };
  }
</script>

<svelte:head>
  <title>OpenLabs | Workspace Details</title>
</svelte:head>

<div class="font-roboto flex h-screen bg-gray-100">
  <!-- Fixed sidebar -->
  <div class="fixed inset-y-0 left-0 z-10 w-54">
    <Sidebar />
  </div>

  <!-- Main content with sidebar margin -->
  <div class="ml-54 flex-1 overflow-y-auto">
    <div class="p-6">
      <!-- Back button -->
      <div class="mb-6">
        <a
          href="/workspaces"
          class="flex items-center text-blue-500 hover:text-blue-700"
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
          Back to Workspaces
        </a>
      </div>

      <!-- Floating Alert -->
      {#if showAlert}
        <div class="fixed top-20 right-4 z-50 max-w-md animate-slideIn" transition:fade={{ duration: 200 }}>
          <div class="rounded-lg shadow-lg overflow-hidden">
            <div class={`p-4 ${
              alertType === 'success' ? 'bg-green-100 border-l-4 border-green-500' : 
              alertType === 'error' ? 'bg-red-100 border-l-4 border-red-500' : 
              alertType === 'warning' ? 'bg-yellow-100 border-l-4 border-yellow-500' : 
              'bg-blue-100 border-l-4 border-blue-500'
            }`}>
              <div class="flex items-start">
                <div class="flex-shrink-0">
                  {#if alertType === 'success'}
                    <svg class="h-5 w-5 text-green-600" viewBox="0 0 20 20" fill="currentColor">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                    </svg>
                  {:else if alertType === 'error'}
                    <svg class="h-5 w-5 text-red-600" viewBox="0 0 20 20" fill="currentColor">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
                    </svg>
                  {:else if alertType === 'warning'}
                    <svg class="h-5 w-5 text-yellow-600" viewBox="0 0 20 20" fill="currentColor">
                      <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
                    </svg>
                  {:else}
                    <svg class="h-5 w-5 text-blue-600" viewBox="0 0 20 20" fill="currentColor">
                      <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" />
                    </svg>
                  {/if}
                </div>
                <div class="ml-3">
                  <p class={`text-sm font-medium ${
                    alertType === 'success' ? 'text-green-800' : 
                    alertType === 'error' ? 'text-red-800' : 
                    alertType === 'warning' ? 'text-yellow-800' : 
                    'text-blue-800'
                  }`}>
                    {alertMessage}
                  </p>
                </div>
                <div class="ml-auto pl-3">
                  <div class="-mx-1.5 -my-1.5">
                    <button 
                      type="button" 
                      class={`inline-flex rounded-md p-1.5 focus:outline-none focus:ring-2 ${
                        alertType === 'success' ? 'text-green-500 hover:bg-green-200 focus:ring-green-600' : 
                        alertType === 'error' ? 'text-red-500 hover:bg-red-200 focus:ring-red-600' : 
                        alertType === 'warning' ? 'text-yellow-500 hover:bg-yellow-200 focus:ring-yellow-600' : 
                        'text-blue-500 hover:bg-blue-200 focus:ring-blue-600'
                      }`}
                      on:click={() => (showAlert = false)}
                    >
                      <span class="sr-only">Dismiss</span>
                      <svg class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                        <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
                      </svg>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      {/if}
      
      <!-- Error Message -->
      {#if error}
        <div class="mb-4 rounded-md bg-red-50 p-4 text-red-700">
          <p>{error}</p>
        </div>
      {/if}

      <!-- Loading Spinner -->
      {#if isLoading}
        <div class="flex justify-center p-12">
          <LoadingSpinner size="large" message="Loading workspace details..." />
        </div>
      <!-- Workspace Details -->
      {:else if workspace}
        <div class="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <!-- Workspace Info Card -->
          <div class="lg:col-span-1">
            <div class="overflow-hidden rounded-lg bg-white shadow mb-4">
              <div class="bg-blue-600 p-4 text-white">
                <div class="flex items-center justify-between">
                  <h1 class="text-xl font-bold">{workspace.name}</h1>
                  {#if workspace.is_admin}
                    <span class="rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-800">
                      Admin
                    </span>
                  {:else}
                    <span class="rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-800">
                      Member
                    </span>
                  {/if}
                </div>
              </div>
              
              {#if isEditing}
                <div class="p-4">
                  <h2 class="mb-4 text-lg font-semibold">Edit Workspace</h2>
                  
                  {#if updateError}
                    <div class="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-700">
                      <p>{updateError}</p>
                    </div>
                  {/if}
                  
                  <div class="space-y-4">
                    <div>
                      <label for="name" class="mb-1 block text-sm font-medium text-gray-700">
                        Name *
                      </label>
                      <input
                        type="text"
                        id="name"
                        class="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                        bind:value={editedName}
                        required
                      />
                    </div>
                    
                    <div>
                      <label for="description" class="mb-1 block text-sm font-medium text-gray-700">
                        Description
                      </label>
                      <textarea
                        id="description"
                        rows="3"
                        class="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                        bind:value={editedDescription}
                      ></textarea>
                    </div>
                    
                    <div>
                      <label for="timeLimit" class="mb-1 block text-sm font-medium text-gray-700">
                        Default Time Limit (minutes)
                      </label>
                      <input
                        type="number"
                        id="timeLimit"
                        class="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                        bind:value={editedTimeLimit}
                        min="1"
                      />
                      <p class="mt-1 text-xs text-gray-500">
                        Leave empty for no time limit
                      </p>
                    </div>
                    
                    <div class="flex justify-end space-x-3 pt-2">
                      <button
                        type="button"
                        class="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50"
                        on:click={() => (isEditing = false)}
                        disabled={isUpdating}
                      >
                        Cancel
                      </button>
                      <button
                        type="button"
                        class="rounded-md bg-blue-500 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-600 focus:outline-none {isUpdating ? 'cursor-not-allowed opacity-70' : ''}"
                        on:click={updateWorkspace}
                        disabled={isUpdating}
                      >
                        {#if isUpdating}
                          <span class="flex items-center">
                            <svg
                              class="mr-2 -ml-1 h-4 w-4 animate-spin text-white"
                              xmlns="http://www.w3.org/2000/svg"
                              fill="none"
                              viewBox="0 0 24 24"
                            >
                              <circle
                                class="opacity-25"
                                cx="12"
                                cy="12"
                                r="10"
                                stroke="currentColor"
                                stroke-width="4"
                              ></circle>
                              <path
                                class="opacity-75"
                                fill="currentColor"
                                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                              ></path>
                            </svg>
                            Saving...
                          </span>
                        {:else}
                          Save Changes
                        {/if}
                      </button>
                    </div>
                  </div>
                </div>
              {:else}
                <div class="p-4">
                  <!-- Description -->
                  <div class="mb-4">
                    <h2 class="mb-2 text-sm font-medium text-gray-500">
                      Description
                    </h2>
                    {#if workspace.description}
                      <p class="text-gray-700">{workspace.description}</p>
                    {:else}
                      <p class="italic text-gray-400">No description</p>
                    {/if}
                  </div>
                  
                  <!-- Time Limit -->
                  {#if workspace.default_time_limit}
                    <div class="mb-4">
                      <h2 class="mb-2 text-sm font-medium text-gray-500">
                        Default Time Limit
                      </h2>
                      <p class="text-gray-700">{workspace.default_time_limit} minutes</p>
                    </div>
                  {/if}
                  
                  <!-- Workspace ID -->
                  <div class="mb-4">
                    <h2 class="mb-2 text-sm font-medium text-gray-500">
                      Workspace ID
                    </h2>
                    <p class="font-mono text-xs text-gray-500">
                      <span class="rounded bg-gray-100 p-1">{workspace.id}</span>
                    </p>
                  </div>
                  
                  <!-- Admin Buttons -->
                  {#if workspace.is_admin}
                    <div class="mt-6 space-y-2">
                      <button
                        class="w-full rounded-md bg-blue-500 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-600"
                        on:click={() => (isEditing = true)}
                      >
                        Edit Workspace
                      </button>
                      
                      <button
                        class="w-full rounded-md border border-red-300 bg-white px-4 py-2 text-sm font-medium text-red-600 shadow-sm hover:bg-red-50"
                        on:click={() => (showDeleteConfirm = true)}
                      >
                        Delete Workspace
                      </button>
                    </div>
                  {/if}
                </div>
              {/if}
            </div>

          </div>
          
          <!-- Users Section -->
          <div class="lg:col-span-2">
            <div class="mb-4 overflow-hidden rounded-lg bg-white shadow">
              <div class="bg-gradient-to-r from-blue-600 to-blue-700 p-4 text-white">
                <div class="flex items-center justify-between">
                  <div>
                    <h2 class="text-lg font-semibold">Workspace Members</h2>
                    <p class="text-sm text-blue-100">Manage access to this workspace</p>
                  </div>
                  {#if workspace.is_admin}
                    <button
                      class="flex items-center rounded-md bg-white px-3 py-1.5 text-sm font-medium text-blue-600 hover:bg-blue-50"
                      on:click={showAddUser}
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" class="mr-1 h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                        <path d="M8 9a3 3 0 100-6 3 3 0 000 6zM8 11a6 6 0 016 6H2a6 6 0 016-6zM16 7a1 1 0 10-2 0v1h-1a1 1 0 100 2h1v1a1 1 0 102 0v-1h1a1 1 0 100-2h-1V7z" />
                      </svg>
                      Add User
                    </button>
                  {/if}
                </div>
              </div>
              
              <!-- Add User Form -->
              {#if showAddUserForm && workspace.is_admin}
                <div class="border-b bg-gradient-to-b from-blue-50 to-white p-6">
                  <h3 class="mb-4 text-lg font-medium text-blue-800">Add User to Workspace</h3>
                  
                  {#if addUserError}
                    <div class="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-700 border border-red-200">
                      <div class="flex">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
                        </svg>
                        <p>{addUserError}</p>
                      </div>
                    </div>
                  {/if}
                  
                  <div class="grid grid-cols-1 gap-6 md:grid-cols-2">
                    <div>
                      <label for="user" class="mb-1 block text-sm font-medium text-gray-700">
                        User *
                      </label>
                      {#if availableUsers.length > 0}
                        <div class="relative">
                          <select
                            id="user"
                            class="block w-full appearance-none rounded-md border border-gray-300 py-2 pl-3 pr-10 text-base focus:border-blue-500 focus:outline-none focus:ring-blue-500"
                            bind:value={selectedUserId}
                            on:change={(e) => logger.debug('Select value changed to', 'workspace', { value: e.target.value })}
                          >
                            <option value="" disabled>Select a user...</option>
                            {#each availableUsers as user}
                              <option value={user.id}>
                                {user.name} ({user.email})
                              </option>
                            {/each}
                          </select>
                          <div class="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-gray-700">
                            <svg class="h-4 w-4 fill-current" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">
                              <path d="M9.293 12.95l.707.707L15.657 8l-1.414-1.414L10 10.828 5.757 6.586 4.343 8z"/>
                            </svg>
                          </div>
                        </div>
                        <p class="mt-1 text-xs text-gray-500">
                          Choose a user to add to this workspace
                        </p>
                      {:else}
                        <div class="rounded-md bg-yellow-50 p-3 text-sm text-yellow-700 border border-yellow-200">
                          <div class="flex">
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
                              <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
                            </svg>
                            <p>No available users to add</p>
                          </div>
                        </div>
                      {/if}
                    </div>
                    
                    <div>
                      <label for="role" class="mb-1 block text-sm font-medium text-gray-700">
                        Role *
                      </label>
                      <div class="relative">
                        <select
                          id="role"
                          class="block w-full appearance-none rounded-md border border-gray-300 py-2 pl-3 pr-10 text-base focus:border-blue-500 focus:outline-none focus:ring-blue-500"
                          bind:value={selectedUserRole}
                        >
                          <option value="admin">Admin</option>
                          <option value="member">Member</option>
                        </select>
                        <div class="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-gray-700">
                          <svg class="h-4 w-4 fill-current" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">
                            <path d="M9.293 12.95l.707.707L15.657 8l-1.414-1.414L10 10.828 5.757 6.586 4.343 8z"/>
                          </svg>
                        </div>
                      </div>
                      <p class="mt-1 text-xs text-gray-500">
                        Admins can manage workspace settings and members
                      </p>
                    </div>
                    
                    <div class="md:col-span-2">
                      <label for="userTimeLimit" class="mb-1 block text-sm font-medium text-gray-700">
                        User Time Limit (minutes)
                      </label>
                      <div class="relative mt-1 rounded-md shadow-sm">
                        <input
                          type="number"
                          id="userTimeLimit"
                          class="block w-full rounded-md border border-gray-300 py-2 pl-3 pr-10 text-base focus:border-blue-500 focus:outline-none focus:ring-blue-500"
                          placeholder="Optional time limit (overrides default)"
                          bind:value={userTimeLimit}
                          min="1"
                        />
                        <div class="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none">
                          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-gray-400" viewBox="0 0 20 20" fill="currentColor">
                            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clip-rule="evenodd" />
                          </svg>
                        </div>
                      </div>
                      <p class="mt-1 text-xs text-gray-500">
                        Leave empty to use workspace default time limit
                      </p>
                    </div>
                  </div>
                  
                  <div class="mt-6 flex justify-end space-x-3 border-t border-gray-200 pt-4">
                    <button
                      type="button"
                      class="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50"
                      on:click={() => (showAddUserForm = false)}
                      disabled={isAddingUser}
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      class="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700 focus:outline-none {isAddingUser || availableUsers.length === 0 ? 'cursor-not-allowed opacity-70' : ''}"
                      on:click={addUserToWorkspace}
                      disabled={isAddingUser || availableUsers.length === 0}
                    >
                      {#if isAddingUser}
                        <span class="flex items-center">
                          <svg
                            class="mr-2 -ml-1 h-4 w-4 animate-spin text-white"
                            xmlns="http://www.w3.org/2000/svg"
                            fill="none"
                            viewBox="0 0 24 24"
                          >
                            <circle
                              class="opacity-25"
                              cx="12"
                              cy="12"
                              r="10"
                              stroke="currentColor"
                              stroke-width="4"
                            ></circle>
                            <path
                              class="opacity-75"
                              fill="currentColor"
                              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                            ></path>
                          </svg>
                          Adding...
                        </span>
                      {:else}
                        Add User
                      {/if}
                    </button>
                  </div>
                </div>
              {/if}
              
              <!-- User List -->
              {#if isUserLoading}
                <div class="flex justify-center p-12">
                  <LoadingSpinner size="small" message="Loading users..." />
                </div>
              {:else if workspaceUsers.length > 0}
                <div class="overflow-x-auto">
                  <table class="min-w-full divide-y divide-gray-200">
                    <thead class="bg-gray-50">
                      <tr>
                        <th scope="col" class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                          User
                        </th>
                        <th scope="col" class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                          Role
                        </th>
                        <th scope="col" class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                          Time Limit
                        </th>
                        <th scope="col" class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                          Last Activity
                        </th>
                        {#if workspace.is_admin}
                          <th scope="col" class="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                            Actions
                          </th>
                        {/if}
                      </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-200 bg-white">
                      {#each workspaceUsers as user}
                        <tr class="hover:bg-gray-50 transition-colors">
                          <td class="whitespace-nowrap px-6 py-4">
                            <div class="flex items-center">
                              <div class="flex-shrink-0 h-10 w-10 bg-gradient-to-br from-blue-500 to-blue-600 rounded-full flex items-center justify-center text-white font-medium shadow-sm">
                                {#if true}
                                  {@const details = getUserDetails(user.user_id)}
                                  {details.name.substring(0, 2).toUpperCase()}
                                {/if}
                              </div>
                              <div class="ml-4">
                                {#if true}
                                  {@const details = getUserDetails(user.user_id)}
                                  <div class="font-medium text-gray-900">{details.name}</div>
                                  <div class="text-sm text-gray-500">{details.email}</div>
                                {/if}
                              </div>
                            </div>
                          </td>
                          <td class="whitespace-nowrap px-6 py-4">
                            {#if user.role === 'admin'}
                              <span class="inline-flex items-center rounded-full bg-blue-100 px-3 py-0.5 text-xs font-medium text-blue-800">
                                <svg xmlns="http://www.w3.org/2000/svg" class="mr-1 h-3 w-3" viewBox="0 0 20 20" fill="currentColor">
                                  <path fill-rule="evenodd" d="M2.166 4.999A11.954 11.954 0 0010 1.944 11.954 11.954 0 0017.834 5c.11.65.166 1.32.166 2.001 0 5.225-3.34 9.67-8 11.317C5.34 16.67 2 12.225 2 7c0-.682.057-1.35.166-2.001zm11.541 3.708a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                                </svg>
                                Admin
                              </span>
                            {:else}
                              <span class="inline-flex items-center rounded-full bg-gray-100 px-3 py-0.5 text-xs font-medium text-gray-800">
                                <svg xmlns="http://www.w3.org/2000/svg" class="mr-1 h-3 w-3" viewBox="0 0 20 20" fill="currentColor">
                                  <path d="M13 6a3 3 0 11-6 0 3 3 0 016 0zM18 8a2 2 0 11-4 0 2 2 0 014 0zM14 15a4 4 0 00-8 0v3h8v-3zM6 8a2 2 0 11-4 0 2 2 0 014 0zM16 18v-3a5.972 5.972 0 00-.75-2.906A3.005 3.005 0 0119 15v3h-3zM4.75 12.094A5.973 5.973 0 004 15v3H1v-3a3 3 0 013.75-2.906z" />
                                </svg>
                                Member
                              </span>
                            {/if}
                          </td>
                          <td class="whitespace-nowrap px-6 py-4 text-sm text-gray-500">
                            {#if user.time_limit}
                              <div class="flex items-center">
                                <svg xmlns="http://www.w3.org/2000/svg" class="mr-1 h-4 w-4 text-gray-400" viewBox="0 0 20 20" fill="currentColor">
                                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clip-rule="evenodd" />
                                </svg>
                                <span>{user.time_limit} minutes</span>
                              </div>
                            {:else if workspace.default_time_limit}
                              <div class="flex items-center text-gray-400">
                                <svg xmlns="http://www.w3.org/2000/svg" class="mr-1 h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clip-rule="evenodd" />
                                </svg>
                                <span>{workspace.default_time_limit} minutes (default)</span>
                              </div>
                            {:else}
                              <div class="flex items-center text-gray-400">
                                <svg xmlns="http://www.w3.org/2000/svg" class="mr-1 h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clip-rule="evenodd" />
                                </svg>
                                <span>No limit</span>
                              </div>
                            {/if}
                          </td>
                          <td class="whitespace-nowrap px-6 py-4 text-sm text-gray-500">
                            <div class="flex items-center">
                              <span class="inline-block h-2 w-2 flex-shrink-0 rounded-full bg-green-400"></span>
                              <span class="ml-1.5">Just now</span>
                            </div>
                          </td>
                          {#if workspace.is_admin}
                            <td class="whitespace-nowrap px-6 py-4 text-right text-sm font-medium">
                              <div class="flex justify-end space-x-3">
                                {#if user.role === 'admin'}
                                  <button
                                    class="text-gray-600 hover:text-gray-900 flex items-center"
                                    on:click={() => demoteUser(user.user_id, getUserDetails(user.user_id).name)}
                                    title="Demote to member"
                                  >
                                    <svg xmlns="http://www.w3.org/2000/svg" class="mr-1 h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-11a1 1 0 10-2 0v3.586L7.707 9.293a1 1 0 00-1.414 1.414l3 3a1 1 0 001.414 0l3-3a1 1 0 00-1.414-1.414L11 10.586V7z" clip-rule="evenodd" />
                                    </svg>
                                    Demote
                                  </button>
                                {:else}
                                  <button
                                    class="text-blue-600 hover:text-blue-900 flex items-center"
                                    on:click={() => promoteUser(user.user_id, getUserDetails(user.user_id).name)}
                                    title="Promote to admin"
                                  >
                                    <svg xmlns="http://www.w3.org/2000/svg" class="mr-1 h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-8.707l-3-3a1 1 0 00-1.414 0l-3 3a1 1 0 001.414 1.414L9 9.414V13a1 1 0 102 0V9.414l1.293 1.293a1 1 0 001.414-1.414z" clip-rule="evenodd" />
                                    </svg>
                                    Promote
                                  </button>
                                {/if}
                                <button
                                  class="text-red-600 hover:text-red-900 flex items-center"
                                  on:click={() => confirmRemoveUser(user.user_id, getUserDetails(user.user_id).name)}
                                >
                                  <svg xmlns="http://www.w3.org/2000/svg" class="mr-1 h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                                    <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
                                  </svg>
                                  Remove
                                </button>
                              </div>
                            </td>
                          {/if}
                        </tr>
                      {/each}
                    </tbody>
                  </table>
                </div>
              {:else}
                <div class="p-10 text-center">
                  <div class="rounded-lg border border-dashed border-gray-300 bg-white p-8">
                    <svg xmlns="http://www.w3.org/2000/svg" class="mx-auto mb-4 h-16 w-16 text-gray-400" viewBox="0 0 20 20" fill="currentColor">
                      <path d="M13 6a3 3 0 11-6 0 3 3 0 016 0zM18 8a2 2 0 11-4 0 2 2 0 014 0zM14 15a4 4 0 00-8 0v3h8v-3zM6 8a2 2 0 11-4 0 2 2 0 014 0zM16 18v-3a5.972 5.972 0 00-.75-2.906A3.005 3.005 0 0119 15v3h-3zM4.75 12.094A5.973 5.973 0 004 15v3H1v-3a3 3 0 013.75-2.906z" />
                    </svg>
                    <h3 class="mb-2 text-lg font-medium text-gray-900">No users in this workspace yet</h3>
                    <p class="mb-6 text-gray-500">Add users to start collaborating in this workspace</p>
                    
                    {#if workspace.is_admin}
                      <button
                        class="inline-flex items-center rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700"
                        on:click={showAddUser}
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" class="mr-2 h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                          <path d="M8 9a3 3 0 100-6 3 3 0 000 6zM8 11a6 6 0 016 6H2a6 6 0 016-6zM16 7a1 1 0 10-2 0v1h-1a1 1 0 100 2h1v1a1 1 0 102 0v-1h1a1 1 0 100-2h-1V7z" />
                        </svg>
                        Add users to get started
                      </button>
                    {/if}
                  </div>
                </div>
              {/if}
            </div>
            
            <!-- Blueprints Section -->
            <div class="overflow-hidden rounded-lg bg-white shadow">
              <div class="bg-gradient-to-r from-blue-600 to-blue-700 p-4 text-white">
                <div class="flex items-center justify-between">
                  <div>
                    <h2 class="text-lg font-semibold">Workspace Blueprints</h2>
                    <p class="text-sm text-blue-100">Blueprints shared with workspace members</p>
                  </div>
                  {#if workspace?.is_admin}
                    <button
                      class="flex items-center rounded-md bg-white px-3 py-1.5 text-sm font-medium text-blue-600 hover:bg-blue-50"
                      on:click={showShareBlueprint}
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" class="mr-1 h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                        <path d="M15 8a3 3 0 10-2.977-2.63l-4.94 2.47a3 3 0 100 4.319l4.94 2.47a3 3 0 10.895-1.789l-4.94-2.47a3.027 3.027 0 000-.74l4.94-2.47C13.456 7.68 14.19 8 15 8z" />
                      </svg>
                      Share Blueprint
                    </button>
                  {/if}
                </div>
              </div>
              
              <!-- Share Blueprint Dialog -->
              {#if showShareBlueprintDialog && workspace?.is_admin}
                <div class="border-b bg-gradient-to-b from-blue-50 to-white p-6">
                  <h3 class="mb-4 text-lg font-medium text-blue-800">Share Blueprint with Workspace</h3>
                  
                  {#if shareBlueprintError}
                    <div class="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-700 border border-red-200">
                      <div class="flex">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
                        </svg>
                        <p>{shareBlueprintError}</p>
                      </div>
                    </div>
                  {/if}
                  
                  <div class="mb-4">
                    <label for="blueprint" class="mb-1 block text-sm font-medium text-gray-700">
                      Select Blueprint to Share *
                    </label>
                    {#if isLoadingAvailableBlueprints}
                      <div class="py-2 text-sm text-gray-500">Loading blueprints...</div>
                    {:else if availableBlueprints.length > 0}
                      <div class="relative">
                        <select
                          id="blueprint"
                          class="block w-full appearance-none rounded-md border border-gray-300 py-2 pl-3 pr-10 text-base focus:border-blue-500 focus:outline-none focus:ring-blue-500"
                          bind:value={selectedBlueprintId}
                        >
                          <option value="" disabled selected>Select a blueprint...</option>
                          {#each availableBlueprints as blueprint}
                            <option value={blueprint.id}>{blueprint.name} ({blueprint.provider})</option>
                          {/each}
                        </select>
                        <div class="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-gray-700">
                          <svg class="h-4 w-4 fill-current" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">
                            <path d="M9.293 12.95l.707.707L15.657 8l-1.414-1.414L10 10.828 5.757 6.586 4.343 8z"/>
                          </svg>
                        </div>
                      </div>
                      <p class="mt-1 text-xs text-gray-500">
                        Choose a blueprint to share with all workspace members
                      </p>
                    {:else}
                      <div class="rounded-md bg-yellow-50 p-3 text-sm text-yellow-700 border border-yellow-200">
                        <div class="flex">
                          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
                            <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
                          </svg>
                          <p>No blueprints available to share</p>
                        </div>
                      </div>
                      <p class="mt-2 text-xs text-gray-500">
                        <a href="/blueprints/create" class="text-blue-600 hover:text-blue-800">Create a new blueprint</a> first
                      </p>
                    {/if}
                  </div>
                  
                  <div class="mt-6 flex justify-end space-x-3 border-t border-gray-200 pt-4">
                    <button
                      type="button"
                      class="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50"
                      on:click={() => (showShareBlueprintDialog = false)}
                      disabled={isSharingBlueprint}
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      class="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700 focus:outline-none {isSharingBlueprint || !selectedBlueprintId || availableBlueprints.length === 0 ? 'cursor-not-allowed opacity-70' : ''}"
                      on:click={shareBlueprint}
                      disabled={isSharingBlueprint || !selectedBlueprintId || availableBlueprints.length === 0}
                    >
                      {#if isSharingBlueprint}
                        <span class="flex items-center">
                          <svg
                            class="mr-2 -ml-1 h-4 w-4 animate-spin text-white"
                            xmlns="http://www.w3.org/2000/svg"
                            fill="none"
                            viewBox="0 0 24 24"
                          >
                            <circle
                              class="opacity-25"
                              cx="12"
                              cy="12"
                              r="10"
                              stroke="currentColor"
                              stroke-width="4"
                            ></circle>
                            <path
                              class="opacity-75"
                              fill="currentColor"
                              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                            ></path>
                          </svg>
                          Sharing...
                        </span>
                      {:else}
                        Share Blueprint
                      {/if}
                    </button>
                  </div>
                </div>
              {/if}
              
              <!-- Workspace Blueprints List -->
              {#if isBlueprintLoading}
                <div class="flex justify-center p-12">
                  <LoadingSpinner size="small" message="Loading shared blueprints..." />
                </div>
              {:else if workspaceBlueprints.length > 0}
                <div class="overflow-x-auto">
                  <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 p-4">
                    {#each workspaceBlueprints as blueprint}
                      <div class="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm hover:shadow-md transition-all duration-200">
                        <div class="border-b border-gray-200 bg-gray-50 p-3">
                          <div class="flex items-center justify-between">
                            <h3 class="text-md font-medium text-gray-900 truncate" title={blueprint.name}>
                              {blueprint.name}
                            </h3>
                            <span class="rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-800">
                              {blueprint.provider}
                            </span>
                          </div>
                        </div>
                        
                        <div class="p-3">
                          {#if blueprint.description}
                            <p class="mb-3 text-sm text-gray-600 line-clamp-2">{blueprint.description}</p>
                          {:else}
                            <p class="mb-3 text-sm italic text-gray-400">No description</p>
                          {/if}
                          
                          <div class="flex space-x-2 text-xs mb-3">
                            <span class={`rounded px-2 py-1 ${blueprint.vnc ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-400'}`}>
                              VNC {blueprint.vnc ? '✓' : '✗'}
                            </span>
                            <span class={`rounded px-2 py-1 ${blueprint.vpn ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-400'}`}>
                              VPN {blueprint.vpn ? '✓' : '✗'}
                            </span>
                          </div>
                          
                          <div class="flex border-t border-gray-100 pt-3">
                            <a
                              href={`/blueprints/${blueprint.blueprint_id}`}
                              class="flex-1 rounded-md bg-blue-500 px-3 py-2 text-center text-sm font-medium text-white shadow-sm hover:bg-blue-600"
                            >
                              View Details
                            </a>
                            
                            {#if workspace?.is_admin}
                              <button
                                class="ml-2 rounded-md border border-red-300 bg-white px-3 py-2 text-sm font-medium text-red-700 shadow-sm hover:bg-red-50"
                                on:click={() => confirmRemoveBlueprint(blueprint)}
                              >
                                Unshare
                              </button>
                            {/if}
                          </div>
                        </div>
                      </div>
                    {/each}
                  </div>
                </div>
              {:else}
                <div class="p-10 text-center">
                  <div class="rounded-lg border border-dashed border-gray-300 bg-white p-8">
                    <svg xmlns="http://www.w3.org/2000/svg" class="mx-auto mb-4 h-16 w-16 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <h3 class="mb-2 text-lg font-medium text-gray-900">No blueprints shared in this workspace</h3>
                    <p class="mb-6 text-gray-500">Share blueprints with workspace members for collaboration</p>
                    
                    {#if workspace?.is_admin}
                      <button
                        class="inline-flex items-center rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700"
                        on:click={showShareBlueprint}
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" class="mr-2 h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                          <path d="M15 8a3 3 0 10-2.977-2.63l-4.94 2.47a3 3 0 100 4.319l4.94 2.47a3 3 0 10.895-1.789l-4.94-2.47a3.027 3.027 0 000-.74l4.94-2.47C13.456 7.68 14.19 8 15 8z" />
                        </svg>
                        Share your first blueprint
                      </button>
                    {/if}
                  </div>
                </div>
              {/if}
            </div>
            
            <!-- Confirm Remove Blueprint Modal -->
            {#if showRemoveBlueprintConfirm && blueprintToRemove}
              <div class="fixed inset-0 z-50 flex items-center justify-center">
                <!-- Backdrop -->
                <div
                  class="absolute inset-0 bg-gray-800 bg-opacity-75 transition-opacity"
                  on:click={() => !isRemovingBlueprint && (showRemoveBlueprintConfirm = false)}
                  on:keydown={(e) => e.key === 'Escape' && !isRemovingBlueprint && (showRemoveBlueprintConfirm = false)}
                  role="presentation"
                ></div>
                
                <!-- Modal dialog -->
                <div class="relative w-full max-w-md rounded-lg bg-white shadow-xl">
                  <div class="p-6">
                    {#if removeBlueprintError}
                      <div class="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-700">
                        <p>{removeBlueprintError}</p>
                      </div>
                    {/if}
                    
                    <div class="mb-4 text-center">
                      <svg
                        class="mx-auto mb-4 h-12 w-12 text-red-500"
                        xmlns="http://www.w3.org/2000/svg"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          stroke-linecap="round"
                          stroke-linejoin="round"
                          stroke-width="2"
                          d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                        />
                      </svg>
                      <h3 class="text-xl font-bold text-gray-900">
                        Unshare Blueprint
                      </h3>
                      <p class="mt-2 text-gray-600">
                        Are you sure you want to unshare <strong>{blueprintToRemove.name}</strong> from this workspace? Workspace members will no longer have access to this blueprint.
                      </p>
                    </div>
                    
                    <div class="mt-6 flex justify-end space-x-3">
                      <button
                        class="rounded border border-gray-300 bg-white px-4 py-2 text-gray-700 hover:bg-gray-50"
                        on:click={() => (showRemoveBlueprintConfirm = false)}
                        disabled={isRemovingBlueprint}
                      >
                        Cancel
                      </button>
                      <button
                        class="rounded bg-red-500 px-4 py-2 text-white hover:bg-red-600 disabled:opacity-70"
                        on:click={removeBlueprint}
                        disabled={isRemovingBlueprint}
                      >
                        {#if isRemovingBlueprint}
                          <span class="flex items-center">
                            <svg
                              class="mr-2 -ml-1 h-4 w-4 animate-spin text-white"
                              xmlns="http://www.w3.org/2000/svg"
                              fill="none"
                              viewBox="0 0 24 24"
                            >
                              <circle
                                class="opacity-25"
                                cx="12"
                                cy="12"
                                r="10"
                                stroke="currentColor"
                                stroke-width="4"
                              ></circle>
                              <path
                                class="opacity-75"
                                fill="currentColor"
                                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                              ></path>
                            </svg>
                            Unsharing...
                          </span>
                        {:else}
                          Unshare
                        {/if}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            {/if}
          </div>
        </div>
      {:else}
        <div class="w-full p-10 text-center">
          <div class="rounded-lg border border-blue-200 bg-blue-50 p-8 text-blue-800 shadow-sm">
            <div class="mb-4">
              <svg xmlns="http://www.w3.org/2000/svg" class="mx-auto mb-2 h-16 w-16 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <h3 class="mb-2 text-xl font-bold">Workspace Not Found</h3>
            </div>
            <p class="mb-6 text-blue-700">
              The workspace you are looking for does not exist or you don't have access to it.
            </p>
            <a
              href="/workspaces"
              class="rounded-md bg-blue-600 px-6 py-3 font-medium text-white shadow-sm transition-colors hover:bg-blue-700 inline-block"
            >
              Back to Workspaces
            </a>
          </div>
        </div>
      {/if}
      
      <!-- Delete Workspace Confirmation Modal -->
      {#if showDeleteConfirm && workspace}
        <div class="fixed inset-0 z-50 flex items-center justify-center">
          <!-- Backdrop -->
          <div 
            class="absolute inset-0 bg-gray-800 bg-opacity-75 transition-opacity"
            on:click={() => !isDeleting && (showDeleteConfirm = false)}
            on:keydown={(e) => e.key === 'Escape' && !isDeleting && (showDeleteConfirm = false)}
            role="presentation"
          ></div>
          
          <!-- Modal dialog -->
          <div class="relative w-full max-w-md rounded-lg bg-white shadow-xl">
            <div class="p-6">
              {#if deleteError}
                <div class="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-700">
                  <p>{deleteError}</p>
                </div>
              {/if}
              
              <div class="mb-4 text-center">
                <svg 
                  class="mx-auto mb-4 h-12 w-12 text-red-500" 
                  xmlns="http://www.w3.org/2000/svg" 
                  fill="none" 
                  viewBox="0 0 24 24" 
                  stroke="currentColor"
                >
                  <path 
                    stroke-linecap="round" 
                    stroke-linejoin="round" 
                    stroke-width="2" 
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" 
                  />
                </svg>
                <h3 class="text-xl font-bold text-gray-900">
                  Delete Workspace
                </h3>
                <p class="mt-2 text-gray-600">
                  Are you sure you want to delete <strong>{workspace.name}</strong>? This will remove all workspace members and this action cannot be undone.
                </p>
              </div>
              
              <div class="mt-6 flex justify-end space-x-3">
                <button
                  class="rounded border border-gray-300 bg-white px-4 py-2 text-gray-700 hover:bg-gray-50"
                  on:click={() => (showDeleteConfirm = false)}
                  disabled={isDeleting}
                >
                  Cancel
                </button>
                <button
                  class="rounded bg-red-500 px-4 py-2 text-white hover:bg-red-600 disabled:opacity-70"
                  on:click={deleteWorkspace}
                  disabled={isDeleting}
                >
                  {#if isDeleting}
                    <span class="flex items-center">
                      <svg
                        class="mr-2 -ml-1 h-4 w-4 animate-spin text-white"
                        xmlns="http://www.w3.org/2000/svg"
                        fill="none"
                        viewBox="0 0 24 24"
                      >
                        <circle
                          class="opacity-25"
                          cx="12"
                          cy="12"
                          r="10"
                          stroke="currentColor"
                          stroke-width="4"
                        ></circle>
                        <path
                          class="opacity-75"
                          fill="currentColor"
                          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                        ></path>
                      </svg>
                      Deleting...
                    </span>
                  {:else}
                    Delete
                  {/if}
                </button>
              </div>
            </div>
          </div>
        </div>
      {/if}

      <!-- Remove User Confirmation Modal -->
      {#if showRemoveUserConfirm && userToRemove}
        <div class="fixed inset-0 z-50 flex items-center justify-center">
          <!-- Backdrop with blur effect -->
          <div 
            class="absolute inset-0 bg-gray-800 bg-opacity-75 backdrop-blur-sm transition-opacity"
            on:click={() => !isRemovingUser && (showRemoveUserConfirm = false)}
            on:keydown={(e) => e.key === 'Escape' && !isRemovingUser && (showRemoveUserConfirm = false)}
            role="presentation"
          ></div>
          
          <!-- Modal dialog -->
          <div class="relative w-full max-w-md transform overflow-hidden rounded-lg bg-white shadow-xl transition-all">
            <div class="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-red-500 to-red-600"></div>
            
            <div class="p-6">
              {#if removeUserError}
                <div class="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-700 border border-red-200">
                  <div class="flex">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
                    </svg>
                    <p>{removeUserError}</p>
                  </div>
                </div>
              {/if}
              
              <div class="flex items-center">
                <div class="flex-shrink-0 h-12 w-12 bg-red-100 rounded-full flex items-center justify-center text-red-500">
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
                  </svg>
                </div>
                <div class="ml-4">
                  <h3 class="text-lg font-medium text-gray-900">
                    Remove User
                  </h3>
                  <p class="text-sm text-gray-500">
                    This will remove the user's access to this workspace
                  </p>
                </div>
              </div>
              
              <div class="mt-4 bg-gray-50 p-4 rounded-md border border-gray-200">
                <p class="text-gray-700">
                  Are you sure you want to remove <span class="font-semibold text-gray-900">{userToRemove.userName}</span> from this workspace?
                </p>
                <p class="mt-2 text-sm text-gray-500">
                  This user will lose access to all shared blueprints in this workspace. They can be added back later if needed.
                </p>
              </div>
              
              <div class="mt-6 flex justify-end space-x-3">
                <button
                  class="flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 transition-colors focus:outline-none focus:ring-2 focus:ring-gray-300"
                  on:click={() => (showRemoveUserConfirm = false)}
                  disabled={isRemovingUser}
                >
                  Cancel
                </button>
                <button
                  class="flex items-center rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-red-700 transition-colors focus:outline-none focus:ring-2 focus:ring-red-300 disabled:opacity-70"
                  on:click={removeUser}
                  disabled={isRemovingUser}
                >
                  {#if isRemovingUser}
                    <svg
                      class="mr-2 h-4 w-4 animate-spin text-white"
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <circle
                        class="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        stroke-width="4"
                      ></circle>
                      <path
                        class="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      ></path>
                    </svg>
                    Removing...
                  {:else}
                    Remove User
                  {/if}
                </button>
              </div>
            </div>
          </div>
        </div>
      {/if}
    </div>
  </div>
</div>
