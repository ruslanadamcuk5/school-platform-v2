import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import {
  fetchCacheSettings,
  testCacheSettings,
  updateCacheSettings,
} from '../api/client';
import type { CacheSettings } from '../api/types';
import { PlatformSettingsPage } from './PlatformSettingsPage';

const accessState = vi.hoisted(() => ({
  permissions: new Set<string>(),
}));

vi.mock('../access/AccessContext', () => ({
  useAccess: () => ({
    can: (code: string) => accessState.permissions.has(code),
    services: [],
    loading: false,
    error: null,
  }),
}));

vi.mock('../api/client', () => ({
  apiErrorMessage: (error: unknown) =>
    error instanceof Error ? error.message : String(error),
  fetchCacheSettings: vi.fn(),
  updateCacheSettings: vi.fn(),
  testCacheSettings: vi.fn(),
}));

const baseSettings: CacheSettings = {
  enabled: true,
  effective_enabled: true,
  mode: 'managed-redis-tls',
  endpoint_configured: true,
  tls_enabled: true,
  ttl_seconds: 60,
  key_prefix: 'school-platform',
  socket_timeout_seconds: 1,
  failure_cooldown_seconds: 30,
  fail_open: true,
  invalidation: 'version',
  source: 'database',
  status: 'connected',
  latency_ms: 3.2,
  updated_at: '2026-11-06T06:00:00+00:00',
  updated_by: 'admin-id',
  requires_restart: false,
};

describe('PlatformSettingsPage', () => {
  beforeEach(() => {
    accessState.permissions = new Set([
      'system.settings.read',
      'system.settings.write',
    ]);
    vi.mocked(fetchCacheSettings).mockResolvedValue(baseSettings);
    vi.mocked(updateCacheSettings).mockResolvedValue({
      ...baseSettings,
      ttl_seconds: 120,
    });
    vi.mocked(testCacheSettings).mockResolvedValue({
      ok: true,
      status: 'connected',
      mode: 'managed-redis-tls',
      latency_ms: 4,
      message: 'Подключение к Redis установлено',
    });
  });

  it('renders masked endpoint and saves non-secret settings', async () => {
    render(<PlatformSettingsPage />);

    expect(await screen.findByText('Managed Redis + TLS')).toBeTruthy();
    expect(
      screen.getByText('Настроен в REDIS_URL (значение скрыто)'),
    ).toBeTruthy();
    expect(screen.getByText('Включён')).toBeTruthy();
    expect(screen.queryByText(/rediss:\/\//)).toBeNull();

    fireEvent.change(screen.getByLabelText('TTL, секунды'), {
      target: { value: '120' },
    });
    fireEvent.click(screen.getByRole('button', { name: /Сохранить/ }));

    await waitFor(() => {
      expect(updateCacheSettings).toHaveBeenCalledWith({
        enabled: true,
        ttl_seconds: 120,
        key_prefix: 'school-platform',
        socket_timeout_seconds: 1,
        failure_cooldown_seconds: 30,
      });
    });
  });

  it('checks the connection and shows the result', async () => {
    render(<PlatformSettingsPage />);

    await screen.findByText('Managed Redis + TLS');
    fireEvent.click(screen.getByRole('button', { name: /Проверить подключение/ }));

    expect(await screen.findByText(/Подключение к Redis установлено/)).toBeTruthy();
    expect(testCacheSettings).toHaveBeenCalled();
  });

  it('is read-only without system.settings.write', async () => {
    accessState.permissions = new Set(['system.settings.read']);
    render(<PlatformSettingsPage />);

    await screen.findByText('Managed Redis + TLS');
    expect(screen.getByText(/Только просмотр/)).toBeTruthy();
    const saveButton = screen.getByRole('button', {
      name: /Сохранить/,
    }) as HTMLButtonElement;
    expect(saveButton.disabled).toBe(true);
  });
});
