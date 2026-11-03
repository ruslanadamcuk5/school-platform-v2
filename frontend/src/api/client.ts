import axios, { AxiosError, type AxiosRequestConfig } from 'axios';

import type {
  AdminStats,
  AnalyticsOverview,
  City,
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
  Region,
  School,
  SchoolClass,
  Service,
  TokenPair,
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
