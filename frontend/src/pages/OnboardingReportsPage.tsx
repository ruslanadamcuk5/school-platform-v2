import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowLeft,
  BarChart3,
  CheckCircle2,
  Clock3,
  Download,
  GraduationCap,
  RefreshCw,
  RotateCcw,
  Search,
  Sparkles,
  TrendingUp,
  Users,
} from 'lucide-react';

import { useAccess } from '../access/AccessContext';
import {
  apiErrorMessage,
  downloadOnboardingReport,
  fetchOnboardingReportUsers,
  fetchSchools,
  resetOnboardingUser,
} from '../api/client';
import type {
  OnboardingReportUser,
  OnboardingReportUsers,
  OnboardingStatus,
  Role,
  School,
} from '../api/types';
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorAlert,
  PageHeader,
  Skeleton,
  StatCard,
} from '../components/ui';
import { cn } from '../lib/cn';
import { formatDateTime, roleLabel } from '../lib/labels';

const PAGE_SIZE = 25;

const statusLabels: Record<OnboardingStatus, string> = {
  not_started: 'Не начато',
  in_progress: 'В процессе',
  completed: 'Завершено',
  skipped: 'Пропущено',
};

const statusClasses: Record<OnboardingStatus, string> = {
  not_started: 'bg-slate-100 text-slate-600 ring-slate-200',
  in_progress: 'bg-amber-50 text-amber-700 ring-amber-200',
  completed: 'bg-accent-50 text-accent-700 ring-accent-200',
  skipped: 'bg-slate-100 text-slate-500 ring-slate-200',
};

const filterRoles: Role[] = [
  'admin',
  'methodologist',
  'teacher',
  'student',
  'parent',
  'psychologist',
  'secretary',
];

const filterStatuses: OnboardingStatus[] = [
  'not_started',
  'in_progress',
  'completed',
];

function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

function ProgressBar({ value }: { value: number }) {
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-20 overflow-hidden rounded-full bg-slate-100">
        <div
          className={cn(
            'h-full rounded-full',
            value >= 100
              ? 'bg-accent-500'
              : 'bg-gradient-to-r from-brand-500 to-accent-500',
          )}
          style={{ width: `${Math.max(0, Math.min(100, value))}%` }}
        />
      </div>
      <span className="w-8 text-right text-[10px] font-semibold text-slate-500">
        {value}%
      </span>
    </div>
  );
}

function UserRow({
  item,
  canReset,
  onReset,
  resetting,
  institutionType,
}: {
  item: OnboardingReportUser;
  canReset: boolean;
  onReset: (item: OnboardingReportUser) => void;
  resetting: boolean;
  institutionType: School['institution_type'] | null;
}) {
  return (
    <tr className="border-t border-slate-100 transition hover:bg-slate-50/70">
      <td className="px-4 py-3">
        <p className="text-xs font-semibold text-slate-900">{item.full_name}</p>
        <p className="text-[10px] text-slate-500">@{item.login}</p>
      </td>
      <td className="px-4 py-3">
        <Badge className="bg-slate-100 text-slate-600 ring-slate-200">
          {roleLabel(item.role, institutionType)}
        </Badge>
      </td>
      <td className="hidden px-4 py-3 text-[11px] text-slate-600 lg:table-cell">
        {item.school_name ?? '—'}
      </td>
      <td className="px-4 py-3 text-[11px] text-slate-600">
        <span className="font-semibold text-slate-800">{item.modules_completed}</span>
        <span className="text-slate-400"> / {item.modules_total}</span>
        {item.addon_modules > 0 ? (
          <Badge className="ml-2 bg-accent-50 text-accent-700 ring-accent-200">
            <Sparkles className="h-2.5 w-2.5" />
            {item.addon_modules}
          </Badge>
        ) : null}
      </td>
      <td className="px-4 py-3">
        <Badge className={statusClasses[item.status]}>
          {statusLabels[item.status]}
        </Badge>
      </td>
      <td className="hidden px-4 py-3 md:table-cell">
        <ProgressBar value={item.progress_percent} />
      </td>
      <td className="hidden px-4 py-3 text-[10px] text-slate-500 xl:table-cell">
        {formatDateTime(item.last_activity_at)}
      </td>
      <td className="px-4 py-3 text-right">
        {canReset ? (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onReset(item)}
            disabled={resetting}
            aria-label={`Сбросить прогресс ${item.full_name}`}
            title="Сбросить прогресс"
          >
            <RotateCcw className="h-3.5 w-3.5" />
          </Button>
        ) : null}
      </td>
    </tr>
  );
}

export function OnboardingReportsPage() {
  const { can, institutionType } = useAccess();
  const [data, setData] = useState<OnboardingReportUsers | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [role, setRole] = useState('');
  const [status, setStatus] = useState('');
  const [offset, setOffset] = useState(0);
  const [exporting, setExporting] = useState(false);
  const [resetting, setResetting] = useState<string | null>(null);
  const [schools, setSchools] = useState<School[]>([]);

  const canReset = can('onboarding.progress.manage');

  useEffect(() => {
    let cancelled = false;
    async function loadSchools() {
      try {
        const result = await fetchSchools();
        if (!cancelled) setSchools(result);
      } catch {
        if (!cancelled) setSchools([]);
      }
    }
    void loadSchools();
    return () => {
      cancelled = true;
    };
  }, []);

  function institutionTypeFor(
    schoolId: string | null,
  ): School['institution_type'] | null {
    if (!schoolId) return institutionType;
    return (
      schools.find((school) => school.id === schoolId)?.institution_type ??
      institutionType
    );
  }

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setData(
        await fetchOnboardingReportUsers({
          search: search.trim() || undefined,
          role: role || undefined,
          status: status || undefined,
          limit: PAGE_SIZE,
          offset,
        }),
      );
    } catch (reason) {
      setError(apiErrorMessage(reason));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [offset, role, status]);

  useEffect(() => {
    setOffset(0);
  }, [search, role, status]);

  const summary = data?.summary;
  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const page = Math.floor(offset / PAGE_SIZE) + 1;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const rangeLabel = useMemo(() => {
    if (total === 0) return '0';
    return `${offset + 1}–${Math.min(offset + PAGE_SIZE, total)} из ${total}`;
  }, [offset, total]);

  async function handleExport() {
    setExporting(true);
    setError(null);
    try {
      const blob = await downloadOnboardingReport({
        search: search.trim() || undefined,
        role: role || undefined,
        status: status || undefined,
      });
      const stamp = new Date().toISOString().slice(0, 10);
      saveBlob(blob, `onboarding-progress-${stamp}.csv`);
    } catch (reason) {
      setError(apiErrorMessage(reason));
    } finally {
      setExporting(false);
    }
  }

  async function handleReset(item: OnboardingReportUser) {
    const confirmed = window.confirm(
      `Сбросить прогресс обучения пользователя «${item.full_name}»? ` +
        'Модули снова станут доступны для прохождения.',
    );
    if (!confirmed) return;
    setResetting(item.user_id);
    setError(null);
    try {
      await resetOnboardingUser(item.user_id);
      await load();
    } catch (reason) {
      setError(apiErrorMessage(reason));
    } finally {
      setResetting(null);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Отчётность"
        title="Прогресс обучения"
        subtitle="Кто прошёл обучение, кто в процессе и где появилось дообучение по новым сервисам. Учитель видит своих учеников, руководитель — свою школу."
        actions={
          <div className="flex flex-wrap gap-2">
            <Link to="/onboarding">
              <Button variant="outline" size="sm">
                <ArrowLeft className="h-4 w-4" />
                К программе
              </Button>
            </Link>
            <Button variant="outline" size="sm" onClick={() => void load()} loading={loading}>
              <RefreshCw className="h-4 w-4" />
              Обновить
            </Button>
            <Button
              size="sm"
              onClick={() => void handleExport()}
              loading={exporting}
              disabled={total === 0}
            >
              <Download className="h-4 w-4" />
              CSV
            </Button>
          </div>
        }
      />

      {error ? <ErrorAlert message={error} onRetry={() => void load()} /> : null}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Пользователей в отчёте"
          value={summary?.total_users ?? 0}
          hint="с учётом фильтров"
          icon={<Users className="h-5 w-5" />}
          accent="brand"
        />
        <StatCard
          label="Завершили обучение"
          value={summary?.users_completed ?? 0}
          hint="все доступные модули"
          icon={<CheckCircle2 className="h-5 w-5" />}
          accent="accent"
        />
        <StatCard
          label="В процессе"
          value={summary?.users_in_progress ?? 0}
          hint="есть сохранённый прогресс"
          icon={<TrendingUp className="h-5 w-5" />}
          accent="amber"
        />
        <StatCard
          label="Не начинали"
          value={summary?.users_not_started ?? 0}
          hint="нет ни одного шага"
          icon={<Clock3 className="h-5 w-5" />}
          accent="sky"
        />
      </div>

      <Card className="overflow-hidden">
        <div className="flex flex-col gap-3 border-b border-slate-100 p-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="relative min-w-0 flex-1 lg:max-w-xs">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter') {
                  setOffset(0);
                  void load();
                }
              }}
              placeholder="ФИО или логин…"
              className="h-9 w-full rounded-xl border border-slate-200 bg-slate-50 pl-9 pr-3 text-xs text-slate-700 outline-none transition placeholder:text-slate-400 focus:border-brand-300 focus:bg-white focus:ring-2 focus:ring-brand-100"
            />
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={role}
              onChange={(event) => setRole(event.target.value)}
              className="h-9 rounded-xl border border-slate-200 bg-white px-2.5 text-xs text-slate-700 outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              aria-label="Фильтр по роли"
            >
              <option value="">Все роли</option>
              {filterRoles.map((item) => (
                <option key={item} value={item}>
                  {roleLabel(item, institutionType)}
                </option>
              ))}
            </select>
            <select
              value={status}
              onChange={(event) => setStatus(event.target.value)}
              className="h-9 rounded-xl border border-slate-200 bg-white px-2.5 text-xs text-slate-700 outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              aria-label="Фильтр по статусу"
            >
              <option value="">Все статусы</option>
              {filterStatuses.map((item) => (
                <option key={item} value={item}>
                  {statusLabels[item]}
                </option>
              ))}
            </select>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setSearch('');
                setRole('');
                setStatus('');
                setOffset(0);
                void load();
              }}
            >
              Сбросить
            </Button>
          </div>
        </div>

        {summary ? (
          <div className="flex flex-wrap gap-x-6 gap-y-1 border-b border-slate-100 bg-slate-50/60 px-4 py-2.5 text-[10px] text-slate-500">
            <span>
              Модулей завершено:{' '}
              <strong className="text-slate-700">{summary.modules_completed}</strong>{' '}
              из {summary.modules_total}
            </span>
            <span>
              Средний прогресс:{' '}
              <strong className="text-slate-700">{summary.progress_percent}%</strong>
            </span>
            <span>
              Дообучение:{' '}
              <strong className="text-slate-700">{summary.addon_modules}</strong>
            </span>
            {Object.entries(summary.by_role).length > 0 ? (
              <span>
                По ролям:{' '}
                {Object.entries(summary.by_role)
                  .map(
                    ([code, count]) =>
                      `${roleLabel(code, institutionType)}: ${count}`,
                  )
                  .join(' · ')}
              </span>
            ) : null}
          </div>
        ) : null}

        {loading && !data ? (
          <div className="space-y-2 p-4">
            {Array.from({ length: 6 }).map((_, index) => (
              <Skeleton key={index} className="h-12 w-full" />
            ))}
          </div>
        ) : items.length === 0 ? (
          <EmptyState
            title="Нет данных за выбранными фильтрами"
            description="Попробуйте изменить роль или статус. Если обучение отключено для контура, отчёт всё равно доступен."
            icon={<BarChart3 className="h-6 w-6" />}
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[780px] text-left">
              <thead className="bg-white text-[10px] uppercase tracking-[0.12em] text-slate-400">
                <tr>
                  <th className="px-4 py-2.5 font-semibold">Пользователь</th>
                  <th className="px-4 py-2.5 font-semibold">Роль</th>
                  <th className="hidden px-4 py-2.5 font-semibold lg:table-cell">
                    Школа
                  </th>
                  <th className="px-4 py-2.5 font-semibold">Модули</th>
                  <th className="px-4 py-2.5 font-semibold">Статус</th>
                  <th className="hidden px-4 py-2.5 font-semibold md:table-cell">
                    Прогресс
                  </th>
                  <th className="hidden px-4 py-2.5 font-semibold xl:table-cell">
                    Активность
                  </th>
                  <th className="px-4 py-2.5" />
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <UserRow
                    key={item.user_id}
                    item={item}
                    canReset={canReset}
                    onReset={(target) => void handleReset(target)}
                    resetting={resetting === item.user_id}
                    institutionType={institutionTypeFor(item.school_id)}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 px-4 py-3">
          <p className="text-[10px] text-slate-500">{rangeLabel}</p>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={offset === 0 || loading}
              onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
            >
              Назад
            </Button>
            <span className="text-[10px] font-semibold text-slate-500">
              {page} / {pages}
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={offset + PAGE_SIZE >= total || loading}
              onClick={() => setOffset(offset + PAGE_SIZE)}
            >
              Вперёд
            </Button>
          </div>
        </div>
      </Card>

      <Card className="flex flex-col gap-3 border-slate-200 bg-white p-5 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-brand-50 text-brand-600">
            <GraduationCap className="h-5 w-5" />
          </div>
          <div>
            <p className="text-sm font-semibold text-slate-800">
              Отчёт учитывает иерархию доступа
            </p>
            <p className="mt-0.5 max-w-2xl text-xs leading-5 text-slate-500">
              Администратор и руководитель видят свою школу или регион, учитель —
              только своих учеников. Сброс прогресса доступен только с правом
              onboarding.progress.manage и фиксируется в журнале аудита.
            </p>
          </div>
        </div>
        <Link to="/onboarding">
          <Button variant="outline" size="sm">
            <ArrowLeft className="h-3.5 w-3.5" />
            Программа обучения
          </Button>
        </Link>
      </Card>
    </div>
  );
}
