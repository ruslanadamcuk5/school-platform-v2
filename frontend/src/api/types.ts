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

export interface Region {
  id: string;
  code: string;
  name: string;
  created_at: string;
}

export interface City {
  id: string;
  region_id: string;
  code: string;
  name: string;
  city_type: string;
  created_at: string;
}

export interface School {
  id: string;
  code: string;
  name: string;
  short_name: string | null;
  institution_type: 'school' | 'college' | 'university';
  education_levels: EducationLevel[];
  profile: Record<string, unknown>;
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
  education_level: EducationLevel;
  program_id: string | null;
  course_year: number | null;
  profile: Record<string, unknown>;
  title: string | null;
  academic_year: string;
  homeroom_teacher_id: string | null;
  is_active: boolean;
  created_at: string;
  display_name: string;
}

export type EducationLevel = 'primary' | 'secondary' | 'vocational' | 'higher';

export interface EducationLevelInfo {
  code: EducationLevel;
  name: string;
  short_name: string;
  icon: string;
  description: string;
  service_code: string;
  read_permission: string;
  manage_permission: string;
  program_permission: string | null;
  profile_read_permission: string | null;
  profile_manage_permission: string | null;
  is_professional: boolean;
}

export interface EducationGroup {
  id: string;
  name: string;
  grade: number;
  letter: string;
  education_level: EducationLevel;
  course_year: number | null;
  program_id: string | null;
  program_name: string | null;
  academic_year: string;
  students: number;
  curator_name: string | null;
  is_active: boolean;
}

export interface EducationProgram {
  id: string;
  institution_id: string;
  code: string;
  name: string;
  education_level: EducationLevel;
  qualification: string | null;
  duration_years: number | null;
  profile: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface StudentAcademicProfile {
  id: string;
  user_id: string;
  login: string;
  full_name: string;
  institution_id: string;
  program_id: string | null;
  program_name: string | null;
  group_id: string | null;
  group_name: string | null;
  course_year: number | null;
  record_book_number: string | null;
  funding_type: 'budget' | 'paid' | 'target' | 'other';
  enrollment_year: number | null;
  academic_status: 'active' | 'academic_leave' | 'expelled' | 'graduated';
  profile: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface StaffAcademicProfile {
  id: string;
  user_id: string;
  login: string;
  full_name: string;
  institution_id: string;
  department: string | null;
  position: string | null;
  academic_degree: string | null;
  academic_title: string | null;
  profile: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export type CurriculumStatus = 'draft' | 'approved' | 'archived';
export type CurriculumComponentType =
  | 'discipline'
  | 'module'
  | 'practice'
  | 'coursework'
  | 'internship'
  | 'other';
export type AssessmentType =
  | 'exam'
  | 'credit'
  | 'differentiated_credit'
  | 'coursework'
  | 'practice_report'
  | 'other';

export interface CurriculumComponent {
  id: string;
  curriculum_id: string;
  code: string;
  name: string;
  component_type: CurriculumComponentType;
  semester: number;
  credits: number;
  academic_hours: number;
  contact_hours: number;
  assessment_type: AssessmentType;
  is_optional: boolean;
  order_index: number;
  description: string | null;
  details: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface EducationCurriculum {
  id: string;
  institution_id: string;
  program_id: string;
  program_name: string;
  education_level: EducationLevel;
  academic_year: string;
  name: string;
  description: string | null;
  status: CurriculumStatus;
  approved_at: string | null;
  approved_by_id: string | null;
  profile: Record<string, unknown>;
  total_credits: number;
  components: CurriculumComponent[];
  created_at: string;
  updated_at: string;
}

export interface EducationTotals {
  students: number;
  teachers: number;
  groups: number;
  programs: number;
}

export interface EducationOverview {
  institution_id: string;
  institution_name: string;
  institution_type: 'school' | 'college' | 'university';
  institution_type_label: string;
  education_levels: EducationLevel[];
  level: EducationLevelInfo;
  academic_year: string;
  available_years: string[];
  generated_at: string;
  totals: EducationTotals;
  groups: EducationGroup[];
  programs: EducationProgram[];
  student_profiles_count: number;
  staff_profiles_count: number;
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

export interface AnalyticsTotals {
  students: number;
  teachers: number;
  classes: number;
  grades_count: number;
}

export interface AnalyticsGrades {
  average: number | null;
  distribution: Record<string, number>;
  excellent: number;
  good: number;
  satisfactory: number;
  low: number;
}

export interface AnalyticsAttendance {
  total: number;
  present: number;
  absent: number;
  sick: number;
  late: number;
  excused: number;
  rate: number | null;
}

export interface AnalyticsSubject {
  subject_id: string;
  subject_name: string;
  grades_count: number;
  average: number | null;
  attendance_total: number;
  attendance_rate: number | null;
}

export interface AnalyticsClass {
  class_id: string;
  class_name: string;
  grade: number;
  letter: string;
  students: number;
  grades_count: number;
  average: number | null;
  attendance_total: number;
  attendance_rate: number | null;
}

export interface AnalyticsOverview {
  school_id: string;
  school_name: string;
  academic_year: string;
  available_years: string[];
  generated_at: string;
  totals: AnalyticsTotals;
  grades: AnalyticsGrades;
  attendance: AnalyticsAttendance;
  subjects: AnalyticsSubject[];
  classes: AnalyticsClass[];
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

export type OnboardingStatus =
  | 'not_started'
  | 'in_progress'
  | 'completed'
  | 'skipped';

export interface OnboardingStep {
  code: string;
  title: string;
  body: string;
  target: string | null;
  route: string | null;
  tip: string | null;
  action: 'next' | 'click';
  duration_seconds: number;
  completed: boolean;
}

export interface OnboardingModule {
  code: string;
  service_code: string;
  service_name: string;
  service_icon: string;
  stage: string;
  title: string;
  description: string;
  icon: string;
  estimated_minutes: number;
  roles: string[] | null;
  is_addon: boolean;
  status: OnboardingStatus;
  current_step_code: string | null;
  completed_steps: number;
  total_steps: number;
  progress_percent: number;
  started_at: string | null;
  completed_at: string | null;
  last_activity_at: string | null;
  steps: OnboardingStep[];
}

export interface OnboardingStage {
  code: string;
  title: string;
  description: string;
  modules: OnboardingModule[];
  total: number;
  completed: number;
  progress_percent: number;
}

export interface OnboardingOverview {
  user_id: string;
  role: Role;
  catalog_version: string;
  generated_at: string;
  known_service_codes: string[];
  stages: OnboardingStage[];
  modules: OnboardingModule[];
  total: number;
  completed: number;
  in_progress: number;
  not_started: number;
  addon_total: number;
  progress_percent: number;
}

export interface OnboardingProgress {
  module_code: string;
  status: OnboardingStatus;
  current_step_code: string | null;
  completed_steps: number;
  total_steps: number;
  progress_percent: number;
  started_at: string | null;
  completed_at: string | null;
  last_activity_at: string | null;
}

export interface OnboardingReportSummary {
  total_users: number;
  users_not_started: number;
  users_in_progress: number;
  users_completed: number;
  modules_total: number;
  modules_completed: number;
  modules_in_progress: number;
  addon_modules: number;
  progress_percent: number;
  by_role: Record<string, number>;
}

export interface OnboardingReportUser {
  user_id: string;
  login: string;
  full_name: string;
  role: Role;
  school_id: string | null;
  school_name: string | null;
  modules_total: number;
  modules_completed: number;
  modules_in_progress: number;
  addon_modules: number;
  status: OnboardingStatus;
  progress_percent: number;
  last_activity_at: string | null;
}

export interface OnboardingReportUsers {
  items: OnboardingReportUser[];
  total: number;
  limit: number;
  offset: number;
  summary: OnboardingReportSummary;
}
