// Workspace role types
export type WorkspaceRole = 'admin' | 'member';

// Workspace model
export interface Workspace {
  id: string;
  name: string;
  description: string;
  created_at: string;
  updated_at: string;
  default_time_limit?: number;
  is_admin: boolean; // Whether the current user is an admin of this workspace
}

// Workspace user model
export interface WorkspaceUser {
  id: string;
  user_id: string;
  workspace_id: string;
  name: string; // User's name
  email: string; // User's email
  role: WorkspaceRole;
  time_limit?: number; // Optional time limit in minutes
  created_at: string;
  updated_at: string;
}

// Model for creating a new workspace
export interface WorkspaceCreate {
  name: string;
  description: string;
  default_time_limit?: number;
}

// Model for updating a workspace
export interface WorkspaceUpdate {
  name?: string;
  description?: string;
  default_time_limit?: number;
}

// Model for adding a user to a workspace
export interface WorkspaceUserCreate {
  user_id: string;
  role: WorkspaceRole;
  time_limit?: number;
}

// Available user model (for users not yet in workspace)
export interface AvailableUser {
  id?: string;
  name: string;
  email: string;
  admin?: boolean;
}