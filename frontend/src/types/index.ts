// Helper Types
export type UserRole = 'admin' | 'member';
export type TaskStatus = 'todo' | 'in_progress' | 'done';

// Auth Request Types
export interface UserRegister {
  email: string;
  password: string;
  organization_name: string;
  name?: string;
}

export interface UserLogin {
  email: string;
  password: string;
}

export interface OTPVerify {
  email: string;
  otp: string;
}

// Auth Response Types
export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

// User Model
export interface User {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  org_id: string;
  created_at: string;
}

// Task Request Types
export interface TaskCreate {
  title: string;
  description?: string | null;
  status: TaskStatus;
  due_date?: string | null;
  assignee_id?: string | null;
}

export interface TaskUpdate {
  title?: string;
  description?: string | null;
  status?: TaskStatus;
  due_date?: string | null;
  assignee_id?: string | null;
}

// Task Response Type
export interface Task {
  id: string;
  title: string;
  description?: string | null;
  status: TaskStatus;
  due_date?: string | null;
  assignee_id?: string | null;
  org_id: string;
  created_by_id: string;
  created_at: string;
  assignee?: User;
}

// Organization Model
export interface Organization {
  id: string;
  name: string;
  domain: string;
  created_at: string;
}