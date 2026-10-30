import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import {
  Activity,
  ArrowRight,
  Boxes,
  Building2,
  CheckCircle2,
  Database,
  GraduationCap,
  KeyRound,
  Layers,
  RefreshCw,
  Server,
  ShieldCheck,
  Sparkles,
  Users,
} from 'lucide-react';

import { useAccess } from '../access/AccessContext';
import {
  apiErrorMessage,
  fetchGroups,
  fetchSchools,
  fetchServices,
  fetchStats,
  healthRequest,
} from '../api/client';
import type { AdminStats, Health, School } from '../api/types';
import { useAuth } from '../auth/AuthContext';
import {
  Badge,
  Button,
  Card,
  ErrorAlert,
  PageHeader,
  Skeleton,
  StatCard,
} from '../components/ui';
import {
  categoryColors,
  categoryLabels,
  greeting,
  pluralize,
  roleLabels,
  scopeColors,
  scopeShortLabels,
  serviceCategoryColors,
  serviceCategoryLabels,
  serviceRoute,
  todayLabel,
} from '../lib/labels';
import { cn } from '../lib/cn';

const recentFeatures = [
  {
    version: '0.6',
    title: 'Групповые права и наследование',
    text: 'Права выдаются группам на уровне страны, области, города, школы и класса.',
  },
  {
    version: '0.6',
    title: 'Каталог из 14 сервисов',
    text: 'Каждый модуль можно включить или отключить на нужном уровне.',
  },
  {
    version: '0.6',
    title: 'Микросервисный запуск',
    text: 'Любой сервис поднимается отдельным процессом с собственным API.',
  },
  {
    version: '0.5',
    title: 'Единый API для всех клиентов',
    text: 'Web, Android и iOS работают с одним контрактом FastAPI.',
  },
];

export function DashboardPage() {
  const { user } = useAuth();
  const { services, groups: myGroups, permissions, can, loading: accessLoading } = useAccess();

  const [schools, setSchools] = useState<School[]>([]);
  const [schoolId, setSchoolId] = useState<string | undefined>(user?.school_id ?? undefined);
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [statsLoading, setStatsLoading] = useState(true);
  const [statsError, setStatsError] = useState<string | null>(null);
  const [groupsTotal, setGroupsTotal] = useState<number | null>(null);
  const [catalogTotal, setCatalogTotal] = useState<number | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function loadSchools() {
      try {
        const data = await fetchSchools();
        if (cancelled) return;
        setSchools(data);
        if (!schoolId && data.length > 0) {
          setSchoolId(data[0].id);
        }
      } catch {
        // Dashboard still works with aggregate data.
      }
    }
    void loadSchools();
    return () => {
      cancelled = true;
    };
  }, [schoolId]);

  useEffect(() => {
    let cancelled = false;

    async function loadStats() {
      if (!schoolId) {
        setStatsLoading(false);
        return;
      }
      setStatsLoading(true);
      setStatsError(null);
      try {
        const data = await fetchStats(schoolId);
        if (!cancelled) setStats(data);
      } catch (error) {
        if (!cancelled) setStatsError(apiErrorMessage(error));
      } finally {
        if (!cancelled) setStatsLoading(false);
      }
    }

    void loadStats();
    return () => {
      cancelled = true;
    };
  }, [schoolId]);

  useEffect(() => {
    let cancelled = false;

    async function loadExtras() {
      const [groupsResult, catalogResult, healthResult] = await Promise.allSettled([
        fetchGroups({ limit: 1 }),
        fetchServices(),
        healthRequest(),
      ]);
      if (cancelled) return;
      if (groupsResult.status === 'fulfilled') {
        setGroupsTotal(groupsResult.value.total);
      }
      if (catalogResult.status === 'fulfilled') {
        setCatalogTotal(catalogResult.value.total);
      }
      if (healthResult.status === 'fulfilled') {
        setHealth(healthResult.value);
      } else {
        setHealthError(apiErrorMessage(healthResult.reason));
      }
    }

    void loadExtras();
    return () => {
      cancelled = true;
    };
  }, []);

  const selectedSchool = useMemo(
    () => schools.find((school) => school.id === schoolId) ?? null,
    [schools, schoolId],
  );

  const enabledServices = services.filter((service) => service.enabled);
  const featureServices = enabledServices
    .filter((service) => !['iam', 'org', 'system', 'audit'].includes(service.code))
    .slice(0, 6);

  async function reloadHealth() {
    setHealthError(null);
    try {
      setHealth(await healthRequest());
    } catch (error) {
      setHealthError(apiErrorMessage(error));
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Республиканская платформа"
        title={`${greeting()}, ${user?.first_name ?? 'коллега'}!`}
        subtitle="Единое окно управления школой, правами и подключёнными сервисами."
        actions={
          <div className="flex items-center gap-2">
            <Badge className="bg-accent-50 text-accent-700 ring-accent-200">
              <span className="h-1.5 w-1.5 rounded-full bg-accent-500" />
              Пилот 0.7
            </Badge>
            <Badge className="bg-white text-slate-600 ring-slate-200">
              <Sparkles className="h-3 w-3 text-brand-500" />
              {todayLabel()}
            </Badge>
          </div>
        }
      />

      <Card className="relative overflow-hidden border-0 bg-slate-950 p-6 text-white shadow-card sm:p-8">
        <div
          className="pointer-events-none absolute inset-0 opacity-80"
          style={{
            backgroundImage:
              'radial-gradient(circle at 12% 20%, rgba(99,102,241,0.45), transparent 35%), radial-gradient(circle at 88% 85%, rgba(16,185,129,0.32), transparent 35%)',
          }}
        />
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.06]"
          style={{
            backgroundImage:
              'linear-gradient(rgba(255,255,255,.6) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.6) 1px, transparent 1px)',
            backgroundSize: '38px 38px',
          }}
        />
        <div className="relative flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-2xl">
            <div className="flex flex-wrap items-center gap-2">
              <Badge className="border border-white/10 bg-white/10 text-accent-200 ring-white/10">
                <ShieldCheck className="h-3 w-3" />
                {roleLabels[user?.role ?? 'student']}
              </Badge>
              {myGroups.length > 0 ? (
                <Badge className="border border-white/10 bg-white/5 text-slate-300 ring-white/10">
                  <Users className="h-3 w-3" />
                  {myGroups.length}{' '}
                  {pluralize(myGroups.length, 'группа', 'группы', 'групп')}
                </Badge>
              ) : null}
              <Badge className="border border-white/10 bg-white/5 text-slate-300 ring-white/10">
                <KeyRound className="h-3 w-3" />
                {permissions.size} прав
              </Badge>
            </div>
            <h2 className="mt-4 text-2xl font-bold tracking-tight sm:text-3xl">
              Всё управление — в одном контуре
            </h2>
            <p className="mt-2 max-w-xl text-sm leading-6 text-slate-400">
              Подключайте сервисы на уровне республики, школы или класса. Права
              наследуются, а доступ к данным остаётся изолированным.
            </p>
            <div className="mt-5 flex flex-wrap gap-2">
              {can('iam.groups.read') ? (
                <Link to="/groups">
                  <Button variant="secondary" size="sm">
                    <Users className="h-4 w-4" />
                    Группы и права
                  </Button>
                </Link>
              ) : null}
              {can('system.services.read') ? (
                <Link to="/services">
                  <Button
                    variant="outline"
                    size="sm"
                    className="border-white/15 bg-white/5 text-white hover:bg-white/10 hover:text-white"
                  >
                    <Boxes className="h-4 w-4" />
                    Сервисы
                  </Button>
                </Link>
              ) : null}
            </div>
          </div>

          <div className="w-full max-w-sm rounded-2xl border border-white/10 bg-white/[0.06] p-4 backdrop-blur-sm">
            <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-slate-400">
              Текущий контур
            </p>
            {user?.role === 'superadmin' && schools.length > 0 ? (
              <select
                value={schoolId ?? ''}
                onChange={(event) => setSchoolId(event.target.value)}
                className="mt-2 h-10 w-full rounded-xl border border-white/10 bg-slate-900/70 px-3 text-sm text-white outline-none focus:border-accent-400"
              >
                {schools.map((school) => (
                  <option key={school.id} value={school.id}>
                    {school.name}
                  </option>
                ))}
              </select>
            ) : (
              <p className="mt-2 flex items-center gap-2 text-sm font-semibold text-white">
                <Building2 className="h-4 w-4 text-accent-300" />
                {selectedSchool?.name ?? 'Школа не выбрана'}
              </p>
            )}
            <div className="mt-3 grid grid-cols-2 gap-2 text-[11px]">
              <div className="rounded-xl bg-white/5 px-3 py-2">
                <p className="text-slate-500">Классов</p>
                <p className="mt-0.5 text-base font-bold text-white">
                  {stats?.classes_total ?? '—'}
                </p>
              </div>
              <div className="rounded-xl bg-white/5 px-3 py-2">
                <p className="text-slate-500">Пользователей</p>
                <p className="mt-0.5 text-base font-bold text-white">
                  {stats?.users_total ?? '—'}
                </p>
              </div>
            </div>
            <p className="mt-3 text-[10px] leading-4 text-slate-500">
              {selectedSchool?.city ?? 'Республика Беларусь'} ·{' '}
              {selectedSchool?.code ?? 'пилотный контур'}
            </p>
          </div>
        </div>
      </Card>

      {statsError ? <ErrorAlert message={statsError} /> : null}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {statsLoading ? (
          Array.from({ length: 4 }).map((_, index) => (
            <Card key={index} className="p-5">
              <Skeleton className="h-3 w-24" />
              <Skeleton className="mt-3 h-8 w-16" />
              <Skeleton className="mt-2 h-3 w-32" />
            </Card>
          ))
        ) : (
          <>
            <StatCard
              label="Пользователи"
              value={stats?.users_total ?? 0}
              hint={`${stats?.users_active ?? 0} активных`}
              icon={<Users className="h-5 w-5" />}
              accent="brand"
            />
            <StatCard
              label="Классы"
              value={stats?.classes_total ?? 0}
              hint={`${stats?.classes_active ?? 0} активных`}
              icon={<GraduationCap className="h-5 w-5" />}
              accent="accent"
            />
            <StatCard
              label="Группы доступа"
              value={groupsTotal ?? myGroups.length}
              hint="на всех уровнях иерархии"
              icon={<Layers className="h-5 w-5" />}
              accent="amber"
            />
            <StatCard
              label="Сервисы"
              value={`${enabledServices.length}/${catalogTotal ?? (services.length || 14)}`}
              hint="включено в контуре"
              icon={<Boxes className="h-5 w-5" />}
              accent="sky"
            />
          </>
        )}
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.35fr_0.65fr]">
        <Card className="overflow-hidden">
          <div className="flex items-center justify-between gap-3 border-b border-slate-100 px-5 py-4">
            <div>
              <h2 className="text-sm font-bold text-slate-900">Подключённые сервисы</h2>
              <p className="mt-0.5 text-xs text-slate-500">
                Формируются из ваших прав и активаций
              </p>
            </div>
            <Link
              to="/services"
              className="inline-flex items-center gap-1 text-xs font-semibold text-brand-600 hover:text-brand-700"
            >
              Все сервисы <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>

          <div className="grid gap-3 p-5 sm:grid-cols-2">
            {accessLoading ? (
              Array.from({ length: 4 }).map((_, index) => (
                <Skeleton key={index} className="h-24 w-full" />
              ))
            ) : featureServices.length === 0 ? (
              <div className="col-span-full rounded-2xl bg-slate-50 p-6 text-center text-sm text-slate-500">
                Нет доступных сервисов. Обратитесь к администратору контура.
              </div>
            ) : (
              featureServices.map((service) => (
                <Link
                  key={service.code}
                  to={serviceRoute(service.code)}
                  className="group flex items-start gap-3 rounded-2xl border border-slate-200 p-3.5 transition hover:border-brand-200 hover:bg-brand-50/40"
                >
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-lg">
                    {service.icon}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <p className="truncate text-sm font-semibold text-slate-800 group-hover:text-brand-700">
                        {service.name}
                      </p>
                      {service.status === 'beta' ? (
                        <Badge className="bg-amber-50 text-amber-700 ring-amber-200">
                          β
                        </Badge>
                      ) : null}
                    </div>
                    <p className="mt-1 line-clamp-2 text-xs leading-5 text-slate-500">
                      {service.description ?? 'Сервис платформы'}
                    </p>
                    <div className="mt-2 flex items-center gap-2">
                      <Badge className={serviceCategoryColors[service.category]}>
                        {serviceCategoryLabels[service.category]}
                      </Badge>
                      <span className="text-[10px] text-slate-400">
                        {service.permission_codes.length} прав
                      </span>
                    </div>
                  </div>
                  <ArrowRight className="mt-1 h-4 w-4 shrink-0 text-slate-300 transition group-hover:text-brand-500" />
                </Link>
              ))
            )}
          </div>
        </Card>

        <div className="space-y-6">
          <Card className="p-5">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-bold text-slate-900">Состояние платформы</h2>
                <p className="mt-0.5 text-xs text-slate-500">Проверка API и БД</p>
              </div>
              <button
                type="button"
                onClick={() => void reloadHealth()}
                className="rounded-lg p-2 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
                aria-label="Обновить статус"
              >
                <RefreshCw className="h-4 w-4" />
              </button>
            </div>

            {healthError ? (
              <div className="mt-4 rounded-xl border border-rose-200 bg-rose-50 p-3 text-xs text-rose-700">
                {healthError}
              </div>
            ) : (
              <div className="mt-4 space-y-2.5">
                <StatusRow
                  icon={<Server className="h-4 w-4" />}
                  label="API"
                  value={health ? health.status : 'проверка…'}
                  ok={health?.status === 'ok'}
                />
                <StatusRow
                  icon={<Database className="h-4 w-4" />}
                  label="PostgreSQL"
                  value={health ? health.database : 'проверка…'}
                  ok={health?.database === 'ok'}
                />
                <StatusRow
                  icon={<KeyRound className="h-4 w-4" />}
                  label="JWT"
                  value={health?.jwt_ready ? 'готов' : 'проверка…'}
                  ok={Boolean(health?.jwt_ready)}
                />
                <StatusRow
                  icon={<Activity className="h-4 w-4" />}
                  label="Среда"
                  value={health?.environment ?? '—'}
                  ok={Boolean(health)}
                />
              </div>
            )}

            <div className="mt-4 flex items-center justify-between rounded-xl bg-slate-50 px-3 py-2 text-[11px] text-slate-500">
              <span>Версия API</span>
              <span className="font-semibold text-slate-700">
                {health?.version ?? '—'}
              </span>
            </div>
          </Card>

          <Card className="p-5">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-brand-500" />
              <h2 className="text-sm font-bold text-slate-900">Что нового</h2>
            </div>
            <div className="mt-4 space-y-4">
              {recentFeatures.map((feature) => (
                <div key={feature.title} className="flex gap-3">
                  <div className="mt-1 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-accent-50 text-accent-600">
                    <CheckCircle2 className="h-3.5 w-3.5" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <p className="text-xs font-semibold text-slate-800">
                        {feature.title}
                      </p>
                      <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[9px] font-bold text-slate-500">
                        v{feature.version}
                      </span>
                    </div>
                    <p className="mt-0.5 text-[11px] leading-5 text-slate-500">
                      {feature.text}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>

      <Card className="p-5">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-sm font-bold text-slate-900">Сводка по ролям</h2>
            <p className="mt-0.5 text-xs text-slate-500">
              Пользователи выбранной школы по ролям
            </p>
          </div>
          <Badge className="bg-white text-slate-600 ring-slate-200">
            <Building2 className="h-3 w-3" />
            {selectedSchool?.short_name ?? selectedSchool?.name ?? 'Школа'}
          </Badge>
        </div>
        <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          {stats && Object.keys(stats.by_role).length > 0 ? (
            Object.entries(stats.by_role).map(([role, count]) => (
              <div
                key={role}
                className="flex items-center justify-between rounded-xl border border-slate-200 px-3 py-2.5"
              >
                <span className="text-xs font-medium text-slate-600">
                  {roleLabels[role as keyof typeof roleLabels] ?? role}
                </span>
                <span className="text-sm font-bold text-slate-900">{count}</span>
              </div>
            ))
          ) : (
            <p className="col-span-full rounded-xl bg-slate-50 px-4 py-6 text-center text-xs text-slate-500">
              {stats?.users_total === 0
                ? 'В выбранной школе пока нет пользователей.'
                : 'Данные появятся после загрузки школы.'}
            </p>
          )}
        </div>
      </Card>

      {myGroups.length > 0 ? (
        <Card className="p-5">
          <h2 className="text-sm font-bold text-slate-900">Мои группы доступа</h2>
          <p className="mt-0.5 text-xs text-slate-500">
            Через них наследуются ваши права
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            {myGroups.map((group) => (
              <div
                key={group.id}
                className="flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-2"
              >
                <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-slate-100 text-xs">
                  {group.code.slice(0, 1).toUpperCase()}
                </span>
                <div>
                  <p className="text-xs font-semibold text-slate-800">{group.name}</p>
                  <div className="mt-0.5 flex items-center gap-1.5">
                    <span
                      className={cn(
                        'rounded px-1.5 py-0.5 text-[9px] font-bold ring-1 ring-inset',
                        scopeColors[group.scope_type],
                      )}
                    >
                      {scopeShortLabels[group.scope_type]}
                    </span>
                    <span
                      className={cn(
                        'rounded px-1.5 py-0.5 text-[9px] font-bold ring-1 ring-inset',
                        categoryColors[group.category],
                      )}
                    >
                      {categoryLabels[group.category]}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      ) : null}
    </div>
  );
}

function StatusRow({
  icon,
  label,
  value,
  ok,
}: {
  icon: ReactNode;
  label: string;
  value: string;
  ok: boolean;
}) {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-slate-200 px-3 py-2.5">
      <span
        className={cn(
          'flex h-8 w-8 items-center justify-center rounded-lg',
          ok ? 'bg-accent-50 text-accent-600' : 'bg-slate-100 text-slate-400',
        )}
      >
        {icon}
      </span>
      <span className="flex-1 text-xs font-medium text-slate-600">{label}</span>
      <span
        className={cn(
          'inline-flex items-center gap-1.5 text-[11px] font-semibold',
          ok ? 'text-accent-700' : 'text-slate-500',
        )}
      >
        <span
          className={cn(
            'h-1.5 w-1.5 rounded-full',
            ok ? 'bg-accent-500' : 'bg-slate-300',
          )}
        />
        {value === 'ok' ? 'работает' : value}
      </span>
    </div>
  );
}
