import axios, { AxiosError, type AxiosRequestConfig } from 'axios';

import type {
  AcademicSession,
  AdminStats,
  AnalyticsOverview,
  AssessmentType,
  City,
  Competency,
  CompetencyMatrix,
  CompetencyType,
  CreditTransfer,
  CreditTransferStatus,
  CurriculumComponent,
  CurriculumComponentType,
  CurriculumStatus,
  EducationCurriculum,
  EducationGroup,
  EducationLevel,
  EducationOverview,
  EducationProgram,
  EffectiveService,
  Group,
  GroupDetail,
  GroupList,
  Health,
  MyPermissions,
  MyServices,
  OnboardingModule,
  OnboardingOverview,
  OnboardingProgress,
  OnboardingReportUsers,
  PermissionList,
  ProgramCompetency,
  Region,
  School,
  SchoolClass,
  Service,
  SessionStatement,
  SessionStatus,
  SessionType,
  StaffAcademicProfile,
  StatementRecord,
  StatementResult,
  StudentAcademicProfile,
  TokenPair,
  Transcript,
  User,
  UserList,
} from './types';

const ACCESS_KEY = 'school.access_token';
const REFRESH_KEY = 'school.refresh_token';
const USER_KEY = 'school.user';

export const API_BASE = (import.meta.env.VITE_API_URL as string | undefined) || '/api/v1';

const explicitOrigin = API_BASE.match(/^https?:\/\/[^/]+/)?.[0];

export const API_ORIGIN =
  explicitOrigin ?? (import.meta.env.DEV ? 'http://127.0.0.1:8000' : window.location.origin);

export const api = axios.create({
  baseURL: API_BASE,
  timeout: 20000,
  headers: { 'Content-Type': 'application/json' },
});

const refreshClient = axios.create({
  baseURL: API_BASE,
  timeout: 20000,
  headers: { 'Content-Type': 'application/json' },
});

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_KEY);
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_KEY);
}

export function getStoredUser(): User | null {
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as User;
  } catch {
    return null;
  }
}

export function storeSession(tokens: TokenPair): void {
  localStorage.setItem(ACCESS_KEY, tokens.access_token);
  localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
  localStorage.setItem(USER_KEY, JSON.stringify(tokens.user));
}

export function storeUser(user: User): void {
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearSession(): void {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
  localStorage.removeItem(USER_KEY);
}

api.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return null;

  if (!refreshPromise) {
    refreshPromise = refreshClient
      .post<TokenPair>('/auth/refresh', { refresh_token: refreshToken })
      .then((response) => {
        storeSession(response.data);
        return response.data.access_token;
      })
      .catch(() => {
        clearSession();
        window.dispatchEvent(new Event('auth:logout'));
        return null;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }

  return refreshPromise;
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as (AxiosRequestConfig & { _retry?: boolean }) | undefined;
    const status = error.response?.status;
    const isAuthCall = original?.url?.includes('/auth/');

    if (status === 401 && original && !original._retry && !isAuthCall) {
      original._retry = true;
      const token = await refreshAccessToken();
      if (token) {
        original.headers = { ...(original.headers || {}), Authorization: `Bearer ${token}` };
        return api.request(original);
      }
    }

    return Promise.reject(error);
  },
);

export function apiErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((item) => (typeof item?.msg === 'string' ? item.msg : JSON.stringify(item)))
        .join('; ');
    }
    if (error.code === 'ECONNABORTED') return 'Сервер не ответил вовремя.';
    if (!error.response) return 'Нет связи с API. Проверьте, запущен ли backend.';
    return `Ошибка API (${error.response.status}).`;
  }
  if (error instanceof Error) return error.message;
  return 'Неизвестная ошибка.';
}

export async function loginRequest(login: string, password: string): Promise<TokenPair> {
  const { data } = await api.post<TokenPair>('/auth/login', { login, password });
  return data;
}

export async function meRequest(): Promise<User> {
  const { data } = await api.get<User>('/auth/me');
  return data;
}

export async function logoutRequest(): Promise<void> {
  const refreshToken = getRefreshToken();
  try {
    await api.post('/auth/logout', { refresh_token: refreshToken });
  } finally {
    clearSession();
  }
}

export async function healthRequest(): Promise<Health> {
  const { data } = await axios.get<Health>(
    explicitOrigin ? `${explicitOrigin}/health` : '/health',
    { timeout: 8000 },
  );
  return data;
}

export async function fetchMyPermissions(): Promise<MyPermissions> {
  const { data } = await api.get<MyPermissions>('/me/permissions');
  return data;
}

export async function fetchMyServices(): Promise<MyServices> {
  const { data } = await api.get<MyServices>('/me/services');
  return data;
}

export async function fetchServices(): Promise<{ items: Service[]; total: number }> {
  const { data } = await api.get<{ items: Service[]; total: number }>('/services');
  return data;
}

export async function fetchEffectiveServices(
  scopeType = 'country',
  scopeId?: string,
): Promise<MyServices> {
  const { data } = await api.get<MyServices>('/services/effective', {
    params: { scope_type: scopeType, scope_id: scopeId || undefined },
  });
  return data;
}

export async function setServiceActivation(
  code: string,
  enabled: boolean,
  scopeType = 'country',
  scopeId?: string,
): Promise<void> {
  await api.put(
    `/services/${encodeURIComponent(code)}/activation`,
    { enabled, config: {} },
    { params: { scope_type: scopeType, scope_id: scopeId || undefined } },
  );
}

export async function fetchGroups(params?: {
  limit?: number;
  offset?: number;
  scope_type?: string;
  category?: string;
  search?: string;
  include_inactive?: boolean;
}): Promise<GroupList> {
  const { data } = await api.get<GroupList>('/groups', {
    params: {
      limit: params?.limit ?? 200,
      offset: params?.offset ?? 0,
      scope_type: params?.scope_type || undefined,
      category: params?.category || undefined,
      search: params?.search || undefined,
      include_inactive: params?.include_inactive || undefined,
    },
  });
  return data;
}

export async function fetchGroup(id: string): Promise<GroupDetail> {
  const { data } = await api.get<GroupDetail>(`/groups/${id}`);
  return data;
}

export async function fetchPermissions(): Promise<PermissionList> {
  const { data } = await api.get<PermissionList>('/groups/permissions');
  return data;
}

export async function createGroup(payload: {
  code: string;
  name: string;
  description?: string | null;
  category: Group['category'];
  scope_type: Group['scope_type'];
  scope_id?: string | null;
  parent_id?: string | null;
}): Promise<GroupDetail> {
  const { data } = await api.post<GroupDetail>('/groups', payload);
  return data;
}

export async function addGroupMembers(
  groupId: string,
  userIds: string[],
): Promise<GroupDetail> {
  const { data } = await api.post<GroupDetail>(`/groups/${groupId}/members`, {
    user_ids: userIds,
    is_primary: true,
  });
  return data;
}

export async function removeGroupMember(groupId: string, userId: string): Promise<void> {
  await api.delete(`/groups/${groupId}/members/${userId}`);
}

export async function setGroupPermission(
  groupId: string,
  permissionCode: string,
  effect: 'allow' | 'deny' = 'allow',
): Promise<void> {
  await api.put(
    `/groups/${groupId}/permissions/${encodeURIComponent(permissionCode)}`,
    { effect, expires_at: null },
  );
}

export async function removeGroupPermission(
  groupId: string,
  permissionCode: string,
): Promise<void> {
  await api.delete(`/groups/${groupId}/permissions/${encodeURIComponent(permissionCode)}`);
}

export async function fetchRegions(): Promise<Region[]> {
  const { data } = await api.get<Region[]>('/org/regions');
  return data;
}

export async function fetchCities(regionId?: string): Promise<City[]> {
  const { data } = await api.get<City[]>('/org/cities', {
    params: { region_id: regionId || undefined },
  });
  return data;
}

export async function fetchSchools(): Promise<School[]> {
  const { data } = await api.get<School[]>('/org/schools');
  return data;
}

export async function fetchClasses(schoolId: string): Promise<SchoolClass[]> {
  const { data } = await api.get<SchoolClass[]>('/org/classes', {
    params: { school_id: schoolId },
  });
  return data;
}

export async function createSchool(payload: {
  code: string;
  name: string;
  short_name?: string | null;
  institution_type: 'school' | 'college' | 'university';
  education_levels: EducationLevel[];
  city?: string | null;
  address?: string | null;
  email?: string | null;
  phone?: string | null;
}): Promise<School> {
  const { data } = await api.post<School>('/org/schools', payload);
  return data;
}

export async function fetchEducationOverview(
  level: EducationLevel,
  params?: { school_id?: string; academic_year?: string },
): Promise<EducationOverview> {
  const { data } = await api.get<EducationOverview>(
    `/education/${level}/overview`,
    {
      params: {
        school_id: params?.school_id || undefined,
        academic_year: params?.academic_year || undefined,
      },
    },
  );
  return data;
}

export async function fetchEducationGroups(
  level: EducationLevel,
  params?: { school_id?: string; academic_year?: string },
): Promise<EducationGroup[]> {
  const { data } = await api.get<EducationGroup[]>(
    `/education/${level}/groups`,
    {
      params: {
        school_id: params?.school_id || undefined,
        academic_year: params?.academic_year || undefined,
      },
    },
  );
  return data;
}

export async function fetchEducationPrograms(
  level: EducationLevel,
  schoolId?: string,
): Promise<EducationProgram[]> {
  const { data } = await api.get<EducationProgram[]>(
    `/education/${level}/programs`,
    { params: { school_id: schoolId || undefined } },
  );
  return data;
}

export async function createEducationProgram(
  level: EducationLevel,
  schoolId: string | undefined,
  payload: {
    code: string;
    name: string;
    qualification?: string | null;
    duration_years?: number | null;
    profile?: Record<string, unknown>;
    is_active?: boolean;
  },
): Promise<EducationProgram> {
  const { data } = await api.post<EducationProgram>(
    `/education/${level}/programs`,
    payload,
    { params: { school_id: schoolId || undefined } },
  );
  return data;
}

export async function updateEducationProgram(
  level: EducationLevel,
  schoolId: string | undefined,
  programId: string,
  payload: Partial<{
    code: string;
    name: string;
    qualification: string | null;
    duration_years: number | null;
    profile: Record<string, unknown>;
    is_active: boolean;
  }>,
): Promise<EducationProgram> {
  const { data } = await api.patch<EducationProgram>(
    `/education/${level}/programs/${programId}`,
    payload,
    { params: { school_id: schoolId || undefined } },
  );
  return data;
}

export async function fetchCurricula(
  level: EducationLevel,
  schoolId?: string,
  programId?: string,
  academicYear?: string,
): Promise<EducationCurriculum[]> {
  const { data } = await api.get<EducationCurriculum[]>(
    `/education/${level}/curricula`,
    {
      params: {
        school_id: schoolId || undefined,
        program_id: programId || undefined,
        academic_year: academicYear || undefined,
      },
    },
  );
  return data;
}

export async function createCurriculum(
  level: EducationLevel,
  schoolId: string | undefined,
  payload: {
    program_id: string;
    academic_year: string;
    name: string;
    description?: string | null;
    status?: CurriculumStatus;
    profile?: Record<string, unknown>;
  },
): Promise<EducationCurriculum> {
  const { data } = await api.post<EducationCurriculum>(
    `/education/${level}/curricula`,
    payload,
    { params: { school_id: schoolId || undefined } },
  );
  return data;
}

export async function updateCurriculum(
  level: EducationLevel,
  schoolId: string | undefined,
  curriculumId: string,
  payload: Partial<{
    name: string;
    description: string | null;
    status: CurriculumStatus;
    profile: Record<string, unknown>;
  }>,
): Promise<EducationCurriculum> {
  const { data } = await api.patch<EducationCurriculum>(
    `/education/${level}/curricula/${curriculumId}`,
    payload,
    { params: { school_id: schoolId || undefined } },
  );
  return data;
}

export async function createCurriculumComponent(
  level: EducationLevel,
  schoolId: string | undefined,
  curriculumId: string,
  payload: {
    code: string;
    name: string;
    component_type?: CurriculumComponentType;
    semester?: number;
    credits?: number;
    academic_hours?: number;
    contact_hours?: number;
    assessment_type?: AssessmentType;
    is_optional?: boolean;
    order_index?: number;
    description?: string | null;
    details?: Record<string, unknown>;
  },
): Promise<CurriculumComponent> {
  const { data } = await api.post<CurriculumComponent>(
    `/education/${level}/curricula/${curriculumId}/components`,
    payload,
    { params: { school_id: schoolId || undefined } },
  );
  return data;
}

export async function updateCurriculumComponent(
  level: EducationLevel,
  schoolId: string | undefined,
  curriculumId: string,
  componentId: string,
  payload: Partial<{
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
  }>,
): Promise<CurriculumComponent> {
  const { data } = await api.patch<CurriculumComponent>(
    `/education/${level}/curricula/${curriculumId}/components/${componentId}`,
    payload,
    { params: { school_id: schoolId || undefined } },
  );
  return data;
}

export async function deleteCurriculumComponent(
  level: EducationLevel,
  schoolId: string | undefined,
  curriculumId: string,
  componentId: string,
): Promise<void> {
  await api.delete(
    `/education/${level}/curricula/${curriculumId}/components/${componentId}`,
    { params: { school_id: schoolId || undefined } },
  );
}

export async function fetchAcademicSessions(
  level: EducationLevel,
  schoolId?: string,
  academicYear?: string,
  status?: SessionStatus,
): Promise<AcademicSession[]> {
  const { data } = await api.get<AcademicSession[]>(
    `/education/${level}/sessions`,
    {
      params: {
        school_id: schoolId || undefined,
        academic_year: academicYear || undefined,
        status: status || undefined,
      },
    },
  );
  return data;
}

export async function createAcademicSession(
  level: EducationLevel,
  schoolId: string | undefined,
  payload: {
    academic_year: string;
    semester: number;
    name: string;
    session_type?: SessionType;
    starts_on?: string | null;
    ends_on?: string | null;
    status?: SessionStatus;
    description?: string | null;
    profile?: Record<string, unknown>;
  },
): Promise<AcademicSession> {
  const { data } = await api.post<AcademicSession>(
    `/education/${level}/sessions`,
    payload,
    { params: { school_id: schoolId || undefined } },
  );
  return data;
}

export async function updateAcademicSession(
  level: EducationLevel,
  schoolId: string | undefined,
  sessionId: string,
  payload: Partial<{
    academic_year: string;
    semester: number;
    name: string;
    session_type: SessionType;
    starts_on: string | null;
    ends_on: string | null;
    status: SessionStatus;
    description: string | null;
    profile: Record<string, unknown>;
  }>,
): Promise<AcademicSession> {
  const { data } = await api.patch<AcademicSession>(
    `/education/${level}/sessions/${sessionId}`,
    payload,
    { params: { school_id: schoolId || undefined } },
  );
  return data;
}

export async function fetchSessionStatements(
  level: EducationLevel,
  schoolId: string | undefined,
  sessionId: string,
): Promise<SessionStatement[]> {
  const { data } = await api.get<SessionStatement[]>(
    `/education/${level}/sessions/${sessionId}/statements`,
    { params: { school_id: schoolId || undefined } },
  );
  return data;
}

export async function createSessionStatement(
  level: EducationLevel,
  schoolId: string | undefined,
  sessionId: string,
  payload: {
    group_id: string;
    component_id: string;
    teacher_id?: string | null;
    statement_number: string;
    issued_on?: string | null;
    notes?: string | null;
    profile?: Record<string, unknown>;
  },
): Promise<SessionStatement> {
  const { data } = await api.post<SessionStatement>(
    `/education/${level}/sessions/${sessionId}/statements`,
    payload,
    { params: { school_id: schoolId || undefined } },
  );
  return data;
}

export async function updateSessionStatement(
  level: EducationLevel,
  schoolId: string | undefined,
  statementId: string,
  payload: Partial<{
    teacher_id: string | null;
    statement_number: string;
    issued_on: string;
    status: SessionStatement['status'];
    notes: string | null;
    profile: Record<string, unknown>;
  }>,
): Promise<SessionStatement> {
  const { data } = await api.patch<SessionStatement>(
    `/education/${level}/statements/${statementId}`,
    payload,
    { params: { school_id: schoolId || undefined } },
  );
  return data;
}

export async function upsertStatementRecords(
  level: EducationLevel,
  schoolId: string | undefined,
  statementId: string,
  records: Array<{
    student_id: string;
    grade?: number | null;
    result?: StatementResult;
    credits_awarded?: number | null;
    comment?: string | null;
  }>,
): Promise<SessionStatement> {
  const { data } = await api.post<SessionStatement>(
    `/education/${level}/statements/${statementId}/records/bulk`,
    { records },
    { params: { school_id: schoolId || undefined } },
  );
  return data;
}

export async function fetchStudentTranscript(
  level: EducationLevel,
  schoolId: string | undefined,
  profileId: string,
  curriculumId?: string,
): Promise<Transcript> {
  const { data } = await api.get<Transcript>(
    `/education/${level}/students/${profileId}/transcript`,
    {
      params: {
        school_id: schoolId || undefined,
        curriculum_id: curriculumId || undefined,
      },
    },
  );
  return data;
}

export async function fetchCreditTransfers(
  level: EducationLevel,
  schoolId?: string,
  studentId?: string,
  status?: CreditTransferStatus,
): Promise<CreditTransfer[]> {
  const { data } = await api.get<CreditTransfer[]>(
    `/education/${level}/credit-transfers`,
    {
      params: {
        school_id: schoolId || undefined,
        student_id: studentId || undefined,
        status: status || undefined,
      },
    },
  );
  return data;
}

export async function createCreditTransfer(
  level: EducationLevel,
  schoolId: string | undefined,
  payload: {
    student_id: string;
    target_program_id?: string | null;
    target_component_id?: string | null;
    source_institution: string;
    source_program: string;
    source_component_code: string;
    source_component_name: string;
    source_academic_year: string;
    source_credits: number;
    awarded_credits?: number | null;
    source_grade?: number | null;
    document_number?: string | null;
    reason?: string | null;
    status?: CreditTransferStatus;
    profile?: Record<string, unknown>;
  },
): Promise<CreditTransfer> {
  const { data } = await api.post<CreditTransfer>(
    `/education/${level}/credit-transfers`,
    payload,
    { params: { school_id: schoolId || undefined } },
  );
  return data;
}

export async function updateCreditTransfer(
  level: EducationLevel,
  schoolId: string | undefined,
  transferId: string,
  payload: Partial<{
    target_program_id: string | null;
    target_component_id: string | null;
    awarded_credits: number;
    source_grade: number | null;
    document_number: string | null;
    reason: string | null;
    status: CreditTransferStatus;
    profile: Record<string, unknown>;
  }>,
): Promise<CreditTransfer> {
  const { data } = await api.patch<CreditTransfer>(
    `/education/${level}/credit-transfers/${transferId}`,
    payload,
    { params: { school_id: schoolId || undefined } },
  );
  return data;
}

export async function fetchCompetencies(
  level: EducationLevel,
  schoolId?: string,
  options?: {
    search?: string;
    competencyType?: CompetencyType;
    isActive?: boolean;
  },
): Promise<Competency[]> {
  const { data } = await api.get<Competency[]>(
    `/education/${level}/competencies`,
    {
      params: {
        school_id: schoolId || undefined,
        search: options?.search || undefined,
        competency_type: options?.competencyType || undefined,
        is_active:
          options?.isActive === undefined ? undefined : options.isActive,
      },
    },
  );
  return data;
}

export async function createCompetency(
  level: EducationLevel,
  schoolId: string | undefined,
  payload: {
    code: string;
    name: string;
    description?: string | null;
    competency_type?: CompetencyType;
    profile?: Record<string, unknown>;
    is_active?: boolean;
  },
): Promise<Competency> {
  const { data } = await api.post<Competency>(
    `/education/${level}/competencies`,
    payload,
    { params: { school_id: schoolId || undefined } },
  );
  return data;
}

export async function updateCompetency(
  level: EducationLevel,
  schoolId: string | undefined,
  competencyId: string,
  payload: Partial<{
    code: string;
    name: string;
    description: string | null;
    competency_type: CompetencyType;
    profile: Record<string, unknown>;
    is_active: boolean;
  }>,
): Promise<Competency> {
  const { data } = await api.patch<Competency>(
    `/education/${level}/competencies/${competencyId}`,
    payload,
    { params: { school_id: schoolId || undefined } },
  );
  return data;
}

export async function fetchProgramCompetencies(
  level: EducationLevel,
  schoolId: string | undefined,
  programId: string,
): Promise<ProgramCompetency[]> {
  const { data } = await api.get<ProgramCompetency[]>(
    `/education/${level}/programs/${programId}/competencies`,
    { params: { school_id: schoolId || undefined } },
  );
  return data;
}

export async function replaceProgramCompetencies(
  level: EducationLevel,
  schoolId: string | undefined,
  programId: string,
  items: Array<{
    competency_id: string;
    target_level?: number | null;
    weight?: number;
    profile?: Record<string, unknown>;
  }>,
): Promise<ProgramCompetency[]> {
  const { data } = await api.put<ProgramCompetency[]>(
    `/education/${level}/programs/${programId}/competencies`,
    { items },
    { params: { school_id: schoolId || undefined } },
  );
  return data;
}

export async function fetchCompetencyMatrix(
  level: EducationLevel,
  schoolId: string | undefined,
  curriculumId: string,
): Promise<CompetencyMatrix> {
  const { data } = await api.get<CompetencyMatrix>(
    `/education/${level}/curricula/${curriculumId}/competency-matrix`,
    { params: { school_id: schoolId || undefined } },
  );
  return data;
}

export async function replaceCompetencyMatrix(
  level: EducationLevel,
  schoolId: string | undefined,
  curriculumId: string,
  links: Array<{
    component_id: string;
    competency_id: string;
    weight?: number;
  }>,
): Promise<CompetencyMatrix> {
  const { data } = await api.put<CompetencyMatrix>(
    `/education/${level}/curricula/${curriculumId}/competency-matrix`,
    { links },
    { params: { school_id: schoolId || undefined } },
  );
  return data;
}

export async function fetchStudentProfiles(
  level: EducationLevel,
  schoolId?: string,
  academicStatus?: string,
): Promise<StudentAcademicProfile[]> {
  const { data } = await api.get<StudentAcademicProfile[]>(
    `/education/${level}/profiles`,
    {
      params: {
        school_id: schoolId || undefined,
        academic_status: academicStatus || undefined,
      },
    },
  );
  return data;
}

export async function createStudentProfile(
  level: EducationLevel,
  schoolId: string | undefined,
  payload: {
    user_id: string;
    program_id?: string | null;
    group_id?: string | null;
    course_year?: number | null;
    record_book_number?: string | null;
    funding_type?: 'budget' | 'paid' | 'target' | 'other';
    enrollment_year?: number | null;
    academic_status?: 'active' | 'academic_leave' | 'expelled' | 'graduated';
    profile?: Record<string, unknown>;
  },
): Promise<StudentAcademicProfile> {
  const { data } = await api.post<StudentAcademicProfile>(
    `/education/${level}/profiles`,
    payload,
    { params: { school_id: schoolId || undefined } },
  );
  return data;
}

export async function updateStudentProfile(
  level: EducationLevel,
  schoolId: string | undefined,
  profileId: string,
  payload: Partial<{
    program_id: string | null;
    group_id: string | null;
    course_year: number | null;
    record_book_number: string | null;
    funding_type: 'budget' | 'paid' | 'target' | 'other';
    enrollment_year: number | null;
    academic_status: 'active' | 'academic_leave' | 'expelled' | 'graduated';
    profile: Record<string, unknown>;
  }>,
): Promise<StudentAcademicProfile> {
  const { data } = await api.patch<StudentAcademicProfile>(
    `/education/${level}/profiles/${profileId}`,
    payload,
    { params: { school_id: schoolId || undefined } },
  );
  return data;
}

export async function fetchStaffProfiles(
  level: EducationLevel,
  schoolId?: string,
): Promise<StaffAcademicProfile[]> {
  const { data } = await api.get<StaffAcademicProfile[]>(
    `/education/${level}/staff-profiles`,
    { params: { school_id: schoolId || undefined } },
  );
  return data;
}

export async function createStaffProfile(
  level: EducationLevel,
  schoolId: string | undefined,
  payload: {
    user_id: string;
    department?: string | null;
    position?: string | null;
    academic_degree?: string | null;
    academic_title?: string | null;
    profile?: Record<string, unknown>;
  },
): Promise<StaffAcademicProfile> {
  const { data } = await api.post<StaffAcademicProfile>(
    `/education/${level}/staff-profiles`,
    payload,
    { params: { school_id: schoolId || undefined } },
  );
  return data;
}

export async function updateStaffProfile(
  level: EducationLevel,
  schoolId: string | undefined,
  profileId: string,
  payload: Partial<{
    department: string | null;
    position: string | null;
    academic_degree: string | null;
    academic_title: string | null;
    profile: Record<string, unknown>;
  }>,
): Promise<StaffAcademicProfile> {
  const { data } = await api.patch<StaffAcademicProfile>(
    `/education/${level}/staff-profiles/${profileId}`,
    payload,
    { params: { school_id: schoolId || undefined } },
  );
  return data;
}

export async function fetchUsers(schoolId: string): Promise<UserList> {
  const { data } = await api.get<UserList>('/admin/users', {
    params: { school_id: schoolId, limit: 200 },
  });
  return data;
}

export async function fetchStats(schoolId?: string): Promise<AdminStats> {
  const { data } = await api.get<AdminStats>('/admin/stats', {
    params: { school_id: schoolId || undefined },
  });
  return data;
}

export async function fetchAnalyticsOverview(params?: {
  school_id?: string;
  academic_year?: string;
}): Promise<AnalyticsOverview> {
  const { data } = await api.get<AnalyticsOverview>('/analytics/overview', {
    params: {
      school_id: params?.school_id || undefined,
      academic_year: params?.academic_year || undefined,
    },
  });
  return data;
}

export async function downloadAnalyticsReport(params?: {
  school_id?: string;
  academic_year?: string;
}): Promise<Blob> {
  const { data } = await api.get<Blob>('/analytics/export.csv', {
    params: {
      school_id: params?.school_id || undefined,
      academic_year: params?.academic_year || undefined,
    },
    responseType: 'blob',
  });
  return data;
}

export async function fetchEffectiveService(
  code: string,
): Promise<EffectiveService | undefined> {
  const data = await fetchMyServices();
  return data.items.find((item) => item.code === code);
}

export async function fetchOnboardingOverview(): Promise<OnboardingOverview> {
  const { data } = await api.get<OnboardingOverview>('/onboarding/me');
  return data;
}

export async function fetchOnboardingModule(
  moduleCode: string,
): Promise<OnboardingModule> {
  const { data } = await api.get<OnboardingModule>(
    `/onboarding/me/modules/${encodeURIComponent(moduleCode)}`,
  );
  return data;
}

export async function startOnboardingModule(
  moduleCode: string,
): Promise<OnboardingProgress> {
  const { data } = await api.post<OnboardingProgress>(
    `/onboarding/me/modules/${encodeURIComponent(moduleCode)}/start`,
  );
  return data;
}

export async function completeOnboardingStep(
  moduleCode: string,
  stepCode: string,
): Promise<OnboardingProgress> {
  const { data } = await api.post<OnboardingProgress>(
    `/onboarding/me/modules/${encodeURIComponent(moduleCode)}/steps/${encodeURIComponent(stepCode)}/complete`,
  );
  return data;
}

export async function fetchOnboardingReportUsers(params?: {
  school_id?: string;
  role?: string;
  status?: string;
  search?: string;
  limit?: number;
  offset?: number;
}): Promise<OnboardingReportUsers> {
  const { data } = await api.get<OnboardingReportUsers>('/onboarding/reports/users', {
    params: {
      school_id: params?.school_id || undefined,
      role: params?.role || undefined,
      status: params?.status || undefined,
      search: params?.search || undefined,
      limit: params?.limit ?? 50,
      offset: params?.offset ?? 0,
    },
  });
  return data;
}

export async function resetOnboardingUser(userId: string): Promise<void> {
  await api.post(`/onboarding/reports/users/${encodeURIComponent(userId)}/reset`);
}

export async function downloadOnboardingReport(params?: {
  school_id?: string;
  role?: string;
  status?: string;
  search?: string;
}): Promise<Blob> {
  const { data } = await api.get<Blob>('/onboarding/reports/export.csv', {
    params: {
      school_id: params?.school_id || undefined,
      role: params?.role || undefined,
      status: params?.status || undefined,
      search: params?.search || undefined,
    },
    responseType: 'blob',
  });
  return data;
}
