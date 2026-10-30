import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import {
  Boxes,
  Building2,
  CheckCircle2,
  CircleOff,
  Globe2,
  Info,
  Layers,
  Lock,
  RefreshCw,
  Search,
  Settings2,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';

import { useAccess } from '../access/AccessContext';
import {
  apiErrorMessage,
  fetchEffectiveServices,
  fetchSchools,
  fetchServices,
  setServiceActivation,
} from '../api/client';
import type {
  EffectiveService,
  School,
  Service,
  Service as ServiceType,
} from '../api/types';
import { useAuth } from '../auth/AuthContext';
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorAlert,
  PageHeader,
  Skeleton,
  Toggle,
} from '../components/ui';
import { cn } from '../lib/cn';
import {
  scopeLabels,
  serviceCategoryColors,
  serviceCategoryLabels,
  serviceRoute,
} from '../lib/labels';

type ScopeMode = 'country' | 'school';

interface MergedService extends EffectiveService {
  version: string;
  default_enabled: boolean;
  is_core: boolean;
  manifest: Service['manifest'];
}

const categories: ServiceType['category'][] = [
  'core',
  'education',
  'management',
  'communication',
  'analytics',
  'ai',
  'security',
];

export function ServicesPage() {
  const { user } = useAuth();
  const { reload: reloadAccess, can } = useAccess();
  const canWrite = can('system.services.write');

  const [catalog, setCatalog] = useState<Service[]>([]);
  const [effective, setEffective] = useState<EffectiveService[]>([]);
  const [schools, setSchools] = useState<School[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<'all' | ServiceType['category']>('all');
  const [scopeMode, setScopeMode] = useState<ScopeMode>(
    user?.role === 'superadmin' ? 'country' : 'school',
  );
  const [scopeId, setScopeId] = useState<string>(user?.school_id ?? '');
  const [savingCode, setSavingCode] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    if (!notice) return;
    const timeout = window.setTimeout(() => setNotice(null), 4000);
    return () => window.clearTimeout(timeout);
  }, [notice]);

  useEffect(() => {
    let cancelled = false;
    async function loadCatalog() {
      try {
        const [catalogData, schoolsData] = await Promise.all([
          fetchServices(),
          fetchSchools(),
        ]);
        if (cancelled) return;
        setCatalog(catalogData.items);
        setSchools(schoolsData);
        if (!scopeId && schoolsData.length > 0) {
          setScopeId(schoolsData[0].id);
        }
      } catch (caught) {
        if (!cancelled) setError(apiErrorMessage(caught));
      }
    }
    void loadCatalog();
    return () => {
      cancelled = true;
    };
    // scopeId intentionally read only on first load.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadEffective = useCallback(async () => {
    if (scopeMode === 'school' && !scopeId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await fetchEffectiveServices(
        scopeMode,
        scopeMode === 'school' ? scopeId : undefined,
      );
      setEffective(data.items);
    } catch (caught) {
      setError(apiErrorMessage(caught));
    } finally {
      setLoading(false);
    }
  }, [scopeMode, scopeId]);

  useEffect(() => {
    void loadEffective();
  }, [loadEffective]);

  const merged = useMemo<MergedService[]>(() => {
    const byCode = new Map(catalog.map((service) => [service.code, service]));
    return effective.map((service) => {
      const catalogService = byCode.get(service.code);
      return {
        ...service,
        version: catalogService?.version ?? '0.0.0',
        default_enabled: catalogService?.default_enabled ?? false,
        is_core: catalogService?.is_core ?? false,
        manifest: catalogService?.manifest ?? {},
      };
    });
  }, [catalog, effective]);

  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase();
    return merged.filter((service) => {
      if (categoryFilter !== 'all' && service.category !== categoryFilter) return false;
      if (!query) return true;
      return (
        service.name.toLowerCase().includes(query) ||
        service.code.toLowerCase().includes(query) ||
        (service.description ?? '').toLowerCase().includes(query)
      );
    });
  }, [merged, search, categoryFilter]);

  const enabledCount = merged.filter((service) => service.enabled).length;
  const coreCount = merged.filter((service) => service.is_core).length;
  const selectedSchool = schools.find((school) => school.id === scopeId) ?? null;
  const scopeLabel =
    scopeMode === 'country' ? 'Республика' : selectedSchool?.name ?? 'Школа';

  async function handleToggle(service: MergedService, next: boolean) {
    if (service.is_core) return;
    setSavingCode(service.code);
    setError(null);
    try {
      await setServiceActivation(
        service.code,
        next,
        scopeMode,
        scopeMode === 'school' ? scopeId : undefined,
      );
      setNotice(
        `Сервис «${service.name}» ${next ? 'включён' : 'отключён'} на уровне «${scopeLabel}».`,
      );
      await loadEffective();
      await reloadAccess();
    } catch (caught) {
      setError(apiErrorMessage(caught));
    } finally {
      setSavingCode(null);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Каталог платформы"
        title="Сервисы"
        subtitle="Каждый модуль можно включить или отключить. Настройка на уровне школы перекрывает республиканскую, а ядро платформы отключить нельзя."
        actions={
          <Button variant="outline" onClick={() => void loadEffective()}>
            <RefreshCw className="h-4 w-4" />
            Обновить
          </Button>
        }
      />

      {notice ? (
        <div className="flex items-center gap-2 rounded-2xl border border-accent-200 bg-accent-50 px-4 py-3 text-sm text-accent-800">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          {notice}
        </div>
      ) : null}

      {error ? <ErrorAlert message={error} onRetry={() => void loadEffective()} /> : null}

      <Card className="p-4 sm:p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex flex-wrap items-center gap-2">
            <div className="inline-flex rounded-xl border border-slate-200 bg-slate-50 p-1">
              <button
                type="button"
                onClick={() => setScopeMode('country')}
                disabled={user?.role !== 'superadmin'}
                className={cn(
                  'inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition disabled:cursor-not-allowed disabled:opacity-50',
                  scopeMode === 'country'
                    ? 'bg-white text-brand-700 shadow-sm ring-1 ring-slate-200'
                    : 'text-slate-500 hover:text-slate-700',
                )}
              >
                <Globe2 className="h-3.5 w-3.5" />
                Республика
              </button>
              <button
                type="button"
                onClick={() => setScopeMode('school')}
                className={cn(
                  'inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition',
                  scopeMode === 'school'
                    ? 'bg-white text-brand-700 shadow-sm ring-1 ring-slate-200'
                    : 'text-slate-500 hover:text-slate-700',
                )}
              >
                <Building2 className="h-3.5 w-3.5" />
                Школа
              </button>
            </div>

            {scopeMode === 'school' ? (
              <select
                value={scopeId}
                onChange={(event) => setScopeId(event.target.value)}
                className="h-9 max-w-xs rounded-xl border border-slate-200 bg-white px-3 text-xs font-semibold text-slate-700 outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              >
                {schools.map((school) => (
                  <option key={school.id} value={school.id}>
                    {school.name}
                  </option>
                ))}
              </select>
            ) : (
              <Badge className="bg-indigo-50 text-indigo-700 ring-indigo-200">
                <Globe2 className="h-3 w-3" />
                Все школы республики
              </Badge>
            )}
          </div>

          <div className="flex items-center gap-2 text-[11px] text-slate-500">
            <ShieldCheck className="h-3.5 w-3.5 text-accent-600" />
            {canWrite
              ? 'Изменения применяются сразу и фиксируются в аудите'
              : 'Только просмотр: нет права system.services.write'}
          </div>
        </div>

        <div className="mt-4 flex flex-col gap-3 border-t border-slate-100 pt-4 lg:flex-row lg:items-center">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Найти сервис по названию или коду…"
              className="h-10 w-full rounded-xl border border-slate-200 bg-slate-50 pl-9 pr-3 text-sm outline-none transition placeholder:text-slate-400 focus:border-brand-300 focus:bg-white focus:ring-2 focus:ring-brand-100"
            />
          </div>
          <div className="flex flex-wrap gap-1.5">
            <FilterChip
              active={categoryFilter === 'all'}
              onClick={() => setCategoryFilter('all')}
            >
              Все
            </FilterChip>
            {categories.map((category) => (
              <FilterChip
                key={category}
                active={categoryFilter === category}
                onClick={() => setCategoryFilter(category)}
              >
                {serviceCategoryLabels[category]}
              </FilterChip>
            ))}
          </div>
        </div>
      </Card>

      <div className="grid gap-4 sm:grid-cols-3">
        <SummaryCard
          label="Доступно сервисов"
          value={`${enabledCount}/${merged.length}`}
          hint={`на уровне «${scopeLabel}»`}
          icon={<Boxes className="h-5 w-5" />}
          tone="brand"
        />
        <SummaryCard
          label="Ядро платформы"
          value={coreCount}
          hint="всегда включено"
          icon={<Lock className="h-5 w-5" />}
          tone="accent"
        />
        <SummaryCard
          label="Отключено"
          value={Math.max(merged.length - enabledCount, 0)}
          hint="доступно для включения"
          icon={<CircleOff className="h-5 w-5" />}
          tone="amber"
        />
      </div>

      {loading ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }).map((_, index) => (
            <Skeleton key={index} className="h-56 w-full" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <Card>
          <EmptyState
            title="Сервисы не найдены"
            description="Измените поисковый запрос или категорию."
            icon={<Search className="h-6 w-6" />}
          />
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {filtered.map((service) => (
            <Card
              key={service.code}
              className={cn(
                'relative flex flex-col p-5 transition',
                service.enabled
                  ? 'border-slate-200'
                  : 'border-dashed border-slate-300 bg-slate-50/60',
              )}
            >
              <div className="flex items-start gap-3">
                <div
                  className={cn(
                    'flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl text-2xl',
                    service.enabled ? 'bg-slate-100' : 'bg-white ring-1 ring-slate-200',
                  )}
                >
                  {service.icon}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <h3 className="truncate text-sm font-bold text-slate-900">
                      {service.name}
                    </h3>
                    {service.is_core ? (
                      <Badge className="bg-slate-900 text-white ring-slate-900">
                        <Lock className="h-2.5 w-2.5" />
                        ядро
                      </Badge>
                    ) : service.status === 'beta' ? (
                      <Badge className="bg-amber-50 text-amber-700 ring-amber-200">
                        beta
                      </Badge>
                    ) : null}
                  </div>
                  <p className="mt-0.5 font-mono text-[10px] text-slate-400">
                    {service.code} · v{service.version}
                  </p>
                </div>
                <Toggle
                  checked={service.enabled}
                  onChange={(next) => void handleToggle(service, next)}
                  disabled={!canWrite || service.is_core || savingCode === service.code}
                  label={`${service.enabled ? 'Отключить' : 'Включить'} ${service.name}`}
                />
              </div>

              <p className="mt-3 line-clamp-2 min-h-10 text-xs leading-5 text-slate-500">
                {service.description ?? 'Сервис платформы'}
              </p>

              <div className="mt-3 flex flex-wrap items-center gap-1.5">
                <Badge className={serviceCategoryColors[service.category]}>
                  {serviceCategoryLabels[service.category]}
                </Badge>
                <Badge
                  className={
                    service.enabled
                      ? 'bg-accent-50 text-accent-700 ring-accent-200'
                      : 'bg-slate-100 text-slate-500 ring-slate-200'
                  }
                >
                  <span
                    className={cn(
                      'h-1.5 w-1.5 rounded-full',
                      service.enabled ? 'bg-accent-500' : 'bg-slate-400',
                    )}
                  />
                  {service.enabled ? 'включён' : 'отключён'}
                </Badge>
                <Badge className="bg-white text-slate-500 ring-slate-200">
                  {sourceLabel(service.source)}
                </Badge>
              </div>

              {service.manifest.depends_on?.length ? (
                <div className="mt-3 rounded-xl bg-slate-50 px-3 py-2">
                  <p className="text-[10px] font-semibold text-slate-500">
                    Зависимости
                  </p>
                  <div className="mt-1 flex flex-wrap gap-1">
                    {service.manifest.depends_on.map((dependency) => (
                      <span
                        key={dependency}
                        className="rounded bg-white px-1.5 py-0.5 font-mono text-[9px] text-slate-500 ring-1 ring-slate-200"
                      >
                        {dependency}
                      </span>
                    ))}
                  </div>
                </div>
              ) : null}

              <div className="mt-auto flex items-center justify-between border-t border-slate-100 pt-3">
                <span className="inline-flex items-center gap-1 text-[10px] text-slate-400">
                  <Settings2 className="h-3 w-3" />
                  {service.manifest.permissions?.length ?? 0} прав в манифесте
                </span>
                <Link
                  to={serviceRoute(service.code)}
                  className="inline-flex items-center gap-1 text-[11px] font-semibold text-brand-600 hover:text-brand-700"
                >
                  Открыть
                  <Layers className="h-3 w-3" />
                </Link>
              </div>
            </Card>
          ))}
        </div>
      )}

      <Card className="flex flex-col gap-3 border-brand-100 bg-gradient-to-br from-brand-50 to-white p-5 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-3">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-600 text-white">
            <Sparkles className="h-5 w-5" />
          </span>
          <div>
            <p className="text-sm font-bold text-slate-900">Как работает приоритет</p>
            <p className="mt-1 max-w-2xl text-xs leading-5 text-slate-600">
              Активация на уровне класса перекрывает школу, школа — город, город —
              область, область — республику. Если настройки нет, действует значение по
              умолчанию. Сервисы ядра отключить невозможно.
            </p>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2 text-[11px] font-semibold text-brand-700">
          <Info className="h-4 w-4" />
          {scopeLabels[scopeMode]}
        </div>
      </Card>
    </div>
  );
}

function FilterChip({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'rounded-lg px-2.5 py-1.5 text-[11px] font-semibold transition',
        active
          ? 'bg-brand-600 text-white shadow-sm'
          : 'bg-slate-100 text-slate-500 hover:bg-slate-200 hover:text-slate-700',
      )}
    >
      {children}
    </button>
  );
}

function SummaryCard({
  label,
  value,
  hint,
  icon,
  tone,
}: {
  label: string;
  value: string | number;
  hint: string;
  icon: ReactNode;
  tone: 'brand' | 'accent' | 'amber';
}) {
  const tones = {
    brand: 'bg-brand-50 text-brand-600',
    accent: 'bg-accent-50 text-accent-600',
    amber: 'bg-amber-50 text-amber-600',
  } as const;

  return (
    <Card className="flex items-center gap-3 p-4">
      <span className={cn('flex h-10 w-10 items-center justify-center rounded-xl', tones[tone])}>
        {icon}
      </span>
      <div>
        <p className="text-[10px] font-bold uppercase tracking-wide text-slate-500">{label}</p>
        <p className="text-xl font-bold text-slate-900">{value}</p>
        <p className="text-[10px] text-slate-400">{hint}</p>
      </div>
    </Card>
  );
}

function sourceLabel(source: EffectiveService['source']): string {
  if (source === 'core') return 'ядро';
  if (source === 'activation') return 'активация';
  return 'по умолчанию';
}
