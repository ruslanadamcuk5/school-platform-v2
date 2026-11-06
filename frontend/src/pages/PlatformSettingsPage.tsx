import { useCallback, useEffect, useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  Database,
  PlugZap,
  RefreshCw,
  Save,
  ShieldCheck,
} from 'lucide-react';

import { useAccess } from '../access/AccessContext';
import {
  apiErrorMessage,
  fetchCacheSettings,
  testCacheSettings,
  updateCacheSettings,
} from '../api/client';
import type { CacheSettings, CacheStatus } from '../api/types';
import {
  Badge,
  Button,
  Card,
  ErrorAlert,
  PageHeader,
  Spinner,
  Toggle,
} from '../components/ui';
import { cn } from '../lib/cn';

interface CacheForm {
  enabled: boolean;
  ttlSeconds: string;
  keyPrefix: string;
  socketTimeoutSeconds: string;
  failureCooldownSeconds: string;
}

function formFromSettings(settings: CacheSettings): CacheForm {
  return {
    // Without REDIS_URL the cache cannot be effective; do not resend a stored
    // `enabled=true` and trigger a needless 409 in the API.
    enabled: settings.endpoint_configured ? settings.enabled : false,
    ttlSeconds: String(settings.ttl_seconds),
    keyPrefix: settings.key_prefix,
    socketTimeoutSeconds: String(settings.socket_timeout_seconds),
    failureCooldownSeconds: String(settings.failure_cooldown_seconds),
  };
}

const statusLabels: Record<CacheStatus, string> = {
  connected: 'Подключён',
  unavailable: 'Недоступен',
  disabled: 'Отключён',
};

const modeLabels: Record<CacheSettings['mode'], string> = {
  'managed-redis-tls': 'Managed Redis + TLS',
  redis: 'Redis',
  disabled: 'Отключён',
};

const statusTones: Record<CacheStatus, string> = {
  connected: 'bg-accent-50 text-accent-700 ring-accent-200',
  unavailable: 'bg-rose-50 text-rose-700 ring-rose-200',
  disabled: 'bg-slate-100 text-slate-600 ring-slate-200',
};

function formatUpdated(value: string | null): string {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('ru-RU');
}

export function PlatformSettingsPage() {
  const { can } = useAccess();
  const canWrite = can('system.settings.write');

  const [settings, setSettings] = useState<CacheSettings | null>(null);
  const [form, setForm] = useState<CacheForm | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchCacheSettings();
      setSettings(data);
      setForm(formFromSettings(data));
    } catch (caught) {
      setError(apiErrorMessage(caught));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!notice) return;
    const timeout = window.setTimeout(() => setNotice(null), 5000);
    return () => window.clearTimeout(timeout);
  }, [notice]);

  async function handleSave() {
    if (!form) return;
    const ttlSeconds = Number(form.ttlSeconds);
    const socketTimeoutSeconds = Number(form.socketTimeoutSeconds);
    const failureCooldownSeconds = Number(form.failureCooldownSeconds);
    if (
      !Number.isFinite(ttlSeconds) ||
      ttlSeconds < 5 ||
      ttlSeconds > 3600 ||
      !Number.isFinite(socketTimeoutSeconds) ||
      socketTimeoutSeconds < 0.1 ||
      socketTimeoutSeconds > 10 ||
      !Number.isFinite(failureCooldownSeconds) ||
      failureCooldownSeconds < 1 ||
      failureCooldownSeconds > 300 ||
      !form.keyPrefix.trim()
    ) {
      setError('Проверьте диапазоны: TTL 5–3600 с, таймаут 0,1–10 с, cooldown 1–300 с.');
      return;
    }

    setSaving(true);
    setError(null);
    try {
      const data = await updateCacheSettings({
        enabled: form.enabled,
        ttl_seconds: ttlSeconds,
        key_prefix: form.keyPrefix.trim(),
        socket_timeout_seconds: socketTimeoutSeconds,
        failure_cooldown_seconds: failureCooldownSeconds,
      });
      setSettings(data);
      setForm(formFromSettings(data));
      setNotice('Настройки кеша сохранены');
    } catch (caught) {
      setError(apiErrorMessage(caught));
    } finally {
      setSaving(false);
    }
  }

  async function handleTest() {
    setTesting(true);
    setError(null);
    try {
      const result = await testCacheSettings();
      setNotice(
        result.ok
          ? `${result.message}${result.latency_ms != null ? ` (${result.latency_ms} мс)` : ''}`
          : result.message,
      );
      await load();
    } catch (caught) {
      setError(apiErrorMessage(caught));
    } finally {
      setTesting(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center gap-2 py-24 text-sm text-slate-500">
        <Spinner />
        Загрузка настроек…
      </div>
    );
  }

  if (!settings || !form) {
    return (
      <div className="space-y-6">
        <PageHeader
          eyebrow="Администрирование"
          title="Эксплуатационные настройки"
          subtitle="Параметры кеша доступа и состояние подключения."
        />
        <ErrorAlert message={error ?? 'Не удалось загрузить настройки'} onRetry={() => void load()} />
      </div>
    );
  }

  const status = settings.status;
  const canEnable = settings.endpoint_configured;
  const readonlyFields = [
    {
      label: 'Endpoint',
      value: settings.endpoint_configured
        ? 'Настроен в REDIS_URL (значение скрыто)'
        : 'Не настроен',
    },
    {
      label: 'TLS',
      value: settings.tls_enabled ? 'Включён' : settings.endpoint_configured ? 'Не используется' : '—',
    },
    {
      label: 'Fail-open',
      value: settings.fail_open ? 'Включён (обязательно)' : 'Выключен',
    },
    {
      label: 'Инвалидация',
      value: settings.invalidation === 'version' ? 'Версионная' : settings.invalidation,
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Администрирование"
        title="Эксплуатационные настройки"
        subtitle="Кеш прав и активаций сервисов. PostgreSQL остаётся источником истины; сбой Redis не блокирует запросы."
        actions={
          <>
            <Button variant="outline" onClick={() => void load()} disabled={loading}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Обновить
            </Button>
            <Button variant="outline" onClick={() => void handleTest()} disabled={testing}>
              <PlugZap className={cn('mr-2 h-4 w-4', testing && 'animate-pulse')} />
              {testing ? 'Проверка…' : 'Проверить подключение'}
            </Button>
          </>
        }
      />

      {error ? <ErrorAlert message={error} onRetry={() => void load()} /> : null}
      {notice ? (
        <div className="flex items-start gap-3 rounded-2xl border border-accent-200 bg-accent-50 p-4 text-sm text-accent-800">
          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
          <p>{notice}</p>
        </div>
      ) : null}

      <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <Card className="p-5 sm:p-6">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="flex items-start gap-3">
              <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-brand-50 text-brand-600">
                <Database className="h-5 w-5" />
              </span>
              <div>
                <p className="text-sm font-bold text-slate-900">Кеш доступа</p>
                <p className="mt-0.5 text-xs text-slate-500">
                  TTL, префикс, таймауты и поведение при сбое.
                </p>
              </div>
            </div>
            <Badge className={statusTones[status]}>
              <span
                className={cn(
                  'h-1.5 w-1.5 rounded-full',
                  status === 'connected'
                    ? 'bg-accent-500'
                    : status === 'unavailable'
                      ? 'bg-rose-500'
                      : 'bg-slate-400',
                )}
              />
              {statusLabels[status]}
            </Badge>
          </div>

          <div className="mt-5 grid gap-3 sm:grid-cols-2">
            {readonlyFields.map((field) => (
              <div key={field.label} className="rounded-xl bg-slate-50 px-3 py-2.5 ring-1 ring-slate-100">
                <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                  {field.label}
                </p>
                <p className="mt-1 text-xs font-medium text-slate-700">{field.value}</p>
              </div>
            ))}
            <div className="rounded-xl bg-slate-50 px-3 py-2.5 ring-1 ring-slate-100">
              <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                Режим
              </p>
              <p className="mt-1 text-xs font-medium text-slate-700">{modeLabels[settings.mode]}</p>
            </div>
            <div className="rounded-xl bg-slate-50 px-3 py-2.5 ring-1 ring-slate-100">
              <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                Задержка
              </p>
              <p className="mt-1 text-xs font-medium text-slate-700">
                {settings.latency_ms != null ? `${settings.latency_ms} мс` : '—'}
              </p>
            </div>
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-1 text-[11px] text-slate-400">
            <span>Источник: {settings.source === 'database' ? 'runtime-настройки' : 'переменные окружения'}</span>
            <span>Обновлено: {formatUpdated(settings.updated_at)}</span>
            {settings.updated_by ? <span>Автор: {settings.updated_by}</span> : null}
          </div>

          <div className="mt-6 flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs leading-5 text-amber-800">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <p>
              Секрет <span className="font-mono">REDIS_URL</span> не хранится в БД и не передаётся в браузер.
              Для смены endpoint используйте серверный <span className="font-mono">.env</span> или секрет-хранилище;
              остальные параметры применяются без перезапуска.
            </p>
          </div>
        </Card>

        <Card className="p-5 sm:p-6">
          <div className="flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent-50 text-accent-600">
              <ShieldCheck className="h-5 w-5" />
            </span>
            <div>
              <p className="text-sm font-bold text-slate-900">Параметры</p>
              <p className="text-xs text-slate-500">Только несекретные значения</p>
            </div>
          </div>

          <div className="mt-6 space-y-5">
            <div className="flex items-center justify-between gap-4 rounded-xl border border-slate-200 p-3">
              <div>
                <p className="text-sm font-semibold text-slate-800">Кеш включён</p>
                <p className="mt-0.5 text-xs text-slate-500">
                  {canEnable
                    ? 'Отключение переводит запросы на PostgreSQL.'
                    : 'Сначала настройте REDIS_URL на сервере.'}
                </p>
              </div>
              <Toggle
                checked={form.enabled}
                onChange={(next) => setForm({ ...form, enabled: next })}
                disabled={!canWrite || !canEnable}
                label="Кеш включён"
              />
            </div>

            <Field
              label="TTL, секунды"
              hint="5–3600. Время жизни записи прав и активаций."
              value={form.ttlSeconds}
              onChange={(value) => setForm({ ...form, ttlSeconds: value })}
              type="number"
              min={5}
              max={3600}
              disabled={!canWrite}
            />
            <Field
              label="Префикс ключей"
              hint="Латиница, цифры, : _ . -; до 64 символов."
              value={form.keyPrefix}
              onChange={(value) => setForm({ ...form, keyPrefix: value })}
              disabled={!canWrite}
            />
            <div className="grid gap-4 sm:grid-cols-2">
              <Field
                label="Таймаут Redis, с"
                hint="0,1–10."
                value={form.socketTimeoutSeconds}
                onChange={(value) => setForm({ ...form, socketTimeoutSeconds: value })}
                type="number"
                min={0.1}
                max={10}
                step={0.1}
                disabled={!canWrite}
              />
              <Field
                label="Cooldown после сбоя, с"
                hint="1–300."
                value={form.failureCooldownSeconds}
                onChange={(value) => setForm({ ...form, failureCooldownSeconds: value })}
                type="number"
                min={1}
                max={300}
                step={1}
                disabled={!canWrite}
              />
            </div>
          </div>

          <div className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-4">
            <span className="text-[11px] text-slate-400">
              {canWrite ? 'Изменения фиксируются в аудите.' : 'Только просмотр: нет права system.settings.write.'}
            </span>
            <Button onClick={() => void handleSave()} disabled={!canWrite || saving}>
              <Save className="mr-2 h-4 w-4" />
              {saving ? 'Сохранение…' : 'Сохранить'}
            </Button>
          </div>
        </Card>
      </div>
    </div>
  );
}

function Field({
  label,
  hint,
  value,
  onChange,
  type = 'text',
  min,
  max,
  step,
  disabled,
}: {
  label: string;
  hint: string;
  value: string;
  onChange: (value: string) => void;
  type?: 'text' | 'number';
  min?: number;
  max?: number;
  step?: number;
  disabled?: boolean;
}) {
  return (
    <label className="block">
      <span className="text-xs font-semibold text-slate-700">{label}</span>
      <input
        type={type}
        value={value}
        min={min}
        max={max}
        step={step}
        disabled={disabled}
        aria-label={label}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1.5 h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-800 outline-none transition focus:border-brand-300 focus:ring-2 focus:ring-brand-100 disabled:bg-slate-50 disabled:text-slate-400"
      />
      <span className="mt-1 block text-[11px] text-slate-400">{hint}</span>
    </label>
  );
}
