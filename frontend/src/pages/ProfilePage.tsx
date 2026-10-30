import { useMemo, useState, type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  BadgeCheck,
  Building2,
  CalendarDays,
  CheckCircle2,
  Clock,
  KeyRound,
  Layers,
  LogOut,
  Mail,
  Phone,
  RefreshCw,
  Shield,
  ShieldOff,
  Sparkles,
  Users,
} from 'lucide-react';

import { useAccess } from '../access/AccessContext';
import type { EffectivePermission, EffectiveService } from '../api/types';
import { useAuth } from '../auth/AuthContext';
import {
  Badge,
  Button,
  Card,
  EmptyState,
  PageHeader,
  Spinner,
} from '../components/ui';
import { cn } from '../lib/cn';
import {
  categoryColors,
  categoryLabels,
  formatDateTime,
  initials,
  pluralize,
  roleLabels,
  scopeColors,
  scopeLabels,
  serviceCategoryColors,
  serviceCategoryLabels,
} from '../lib/labels';

interface PermissionGroup {
  serviceCode: string;
  service: EffectiveService | undefined;
  items: EffectivePermission[];
}

export function ProfilePage() {
  const { user, logout } = useAuth();
  const { details, denied, groups, services, permissions, loading, reload } = useAccess();
  const navigate = useNavigate();
  const [refreshing, setRefreshing] = useState(false);

  const grouped = useMemo<PermissionGroup[]>(() => {
    const byService = new Map<string, EffectivePermission[]>();
    for (const detail of details) {
      const serviceCode = detail.code.split('.')[0] ?? 'other';
      const list = byService.get(serviceCode) ?? [];
      list.push(detail);
      byService.set(serviceCode, list);
    }
    return [...byService.entries()]
      .map(([serviceCode, items]) => ({
        serviceCode,
        service: services.find((service) => service.code === serviceCode),
        items: items.sort((a, b) => a.code.localeCompare(b.code)),
      }))
      .sort((a, b) => a.serviceCode.localeCompare(b.serviceCode));
  }, [details, services]);

  if (!user) return null;

  async function handleRefresh() {
    setRefreshing(true);
    try {
      await reload();
    } finally {
      setRefreshing(false);
    }
  }

  async function handleLogout() {
    await logout();
    navigate('/login', { replace: true });
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Аккаунт и доступ"
        title="Профиль и права"
        subtitle="Здесь видно, какие группы дают вам доступ и какие сервисы включены в вашем контуре."
        actions={
          <Button variant="outline" onClick={() => void handleRefresh()} loading={refreshing}>
            <RefreshCw className="h-4 w-4" />
            Обновить доступ
          </Button>
        }
      />

      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <Card className="overflow-hidden">
          <div className="relative bg-slate-950 p-6 text-white">
            <div
              className="pointer-events-none absolute inset-0 opacity-70"
              style={{
                backgroundImage:
                  'radial-gradient(circle at 15% 20%, rgba(99,102,241,0.45), transparent 38%), radial-gradient(circle at 85% 90%, rgba(16,185,129,0.3), transparent 38%)',
              }}
            />
            <div className="relative flex items-start gap-4">
              <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl bg-white/10 text-xl font-bold ring-1 ring-white/15 backdrop-blur-sm">
                {initials(user.full_name)}
              </div>
              <div className="min-w-0">
                <h2 className="truncate text-xl font-bold">{user.full_name}</h2>
                <p className="mt-0.5 text-sm text-slate-400">@{user.login}</p>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  <Badge className="border border-white/10 bg-white/10 text-accent-200 ring-white/10">
                    <Shield className="h-3 w-3" />
                    {roleLabels[user.role]}
                  </Badge>
                  {user.is_verified ? (
                    <Badge className="border border-white/10 bg-white/5 text-slate-300 ring-white/10">
                      <BadgeCheck className="h-3 w-3 text-accent-300" />
                      Подтверждён
                    </Badge>
                  ) : null}
                </div>
              </div>
            </div>
          </div>

          <div className="divide-y divide-slate-100">
            <InfoRow
              icon={<Mail className="h-4 w-4" />}
              label="Email"
              value={user.email ?? 'Не указан'}
            />
            <InfoRow
              icon={<Phone className="h-4 w-4" />}
              label="Телефон"
              value={user.phone ?? 'Не указан'}
            />
            <InfoRow
              icon={<Building2 className="h-4 w-4" />}
              label="Школа"
              value={
                user.school_id ? 'Закреплена за школой' : 'Республиканский уровень'
              }
            />
            <InfoRow
              icon={<CalendarDays className="h-4 w-4" />}
              label="Последний вход"
              value={formatDateTime(user.last_login_at)}
            />
            <InfoRow
              icon={<Clock className="h-4 w-4" />}
              label="Аккаунт создан"
              value={formatDateTime(user.created_at)}
            />
          </div>

          <div className="border-t border-slate-100 bg-slate-50/60 p-4">
            <div className="flex items-center justify-between gap-2">
              <div>
                <p className="text-xs font-semibold text-slate-700">Сессия</p>
                <p className="mt-0.5 text-[11px] text-slate-500">
                  JWT активен · {permissions.size}{' '}
                  {pluralize(permissions.size, 'право', 'права', 'прав')}
                </p>
              </div>
              <Button variant="danger" size="sm" onClick={() => void handleLogout()}>
                <LogOut className="h-3.5 w-3.5" />
                Выйти
              </Button>
            </div>
          </div>
        </Card>

        <div className="space-y-6">
          <Card className="p-5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <h2 className="flex items-center gap-2 text-sm font-bold text-slate-900">
                  <Users className="h-4 w-4 text-brand-500" />
                  Группы доступа
                </h2>
                <p className="mt-0.5 text-xs text-slate-500">
                  Членство в группах определяет ваши права
                </p>
              </div>
              <Badge className="bg-slate-100 text-slate-600 ring-slate-200">
                {groups.length}
              </Badge>
            </div>

            {loading ? (
              <div className="mt-4 flex items-center gap-2 text-xs text-slate-500">
                <Spinner className="h-4 w-4" />
                Загрузка групп…
              </div>
            ) : groups.length === 0 ? (
              <div className="mt-4">
                <EmptyState
                  title="Групп пока нет"
                  description="Права начисляются через группы. Обратитесь к администратору контура."
                  icon={<Users className="h-6 w-6" />}
                />
              </div>
            ) : (
              <div className="mt-4 space-y-2">
                {groups.map((group) => (
                  <div
                    key={group.id}
                    className="flex items-start gap-3 rounded-xl border border-slate-200 p-3"
                  >
                    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-xs font-bold text-slate-500">
                      {group.code.slice(0, 2).toUpperCase()}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-xs font-semibold text-slate-800">
                        {group.name}
                      </p>
                      <p className="truncate font-mono text-[10px] text-slate-400">
                        {group.code}
                      </p>
                      <div className="mt-1.5 flex flex-wrap gap-1.5">
                        <Badge className={scopeColors[group.scope_type]}>
                          <Layers className="h-2.5 w-2.5" />
                          {scopeLabels[group.scope_type]}
                        </Badge>
                        <Badge className={categoryColors[group.category]}>
                          {categoryLabels[group.category]}
                        </Badge>
                        <Badge className="bg-white text-slate-500 ring-slate-200">
                          {group.permissions_count}{' '}
                          {pluralize(group.permissions_count, 'право', 'права', 'прав')}
                        </Badge>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>

          <Card className="p-5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <h2 className="flex items-center gap-2 text-sm font-bold text-slate-900">
                  <KeyRound className="h-4 w-4 text-brand-500" />
                  Действующие права
                </h2>
                <p className="mt-0.5 text-xs text-slate-500">
                  С учётом наследования, приоритета и запретов
                </p>
              </div>
              <div className="flex items-center gap-1.5">
                <Badge className="bg-accent-50 text-accent-700 ring-accent-200">
                  {permissions.size} allow
                </Badge>
                {denied.length > 0 ? (
                  <Badge className="bg-rose-50 text-rose-700 ring-rose-200">
                    {denied.length} deny
                  </Badge>
                ) : null}
              </div>
            </div>

            {loading ? (
              <div className="mt-4 flex items-center gap-2 text-xs text-slate-500">
                <Spinner className="h-4 w-4" />
                Загрузка прав…
              </div>
            ) : grouped.length === 0 ? (
              <div className="mt-4">
                <EmptyState
                  title="Права не найдены"
                  description="Проверьте членство в группах или обновите доступ."
                  icon={<ShieldOff className="h-6 w-6" />}
                />
              </div>
            ) : (
              <div className="mt-4 space-y-4">
                {grouped.map((group) => (
                  <div key={group.serviceCode}>
                    <div className="flex items-center gap-2">
                      <span className="text-base">{group.service?.icon ?? '🔐'}</span>
                      <p className="text-xs font-bold text-slate-800">
                        {group.service?.name ?? group.serviceCode}
                      </p>
                      {group.service ? (
                        <Badge className={serviceCategoryColors[group.service.category]}>
                          {serviceCategoryLabels[group.service.category]}
                        </Badge>
                      ) : null}
                      <span className="ml-auto text-[10px] text-slate-400">
                        {group.items.length}
                      </span>
                    </div>
                    <div className="mt-2 grid gap-1.5 sm:grid-cols-2">
                      {group.items.map((item) => (
                        <div
                          key={`${item.code}-${item.group_id}`}
                          className={cn(
                            'flex items-start gap-2 rounded-xl border px-3 py-2',
                            item.allowed
                              ? 'border-slate-200 bg-white'
                              : 'border-rose-200 bg-rose-50/50',
                          )}
                        >
                          <span
                            className={cn(
                              'mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-lg',
                              item.allowed
                                ? 'bg-accent-50 text-accent-600'
                                : 'bg-rose-100 text-rose-600',
                            )}
                          >
                            {item.allowed ? (
                              <CheckCircle2 className="h-3.5 w-3.5" />
                            ) : (
                              <ShieldOff className="h-3.5 w-3.5" />
                            )}
                          </span>
                          <div className="min-w-0">
                            <p className="truncate font-mono text-[10px] font-semibold text-slate-700">
                              {item.code}
                            </p>
                            <p className="mt-0.5 truncate text-[10px] text-slate-400">
                              {item.group_name} · {scopeLabels[item.scope_type]} · depth{' '}
                              {item.depth}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>

          {denied.length > 0 ? (
            <Card className="border-rose-200 bg-rose-50/50 p-5">
              <div className="flex items-center gap-2">
                <ShieldOff className="h-4 w-4 text-rose-600" />
                <h2 className="text-sm font-bold text-rose-800">Явные запреты</h2>
              </div>
              <p className="mt-1 text-xs leading-5 text-rose-600">
                Эти права перекрыты более конкретной группой или deny-правилом.
              </p>
              <div className="mt-3 flex flex-wrap gap-1.5">
                {denied.map((code) => (
                  <span
                    key={code}
                    className="rounded-lg bg-white px-2 py-1 font-mono text-[10px] text-rose-700 ring-1 ring-rose-200"
                  >
                    {code}
                  </span>
                ))}
              </div>
            </Card>
          ) : null}

          <Card className="flex items-start gap-3 border-brand-100 bg-gradient-to-br from-brand-50 to-white p-5">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-600 text-white">
              <Sparkles className="h-5 w-5" />
            </span>
            <div>
              <p className="text-sm font-bold text-slate-900">Как выдаются права</p>
              <p className="mt-1 text-xs leading-5 text-slate-600">
                Администратор добавляет пользователя в группу. Группа получает права на
                своём уровне, и они наследуются вниз. На равной глубине запрет побеждает
                разрешение. Сервисы включаются отдельно и тоже наследуются.
              </p>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}

function InfoRow({
  icon,
  label,
  value,
}: {
  icon: ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center gap-3 px-5 py-3">
      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-slate-500">
        {icon}
      </span>
      <span className="flex-1 text-xs font-medium text-slate-500">{label}</span>
      <span className="max-w-[55%] truncate text-xs font-semibold text-slate-800">
        {value}
      </span>
    </div>
  );
}
