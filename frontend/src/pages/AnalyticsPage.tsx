import { useEffect, useMemo, useState } from 'react';
import {
  BarChart3,
  Building2,
  CalendarDays,
  CheckCircle2,
  Download,
  GraduationCap,
  RefreshCw,
  ShieldCheck,
  TrendingUp,
  Users,
} from 'lucide-react';

import { useAccess } from '../access/AccessContext';
import {
  apiErrorMessage,
  downloadAnalyticsReport,
  fetchAnalyticsOverview,
  fetchSchools,
} from '../api/client';
import type { AnalyticsOverview, School } from '../api/types';
import { useAuth } from '../auth/AuthContext';
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
import { pluralize } from '../lib/labels';

function number(value: number): string {
  return new Intl.NumberFormat('ru-RU').format(value);
}

function percent(value: number | null): string {
  return value === null ? '—' : `${value.toFixed(1).replace('.', ',')}%`;
}

function average(value: number | null): string {
  return value === null ? '—' : value.toFixed(2).replace('.', ',');
}

function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function gradeTone(grade: number): string {
  if (grade >= 9) return 'bg-accent-500';
  if (grade >= 7) return 'bg-brand-500';
  if (grade >= 4) return 'bg-amber-400';
  return 'bg-rose-400';
}

export function AnalyticsPage() {
  const { user } = useAuth();
  const { can } = useAccess();

  const [schools, setSchools] = useState<School[]>([]);
  const [schoolId, setSchoolId] = useState(user?.school_id ?? '');
  const [year, setYear] = useState('');
  const [data, setData] = useState<AnalyticsOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  useEffect(() => {
    if (user?.role !== 'superadmin') return;
    let cancelled = false;
    fetchSchools()
      .then((items) => {
        if (cancelled) return;
        setSchools(items);
        setSchoolId((current) => current || items[0]?.id || '');
      })
      .catch(() => {
        // The report still reports the access error when loading.
      });
    return () => {
      cancelled = true;
    };
  }, [user?.role]);

  useEffect(() => {
    let cancelled = false;
    if (!schoolId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    fetchAnalyticsOverview({
      school_id: schoolId,
      academic_year: year || undefined,
    })
      .then((payload) => {
        if (cancelled) return;
        setData(payload);
      })
      .catch((reason) => {
        if (!cancelled) setError(apiErrorMessage(reason));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [schoolId, year, reloadKey]);

  const distributionMax = useMemo(() => {
    if (!data) return 1;
    return Math.max(1, ...Object.values(data.grades.distribution));
  }, [data]);

  async function handleExport() {
    setExportError(null);
    setExporting(true);
    try {
      const blob = await downloadAnalyticsReport({
        school_id: schoolId || undefined,
        academic_year: year || undefined,
      });
      const suffix = (year || 'report').replace('/', '-');
      saveBlob(blob, `analytics-${suffix}.csv`);
    } catch (reason) {
      setExportError(apiErrorMessage(reason));
    } finally {
      setExporting(false);
    }
  }

  const canExport = can('analytics.reports.export');
  const selectedSchool = schools.find((item) => item.id === schoolId);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Аналитика и отчётность"
        title="Аналитика школы"
        subtitle="Оценки, посещаемость и срезы по предметам и классам. Данные доступны только в пределах вашей школы."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Badge className="bg-brand-50 text-brand-700 ring-brand-200">
              <BarChart3 className="h-3 w-3" />
              Базовые отчёты
            </Badge>
            {canExport ? (
              <Button
                variant="outline"
                onClick={() => void handleExport()}
                disabled={exporting || !data}
              >
                <Download className={cn('h-4 w-4', exporting && 'animate-bounce')} />
                {exporting ? 'Выгружаем…' : 'CSV'}
              </Button>
            ) : null}
            <Button
              variant="outline"
              onClick={() => {
                setYear('');
                setData(null);
                setError(null);
                setReloadKey((value) => value + 1);
              }}
              disabled={loading}
            >
              <RefreshCw className={cn('h-4 w-4', loading && 'animate-spin')} />
              Обновить
            </Button>
          </div>
        }
      />

      <Card className="p-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div className="flex flex-1 flex-col gap-3 sm:flex-row">
            {user?.role === 'superadmin' ? (
              <label className="block min-w-0 flex-1">
                <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                  Школа
                </span>
                <div className="relative">
                  <Building2 className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                  <select
                    value={schoolId}
                    onChange={(event) => {
                      setSchoolId(event.target.value);
                      setYear('');
                    }}
                    className="h-10 w-full rounded-xl border border-slate-200 bg-white pl-9 pr-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
                  >
                    <option value="">Выберите школу</option>
                    {schools.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.name}
                      </option>
                    ))}
                  </select>
                </div>
              </label>
            ) : (
              <div className="flex min-w-0 flex-1 items-center gap-3 rounded-xl bg-slate-50 px-3 py-2.5">
                <Building2 className="h-4 w-4 text-slate-400" />
                <div className="min-w-0">
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                    Школа
                  </p>
                  <p className="truncate text-sm font-semibold text-slate-800">
                    {data?.school_name ?? user?.full_name ?? 'Ваша школа'}
                  </p>
                </div>
              </div>
            )}

            <label className="block sm:w-48">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Учебный год
              </span>
              <div className="relative">
                <CalendarDays className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <select
                  value={year || data?.academic_year || ''}
                  onChange={(event) => setYear(event.target.value)}
                  className="h-10 w-full rounded-xl border border-slate-200 bg-white pl-9 pr-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
                >
                  {(data?.available_years ?? []).map((item) => (
                    <option key={item} value={item}>
                      {item}
                    </option>
                  ))}
                  {data && !data.available_years.includes(year) && year ? (
                    <option value={year}>{year}</option>
                  ) : null}
                  {!data?.available_years.length ? (
                    <option value={year || ''}>{year || 'Нет учебных годов'}</option>
                  ) : null}
                </select>
              </div>
            </label>
          </div>

          <div className="flex items-center gap-2 text-xs text-slate-500">
            <ShieldCheck className="h-4 w-4 text-accent-500" />
            Изоляция по школе и правам
          </div>
        </div>
      </Card>

      {exportError ? (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          Не удалось выгрузить CSV: {exportError}
        </div>
      ) : null}

      {error ? (
        <ErrorAlert
          message={error}
          onRetry={() => setReloadKey((value) => value + 1)}
        />
      ) : null}

      {loading ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="h-32" />
          ))}
        </div>
      ) : null}

      {!loading && !error && data ? (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard
              label="Ученики"
              value={number(data.totals.students)}
              hint="активные аккаунты"
              icon={<Users className="h-5 w-5" />}
              accent="brand"
            />
            <StatCard
              label="Учителя"
              value={number(data.totals.teachers)}
              hint="активные аккаунты"
              icon={<GraduationCap className="h-5 w-5" />}
              accent="accent"
            />
            <StatCard
              label="Классы"
              value={number(data.totals.classes)}
              hint={data.academic_year}
              icon={<Building2 className="h-5 w-5" />}
              accent="sky"
            />
            <StatCard
              label="Оценки"
              value={number(data.totals.grades_count)}
              hint={`средний балл ${average(data.grades.average)}`}
              icon={<BarChart3 className="h-5 w-5" />}
              accent="amber"
            />
          </div>

          <div className="grid gap-4 xl:grid-cols-[1.35fr_1fr]">
            <Card className="p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 className="text-base font-semibold text-slate-900">
                    Распределение оценок
                  </h2>
                  <p className="mt-1 text-sm text-slate-500">
                    Все выставленные оценки за {data.academic_year} учебный год.
                  </p>
                </div>
                <Badge className="bg-slate-100 text-slate-600 ring-slate-200">
                  <TrendingUp className="h-3 w-3" />
                  средний {average(data.grades.average)}
                </Badge>
              </div>

              {data.totals.grades_count === 0 ? (
                <EmptyState
                  title="Оценок пока нет"
                  description="Как только учителя начнут выставлять оценки, здесь появится распределение по баллам."
                  icon={<BarChart3 className="h-6 w-6" />}
                />
              ) : (
                <>
                  <div className="mt-5 flex h-44 items-end gap-2">
                    {Object.entries(data.grades.distribution)
                      .sort(([left], [right]) => Number(left) - Number(right))
                      .map(([grade, count]) => (
                        <div
                          key={grade}
                          className="flex min-w-0 flex-1 flex-col items-center gap-2"
                        >
                          <span className="text-[10px] font-semibold text-slate-500">
                            {count}
                          </span>
                          <div className="flex h-32 w-full items-end rounded-lg bg-slate-100">
                            <div
                              className={cn(
                                'w-full rounded-lg transition-all duration-500',
                                gradeTone(Number(grade)),
                              )}
                              style={{
                                height: `${Math.max(4, (count / distributionMax) * 100)}%`,
                              }}
                            />
                          </div>
                          <span className="text-xs font-semibold text-slate-600">
                            {grade}
                          </span>
                        </div>
                      ))}
                  </div>
                  <div className="mt-5 grid grid-cols-2 gap-2 sm:grid-cols-4">
                    {[
                      ['Отлично', data.grades.excellent, 'text-accent-700 bg-accent-50'],
                      ['Хорошо', data.grades.good, 'text-brand-700 bg-brand-50'],
                      ['Удовлетв.', data.grades.satisfactory, 'text-amber-700 bg-amber-50'],
                      ['Низкие', data.grades.low, 'text-rose-700 bg-rose-50'],
                    ].map(([label, value, tone]) => (
                      <div
                        key={String(label)}
                        className={cn('rounded-xl px-3 py-2', String(tone))}
                      >
                        <p className="text-[10px] font-semibold uppercase tracking-wide">
                          {label}
                        </p>
                        <p className="mt-0.5 text-lg font-bold">{number(Number(value))}</p>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </Card>

            <Card className="p-5">
              <div>
                <h2 className="text-base font-semibold text-slate-900">Посещаемость</h2>
                <p className="mt-1 text-sm text-slate-500">
                  Доля присутствующих и опоздавших от всех отметок.
                </p>
              </div>

              <div className="mt-5 flex flex-col items-center gap-5 sm:flex-row">
                <div
                  className="relative flex h-36 w-36 shrink-0 items-center justify-center rounded-full"
                  style={{
                    background: `conic-gradient(#10b981 ${
                      (data.attendance.rate ?? 0) * 3.6
                    }deg, #e2e8f0 0deg)`,
                  }}
                >
                  <div className="flex h-28 w-28 flex-col items-center justify-center rounded-full bg-white shadow-inner">
                    <span className="text-2xl font-bold text-slate-900">
                      {percent(data.attendance.rate)}
                    </span>
                    <span className="text-[11px] text-slate-500">посещаемость</span>
                  </div>
                </div>

                <div className="grid w-full grid-cols-2 gap-2 text-sm">
                  {[
                    ['Присутствовали', data.attendance.present, 'bg-accent-500'],
                    ['Опоздали', data.attendance.late, 'bg-sky-400'],
                    ['Болели', data.attendance.sick, 'bg-amber-400'],
                    ['Отсутствовали', data.attendance.absent, 'bg-rose-400'],
                    ['Уважительная', data.attendance.excused, 'bg-slate-400'],
                  ].map(([label, value, tone]) => (
                    <div key={String(label)} className="flex items-center gap-2">
                      <span className={cn('h-2.5 w-2.5 rounded-full', String(tone))} />
                      <span className="min-w-0 flex-1 truncate text-slate-600">
                        {label}
                      </span>
                      <span className="font-semibold text-slate-900">
                        {number(Number(value))}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="mt-5 flex items-center gap-2 rounded-xl bg-accent-50 px-3 py-2 text-xs text-accent-800">
                <CheckCircle2 className="h-4 w-4 shrink-0" />
                Всего отметок: {number(data.attendance.total)}
              </div>
            </Card>
          </div>

          <div className="grid gap-4 xl:grid-cols-2">
            <Card className="p-5">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h2 className="text-base font-semibold text-slate-900">
                    Предметы
                  </h2>
                  <p className="mt-1 text-sm text-slate-500">
                    Средний балл и посещаемость по предметам.
                  </p>
                </div>
                <Badge className="bg-slate-100 text-slate-600 ring-slate-200">
                  {pluralize(data.subjects.length, 'предмет', 'предмета', 'предметов')}
                </Badge>
              </div>

              {data.subjects.length === 0 ? (
                <EmptyState
                  title="Нет данных по предметам"
                  description="Отчёт появится после первых записей в журнале."
                  icon={<BarChart3 className="h-6 w-6" />}
                />
              ) : (
                <div className="mt-4 space-y-3">
                  {data.subjects.map((subject) => (
                    <div key={subject.subject_id} className="space-y-1.5">
                      <div className="flex items-center justify-between gap-3 text-sm">
                        <span className="truncate font-medium text-slate-700">
                          {subject.subject_name}
                        </span>
                        <span className="shrink-0 text-xs text-slate-500">
                          {average(subject.average)} · {percent(subject.attendance_rate)}
                        </span>
                      </div>
                      <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                        <div
                          className="h-full rounded-full bg-gradient-to-r from-brand-500 to-accent-500"
                          style={{
                            width: `${Math.min(100, ((subject.average ?? 0) / 10) * 100)}%`,
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Card>

            <Card className="p-5">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h2 className="text-base font-semibold text-slate-900">Классы</h2>
                  <p className="mt-1 text-sm text-slate-500">
                    Сводка по каждому классу за выбранный учебный год.
                  </p>
                </div>
                <Badge className="bg-slate-100 text-slate-600 ring-slate-200">
                  {pluralize(data.classes.length, 'класс', 'класса', 'классов')}
                </Badge>
              </div>

              {data.classes.length === 0 ? (
                <EmptyState
                  title="Классы не найдены"
                  description="Для выбранного учебного года в школе ещё нет классов."
                  icon={<Building2 className="h-6 w-6" />}
                />
              ) : (
                <div className="mt-4 overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead>
                      <tr className="border-b border-slate-100 text-[11px] uppercase tracking-wide text-slate-500">
                        <th className="px-2 py-2 font-semibold">Класс</th>
                        <th className="px-2 py-2 text-right font-semibold">Ученики</th>
                        <th className="px-2 py-2 text-right font-semibold">Средний</th>
                        <th className="px-2 py-2 text-right font-semibold">Посещ.</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.classes.map((item) => (
                        <tr
                          key={item.class_id}
                          className="border-b border-slate-50 last:border-0 hover:bg-slate-50/60"
                        >
                          <td className="px-2 py-2.5 font-semibold text-slate-800">
                            {item.class_name}
                          </td>
                          <td className="px-2 py-2.5 text-right text-slate-600">
                            {number(item.students)}
                          </td>
                          <td className="px-2 py-2.5 text-right text-slate-600">
                            {average(item.average)}
                          </td>
                          <td className="px-2 py-2.5 text-right text-slate-600">
                            {percent(item.attendance_rate)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>
          </div>

          <p className="text-xs text-slate-400">
            Отчёт сформирован {new Date(data.generated_at).toLocaleString('ru-RU')} ·{' '}
            {selectedSchool?.name ?? data.school_name}
          </p>
        </>
      ) : null}

      {!loading && !error && !schoolId ? (
        <Card>
          <EmptyState
            title="Выберите школу"
            description="Для супер-администратора школа выбирается явно, чтобы не смешивать данные контуров."
            icon={<Building2 className="h-6 w-6" />}
          />
        </Card>
      ) : null}
    </div>
  );
}
