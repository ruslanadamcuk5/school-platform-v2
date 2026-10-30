export type Role =
  | 'superadmin'
  | 'admin'
  | 'methodologist'
  | 'teacher'
  | 'student'
  | 'parent'
  | 'psychologist'
  | 'secretary';

export type ScopeType = 'country' | 'region' | 'city' | 'school' | 'class';

export interface User {
  id: string;
  school_id: string | null;
  login: string;
  email: string | null;
  role: Role;
  first_name: string;
  last_name: string;
  middle_name: string | null;
  full_name: string;
  phone: string | null;
  avatar: string;
  locale: string;
  timezone: string;
  is_active: boolean;
  is_verified: boolean;
  must_change_password: boolean;
  last_login_at: string | null;
  created_at: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  refresh_expires_in: number;
  user: User;
}

export interface Service {
  code: string;
  name: string;
  description: string | null;
  version: string;
  category:
    | 'core'
    | 'education'
    | 'management'
    | 'communication'
    | 'analytics'
    | 'ai'
    | 'security';
  api_prefix: string;
  icon: string;
  default_enabled: boolean;
  is_core: boolean;
  status: 'active' | 'beta' | 'disabled';
  manifest: {
    permissions?: Array<{ code: string; name: string; category: string }>;
    depends_on?: string[];
  };
}

export interface EffectiveService {
  code: string;
  name: string;
  description: string | null;
  icon: string;
  category: Service['category'];
  api_prefix: string;
  status: Service['status'];
  enabled: boolean;
  source: 'core' | 'activation' | 'default';
  permission_codes: string[];
}

export interface MyServices {
  items: EffectiveService[];
  total: number;
}

export interface Permission {
  id: string;
  code: string;
  name: string;
  description: string | null;
  service_code: string;
  category: 'read' | 'write' | 'admin' | 'use';
  is_system: boolean;
}

export interface PermissionList {
  items: Permission[];
  total: number;
}

export interface EffectivePermission {
  code: string;
  allowed: boolean;
  effect: 'allow' | 'deny';
  scope_type: ScopeType;
  group_id: string;
  group_code: string;
  group_name: string;
  depth: number;
}

export interface Group {
  id: string;
  code: string;
  name: string;
  description: string | null;
  category:
    | 'students'
    | 'teachers'
    | 'administration'
    | 'methodologists'
    | 'psychologists'
    | 'secretaries'
    | 'parents'
    | 'other';
  scope_type: ScopeType;
  scope_id: string;
  depth: number;
  parent_id: string | null;
  is_system: boolean;
  is_active: boolean;
  members_count: number;
  permissions_count: number;
  created_at: string;
}

export interface GroupMember {
  user_id: string;
  login: string;
  full_name: string;
  role: Role;
  assigned_at: string;
  expires_at: string | null;
  is_primary: boolean;
}

export interface GroupPermission {
  permission_code: string;
  permission_name: string;
  effect: 'allow' | 'deny';
  granted_at: string;
  expires_at: string | null;
}

export interface GroupDetail extends Group {
  members: GroupMember[];
  permissions: GroupPermission[];
  children: Group[];
}

export interface GroupList {
  items: Group[];
  total: number;
}

export interface MyPermissions {
  user_id: string;
  role: Role;
  permissions: string[];
  denied: string[];
  details: EffectivePermission[];
  groups: Group[];
}

export interface School {
  id: string;
  code: string;
  name: string;
  short_name: string | null;
  city: string | null;
  address: string | null;
  phone: string | null;
  email: string | null;
  is_active: boolean;
  created_at: string;
}

export interface SchoolClass {
  id: string;
  school_id: string;
  grade: number;
  letter: string;
  title: string | null;
  academic_year: string;
  homeroom_teacher_id: string | null;
  is_active: boolean;
  created_at: string;
  display_name: string;
}

export interface UserList {
  items: User[];
  total: number;
  limit: number;
  offset: number;
}

export interface AdminStats {
  school_id: string;
  users_total: number;
  users_active: number;
  by_role: Record<string, number>;
  classes_total: number;
  classes_active: number;
}

export interface Health {
  status: 'ok' | 'degraded';
  service: string;
  version: string;
  environment: string;
  database: 'ok' | 'error';
  jwt_ready: boolean;
  time: string;
}

export interface AuditEvent {
  id: string;
  school_id: string | null;
  user_id: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  details: Record<string, unknown>;
  ip_address: string | null;
  created_at: string;
}

export interface AuditList {
  items: AuditEvent[];
  limit: number;
  offset: number;
}
