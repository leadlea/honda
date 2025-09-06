export interface User {
  user_id: string;
  employee_id: string;
  email: string;
  name: string;
  department: string;
  join_date: string;
  role: 'veteran' | 'admin' | 'external_recruiter';
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AuthState {
  isAuthenticated: boolean;
  user: User | null;
  loading: boolean;
  error: string | null;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface SignUpData {
  email: string;
  password: string;
  name: string;
  employee_id: string;
  department: string;
}