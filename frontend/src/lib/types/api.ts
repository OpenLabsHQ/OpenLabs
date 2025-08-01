// Base API response types
export interface ApiResponse<T> {
  data?: T;
  error?: string;
  status?: number;
  isAuthError?: boolean;
}

// User related types
export interface User {
  id: string;
  name: string;
  email: string;
  admin?: boolean;
  authenticated?: boolean;
}

export interface UserSecrets {
  aws_configured: boolean;
  azure_configured: boolean;
}

export interface LoginResponse {
  message: string;
  user?: User;
}

export interface RegisterResponse {
  message: string;
  user?: User;
}

// Job system types
export interface JobSubmissionResponse {
  arq_job_id: string;
  detail: string;
}

// Job result types for different job types
export interface DeployJobResult {
  range_id?: string | number;
  range?: {
    id: string | number;
    name?: string;
  };
  message?: string;
}

export interface DestroyJobResult {
  message?: string;
  range_id?: string | number;
}

export interface Job {
  arq_job_id: string;
  job_name: string;
  job_try: number | null;
  enqueue_time: string;
  start_time: string | null;
  finish_time: string | null;
  status: 'queued' | 'in_progress' | 'complete' | 'failed' | 'not_found';
  result: DeployJobResult | DestroyJobResult | Record<string, unknown> | null;
  error_message: string | null;
  id: number;
}

// Range related types
export interface DeployedHost {
  id: string;
  hostname: string;
  ip_address?: string;
  status: string;
  os: string;
  spec: string;
  size: number;
}

export interface DeployedSubnet {
  id: string;
  name: string;
  cidr: string;
  hosts: DeployedHost[];
}

export interface DeployedVPC {
  id: string;
  name: string;
  cidr: string;
  subnets: DeployedSubnet[];
}

export interface DeployedRange {
  id: string;
  name: string;
  description: string;
  provider: string;
  region: string;
  status: 'building' | 'ready' | 'error' | 'destroying';
  created_at: string;
  updated_at: string;
  vpcs: DeployedVPC[];
  vnc_enabled: boolean;
  vpn_enabled: boolean;
  readme?: string;
}

export interface RangeSSHKey {
  private_key: string;
  public_key: string;
}

// Blueprint related types
export interface BlueprintHost {
  hostname: string;
  os: string;
  spec: string;
  size: number;
  tags: string[];
  count?: number;
}

export interface BlueprintSubnet {
  name: string;
  cidr: string;
  hosts: BlueprintHost[];
}

export interface BlueprintVPC {
  name: string;
  cidr: string;
  subnets: BlueprintSubnet[];
}

export interface BlueprintRange {
  id?: number;
  name: string;
  description?: string;
  provider: string;
  vnc: boolean;
  vpn: boolean;
  vpcs: BlueprintVPC[];
  created_at?: string;
  updated_at?: string;
  user_id?: string;
}

// Network graph types
export interface NetworkNode {
  id: string;
  label: string;
  group: 'vpc' | 'subnet' | 'host';
  level?: number;
  color?: string;
}

export interface NetworkEdge {
  from: string;
  to: string;
  color?: string;
}

export interface NetworkGraphData {
  nodes: NetworkNode[];
  edges: NetworkEdge[];
}

// Validation error types (from FastAPI)
export interface ValidationError {
  loc: (string | number)[];
  msg: string;
  type: string;
}

export interface HTTPValidationError {
  detail: ValidationError[];
}

// Generic error response
export interface ErrorResponse {
  detail: string | ValidationError[];
  message?: string;
}

// Password update types
export interface PasswordUpdateRequest {
  current_password: string;
  new_password: string;
}

export interface PasswordUpdateResponse {
  message: string;
}

// Secrets verification response
export interface SecretsRequest {
  provider: string;
  credentials: any;
}
export interface SecretsResponse {
  message: string;
}

// Deploy range request
export interface DeployRangeRequest {
  blueprint_id: number;
  name: string;
  description: string;
  region: 'us_east_1' | 'us_east_2';
  readme?: string | null;
}