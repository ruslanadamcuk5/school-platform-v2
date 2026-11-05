import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import {
  createSafetyAppeal,
  fetchMySafetyAppeals,
  fetchSafetyIncidents,
} from '../api/client';
import { SafetyPage } from './SafetyPage';

const accessState = vi.hoisted(() => ({
  permissions: new Set<string>(),
  services: [] as Array<{ code: string; enabled: boolean }>,
  role: 'admin',
  schoolId: 'school-1',
}));

vi.mock('../auth/AuthContext', () => ({
  useAuth: () => ({
    user: {
      id: 'user-1',
      role: accessState.role,
      school_id: accessState.schoolId,
      full_name: 'Администратор школы',
    },
  }),
}));

vi.mock('../access/AccessContext', () => ({
  useAccess: () => ({
    can: (code: string) => accessState.permissions.has(code),
    services: accessState.services,
    loading: false,
    error: null,
  }),
}));

vi.mock('../api/client', () => ({
  apiErrorMessage: (error: unknown) =>
    error instanceof Error ? error.message : String(error),
  fetchMySafetyAppeals: vi.fn().mockResolvedValue([]),
  fetchSafetyAppeals: vi.fn().mockResolvedValue([]),
  createSafetyAppeal: vi.fn().mockResolvedValue({
    id: 'appeal-1',
    is_anonymous: false,
  }),
  respondSafetyAppeal: vi.fn(),
  closeSafetyAppeal: vi.fn(),
  fetchSafetyIncidents: vi.fn().mockResolvedValue([]),
  createSafetyIncident: vi.fn(),
  resolveSafetyIncident: vi.fn(),
  fetchSafetyConsents: vi.fn().mockResolvedValue([]),
  createSafetyConsent: vi.fn(),
  revokeSafetyConsent: vi.fn(),
  fetchSafetyGeolocation: vi.fn().mockResolvedValue([]),
  createSafetyGeolocationPoint: vi.fn(),
  fetchSafetySettings: vi.fn().mockResolvedValue({
    retention_days: 365,
    incident_retention_days: 1095,
    consent_age_threshold: 16,
    allow_anonymous_appeals: true,
    geolocation_enabled: true,
  }),
  updateSafetySettings: vi.fn(),
  purgeSafetyData: vi.fn(),
  fetchSchools: vi.fn().mockResolvedValue([]),
  fetchUsers: vi.fn().mockResolvedValue({
    items: [],
    total: 0,
    limit: 200,
    offset: 0,
  }),
}));

function renderPage() {
  return render(
    <MemoryRouter>
      <SafetyPage />
    </MemoryRouter>,
  );
}

const allSafetyPermissions = new Set([
  'safety.support.use',
  'safety.incidents.read',
  'safety.incidents.manage',
  'safety.consents.manage',
  'safety.geolocation.read',
  'safety.settings.manage',
  'system.services.read',
]);

describe('SafetyPage', () => {
  beforeEach(() => {
    accessState.permissions = new Set(allSafetyPermissions);
    accessState.services = [{ code: 'safety', enabled: true }];
    accessState.role = 'admin';
    accessState.schoolId = 'school-1';
    vi.mocked(fetchMySafetyAppeals).mockResolvedValue([]);
    vi.mocked(fetchSafetyIncidents).mockResolvedValue([]);
    vi.mocked(createSafetyAppeal).mockResolvedValue({
      id: 'appeal-1',
      is_anonymous: false,
    } as never);
  });

  it('показывает состояние отключённого сервиса', () => {
    accessState.services = [{ code: 'safety', enabled: false }];

    renderPage();

    expect(screen.getByText('Сервис безопасности отключён')).toBeTruthy();
    expect(screen.queryByText('Мои обращения')).toBeNull();
  });

  it('показывает вкладки по правам и загружает инциденты', async () => {
    renderPage();

    expect(screen.getByText('Мои обращения')).toBeTruthy();
    expect(screen.getByText('Обращения школы')).toBeTruthy();
    expect(screen.getByText('Согласия')).toBeTruthy();
    expect(screen.getByText('Настройки')).toBeTruthy();

    fireEvent.click(screen.getByText('Инциденты'));

    expect(await screen.findByText('Инцидентов нет')).toBeTruthy();
    expect(fetchSafetyIncidents).toHaveBeenCalledWith('school-1', {
      status: undefined,
      severity: undefined,
    });
  });

  it('скрывает управленческие вкладки от ученика', async () => {
    accessState.role = 'student';
    accessState.permissions = new Set(['safety.support.use']);

    renderPage();

    await screen.findByText('Обращений пока нет');
    expect(screen.getByText('Мои обращения')).toBeTruthy();
    expect(screen.queryByText('Обращения школы')).toBeNull();
    expect(screen.queryByText('Инциденты')).toBeNull();
    expect(screen.queryByText('Согласия')).toBeNull();
    expect(screen.queryByText('Настройки')).toBeNull();
  });

  it('отправляет обращение с согласием', async () => {
    renderPage();

    await screen.findByText('Обращений пока нет');
    fireEvent.click(screen.getByText('Новое обращение'));
    fireEvent.change(screen.getByPlaceholderText('Кратко опишите ситуацию'), {
      target: { value: 'Тревожная ситуация' },
    });
    fireEvent.change(
      screen.getByPlaceholderText('Что произошло, когда и какая помощь нужна?'),
      { target: { value: 'Нужна помощь психолога' } },
    );
    fireEvent.click(screen.getByText('Отправить'));

    await waitFor(() => {
      expect(createSafetyAppeal).toHaveBeenCalledTimes(1);
    });
    expect(vi.mocked(createSafetyAppeal).mock.calls[0][0]).toMatchObject({
      school_id: 'school-1',
      subject: 'Тревожная ситуация',
      message: 'Нужна помощь психолога',
      is_anonymous: false,
      consent_required: true,
      consent_given: true,
    });
  });
});
