import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { startMfaEnrollment } from '../api/client';
import type { User } from '../api/types';
import { LoginPage } from './LoginPage';

const authState = vi.hoisted(() => ({
  login: vi.fn(),
  completeMfa: vi.fn(),
  completeMfaEnrollment: vi.fn(),
}));

vi.mock('../auth/AuthContext', () => ({
  useAuth: () => ({
    user: null,
    loading: false,
    login: authState.login,
    completeMfa: authState.completeMfa,
    completeMfaEnrollment: authState.completeMfaEnrollment,
    logout: vi.fn(),
    reloadUser: vi.fn(),
  }),
}));

vi.mock('../api/client', () => ({
  apiErrorMessage: (error: unknown) =>
    error instanceof Error ? error.message : String(error),
  startMfaEnrollment: vi.fn(),
}));

const baseUser: User = {
  id: 'user-1',
  school_id: null,
  login: 'admin',
  email: null,
  role: 'superadmin',
  first_name: 'Иван',
  last_name: 'Иванов',
  middle_name: null,
  full_name: 'Иванов Иван',
  phone: null,
  avatar: '👤',
  locale: 'ru',
  timezone: 'Europe/Minsk',
  is_active: true,
  is_verified: true,
  must_change_password: false,
  mfa_enabled: false,
  last_login_at: null,
  created_at: '2026-11-09T00:00:00+00:00',
};

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/login']}>
      <LoginPage />
    </MemoryRouter>,
  );
}

describe('LoginPage MFA', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(startMfaEnrollment).mockResolvedValue({
      secret: 'JBSWY3DPEHPK3PXP',
      otpauth_uri: 'otpauth://totp/VECTOR:admin?secret=JBSWY3DPEHPK3PXP',
      expires_in: 600,
    });
  });

  it('asks for a code when MFA is already enabled', async () => {
    authState.login.mockResolvedValue({
      status: 'mfa_required',
      mfa_token: 'challenge-token',
      expires_in: 300,
      user: { ...baseUser, mfa_enabled: true },
    });

    renderPage();
    fireEvent.change(screen.getByLabelText('Пароль'), {
      target: { value: 'secret' },
    });
    fireEvent.click(screen.getByRole('button', { name: /Войти/ }));

    expect(await screen.findByText('Подтвердите вход')).toBeTruthy();
    fireEvent.change(screen.getByLabelText('Код подтверждения'), {
      target: { value: '123456' },
    });
    fireEvent.click(screen.getByRole('button', { name: /Подтвердить/ }));

    await waitFor(() => {
      expect(authState.completeMfa).toHaveBeenCalledWith(
        'challenge-token',
        '123456',
      );
    });
  });

  it('shows the secret and recovery codes for first-time enrollment', async () => {
    authState.login.mockResolvedValue({
      status: 'mfa_enrollment_required',
      mfa_token: 'enroll-token',
      expires_in: 600,
      user: baseUser,
    });
    authState.completeMfaEnrollment.mockResolvedValue([
      'aaaa-bbbb-cccc-dddd',
      'eeee-ffff-0000-1111',
    ]);

    renderPage();
    fireEvent.change(screen.getByLabelText('Пароль'), {
      target: { value: 'secret' },
    });
    fireEvent.click(screen.getByRole('button', { name: /Войти/ }));

    expect(await screen.findByText('Защитите аккаунт')).toBeTruthy();
    expect(screen.getByText('JBSWY3DPEHPK3PXP')).toBeTruthy();
    fireEvent.change(screen.getByLabelText('Первый код MFA'), {
      target: { value: '123456' },
    });
    fireEvent.click(screen.getByRole('button', { name: /Включить MFA/ }));

    expect(await screen.findByText('Сохраните коды')).toBeTruthy();
    expect(screen.getByText('aaaa-bbbb-cccc-dddd')).toBeTruthy();
    expect(authState.completeMfaEnrollment).toHaveBeenCalledWith(
      'enroll-token',
      '123456',
    );
  });
});
