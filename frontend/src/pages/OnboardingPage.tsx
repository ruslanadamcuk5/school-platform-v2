import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  ArrowRight,
  Award,
  BarChart3,
  BookOpenCheck,
  CheckCircle2,
  ChevronRight,
  Clock3,
  GraduationCap,
  Play,
  RefreshCw,
  Sparkles,
  Target,
  TrendingUp,
} from 'lucide-react';

import { useAccess } from '../access/AccessContext';
import { apiErrorMessage, fetchOnboardingOverview } from '../api/client';
import type { OnboardingModule, OnboardingOverview } from '../api/types';
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
import { useCoach } from '../onboarding/CoachContext';

const statusLabels: Record<OnboardingModule['status'], string> = {
  not_started: 'Не начато',
  in_progress: 'В процессе',
  completed: 'Завершено',
  skipped: 'Пропущено',
};

const statusClasses: Record<OnboardingModule['status'], string> = {
  not_started: 'bg-slate-100 text-slate-600 ring-slate-200',
  in_progress: 'bg-amber-50 text-amber-700 ring-amber-200',
  completed: 'bg-accent-50 text-accent-700 ring-accent-200',
  skipped: 'bg-slate-100 text-slate-500 ring-slate-200',
};

function ProgressRing({ value }: { value: number }) {
  const safe = Math.max(0, Math.min(100, value));
  return (
    <div
      className="relative flex h-28 w-28 shrink-0 items-center justify-center rounded-full"
      style={{
        background: `conic-gradient(#34d399 ${safe * 3.6}deg, rgba(255,255,255,0.12) 0)`,
      }}
    >
      <div className="flex h-[88px] w-[88px] flex-col items-center justify-center rounded-full bg-slate-950 text-white">
        <span className="text-2xl font-bold">{safe}%</span>
        <span className="text-[9px] font-semibold uppercase tracking-[0.16em] text-slate-500">
          прогресс
        </span>
      </div>
    </div>
  );
}

function ModuleCard({
  module,
  onStart,
  starting,
}: {
  module: OnboardingModule;
  onStart: (module: OnboardingModule) => void;
  starting: boolean;
}) {
  const navigate = useNavigate();
  const actionLabel =
    module.status === 'completed'
      ? 'Повторить'
      : module.status === 'in_progress'
        ? 'Продолжить'
        : module.is_addon
          ? 'Пройти дообучение'
          : 'Начать';
  const progress = module.total_steps
    ? Math.round((module.completed_steps / module.total_steps) * 100)
    : module.progress_percent;

  return (
    <Card
      className={cn(
        'group flex h-full flex-col overflow-hidden transition hover:-translate-y-0.5 hover:shadow-lg',
        module.is_addon ? 'border-accent-200 ring-1 ring-accent-100' : '',
      )}
    >
      <div className="flex flex-1 flex-col p-5">
        <div className="flex items-start gap-3">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-slate-100 text-xl">
            {module.icon}
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-1.5">
              <Badge className={statusClasses[module.status]}>
                {statusLabels[module.status]}
              </Badge>
              {module.is_addon ? (
                <Badge className="bg-accent-50 text-accent-700 ring-accent-200">
                  <Sparkles className="h-3 w-3" />
                  Дообучение
                </Badge>
              ) : null}
            </div>
            <Link
              to={`/onboarding/${module.code}`}
              className="mt-1.5 block text-sm font-bold text-slate-900 hover:text-brand-700"
            >
              {module.title}
            </Link>
            <p className="mt-1 flex items-center gap-2 text-[11px] font-medium text-slate-500">
              <span>{module.service_icon}</span>
              {module.service_name}
              <span className="text-slate-300">·</span>
              <Clock3 className="h-3 w-3" />
              {module.estimated_minutes} мин
            </p>
          </div>
        </div>

        <p className="mt-3 line-clamp-2 text-xs leading-5 text-slate-500">
          {module.description}
        </p>

        <div className="mt-4">
          <div className="flex items-center justify-between text-[10px] font-semibold text-slate-500">
            <span>
              {module.completed_steps} из {module.total_steps}{' '}
              {pluralize(module.total_steps, 'шага', 'шагов', 'шагов')}
            </span>
            <span>{progress}%</span>
          </div>
          <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-slate-100">
            <div
              className={cn(
                'h-full rounded-full transition-all',
                module.status === 'completed'
                  ? 'bg-accent-500'
                  : 'bg-gradient-to-r from-brand-500 to-accent-500',
              )}
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        <div className="mt-4 flex items-center gap-2">
          <Button
            size="sm"
            variant={module.status === 'completed' ? 'outline' : 'primary'}
            className="flex-1"
            onClick={() => onStart(module)}
            loading={starting}
          >
            {module.status === 'completed' ? (
              <RefreshCw className="h-3.5 w-3.5" />
            ) : (
              <Play className="h-3.5 w-3.5" />
            )}
            {actionLabel}
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => navigate(`/onboarding/${module.code}`)}
            aria-label={`Открыть модуль ${module.title}`}
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </Card>
  );
}

export function OnboardingPage() {
  const { can } = useAccess();
  const { start, busy } = useCoach();
  const navigate = useNavigate();
  const [overview, setOverview] = useState<OnboardingOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setOverview(await fetchOnboardingOverview());
    } catch (reason) {
      setError(apiErrorMessage(reason));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  const nextModule = useMemo(() => {
    if (!overview) return null;
    return (
      overview.modules.find((module) => module.status === 'in_progress') ??
      overview.modules.find((module) => module.status === 'not_started') ??
      overview.modules[0] ??
      null
    );
  }, [overview]);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Персональная программа"
        title="Обучение работе в платформе"
        subtitle="Интерактивные туры по тем сервисам, которые включены именно вам. Проходите по шагам — прогресс сохраняется."
        actions={
          <div className="flex flex-wrap gap-2">
            {can('onboarding.progress.read') ? (
              <Link to="/onboarding/reports">
                <Button variant="outline" size="sm">
                  <BarChart3 className="h-4 w-4" />
                  Отчёты
                </Button>
              </Link>
            ) : null}
            <Button variant="outline" size="sm" onClick={() => void load()} loading={loading}>
              <RefreshCw className="h-4 w-4" />
              Обновить
            </Button>
          </div>
        }
      />

      {error ? <ErrorAlert message={error} onRetry={() => void load()} /> : null}

      {loading && !overview ? (
        <div className="grid gap-4 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <Card key={index} className="p-5">
              <Skeleton className="h-3 w-24" />
              <Skeleton className="mt-3 h-8 w-16" />
              <Skeleton className="mt-2 h-3 w-32" />
            </Card>
          ))}
        </div>
      ) : overview ? (
        <>
          <Card className="relative overflow-hidden border-0 bg-slate-950 p-6 text-white shadow-card sm:p-8">
            <div
              className="pointer-events-none absolute inset-0 opacity-80"
              style={{
                backgroundImage:
                  'radial-gradient(circle at 12% 20%, rgba(99,102,241,0.45), transparent 36%), radial-gradient(circle at 88% 85%, rgba(16,185,129,0.34), transparent 36%)',
              }}
            />
            <div className="relative flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
              <div className="max-w-2xl">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge className="border border-white/10 bg-white/10 text-accent-200 ring-white/10">
                    <GraduationCap className="h-3 w-3" />
                    {overview.total} модулей
                  </Badge>
                  {overview.addon_total > 0 ? (
                    <Badge className="border border-accent-300/20 bg-accent-400/15 text-accent-200 ring-accent-300/20">
                      <Sparkles className="h-3 w-3" />
                      {overview.addon_total} дообучение
                    </Badge>
                  ) : null}
                  <Badge className="border border-white/10 bg-white/5 text-slate-300 ring-white/10">
                    <Target className="h-3 w-3" />
                    {overview.completed} завершено
                  </Badge>
                </div>
                <h2 className="mt-4 text-2xl font-bold tracking-tight sm:text-3xl">
                  {overview.completed === overview.total && overview.total > 0
                    ? 'Программа пройдена. Отличная работа!'
                    : 'Продолжайте в удобном темпе'}
                </h2>
                <p className="mt-2 max-w-xl text-sm leading-6 text-slate-400">
                  Обучение можно проходить за несколько дней. Если администратор
                  включит новый сервис, здесь появится отдельное дообучение только
                  по новым возможностям.
                </p>
                {nextModule ? (
                  <div className="mt-5 flex flex-wrap items-center gap-2">
                    <Button
                      variant="secondary"
                      size="md"
                      onClick={() => void start(nextModule)}
                      loading={busy}
                    >
                      <Play className="h-4 w-4" />
                      {nextModule.status === 'in_progress'
                        ? 'Продолжить обучение'
                        : 'Начать обучение'}
                    </Button>
                    <Button
                      variant="ghost"
                      size="md"
                      className="text-slate-300 hover:bg-white/10 hover:text-white"
                      onClick={() => navigate(`/onboarding/${nextModule.code}`)}
                    >
                      О модуле
                      <ArrowRight className="h-4 w-4" />
                    </Button>
                  </div>
                ) : null}
              </div>
              <ProgressRing value={overview.progress_percent} />
            </div>
          </Card>

          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard
              label="Всего модулей"
              value={overview.total}
              hint={`${overview.not_started} ещё не начато`}
              icon={<BookOpenCheck className="h-5 w-5" />}
              accent="brand"
            />
            <StatCard
              label="Завершено"
              value={overview.completed}
              hint={`${overview.progress_percent}% программы`}
              icon={<CheckCircle2 className="h-5 w-5" />}
              accent="accent"
            />
            <StatCard
              label="В процессе"
              value={overview.in_progress}
              hint="можно продолжить сегодня"
              icon={<TrendingUp className="h-5 w-5" />}
              accent="amber"
            />
            <StatCard
              label="Дообучение"
              value={overview.addon_total}
              hint="по новым сервисам"
              icon={<Sparkles className="h-5 w-5" />}
              accent="sky"
            />
          </div>

          {overview.addon_total > 0 ? (
            <Card className="border-accent-200 bg-accent-50/60 p-4">
              <div className="flex items-start gap-3">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-accent-100 text-accent-700">
                  <Award className="h-4 w-4" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-accent-900">
                    Для вас открыто дообучение
                  </p>
                  <p className="mt-0.5 text-xs leading-5 text-accent-800">
                    Администратор включил новые сервисы. В программе появились
                    модули только по ним — остальные знания сохраняются.
                  </p>
                </div>
              </div>
            </Card>
          ) : null}

          {overview.stages.length === 0 ? (
            <Card>
              <EmptyState
                title="Модули пока не назначены"
                description="Для вашей роли и включённых сервисов нет доступных модулей. Проверьте права в профиле или обратитесь к администратору."
                icon={<GraduationCap className="h-6 w-6" />}
              />
            </Card>
          ) : (
            <div className="space-y-6">
              {overview.stages.map((stage, stageIndex) => (
                <section key={stage.code} className="space-y-3">
                  <div className="flex flex-wrap items-end justify-between gap-2">
                    <div>
                      <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-brand-600">
                        Этап {stageIndex + 1}
                      </p>
                      <h2 className="mt-0.5 text-lg font-bold tracking-tight text-slate-900">
                        {stage.title}
                      </h2>
                      <p className="mt-0.5 text-xs text-slate-500">{stage.description}</p>
                    </div>
                    <Badge className="bg-white text-slate-600 ring-slate-200">
                      {stage.completed} / {stage.total} завершено
                    </Badge>
                  </div>
                  <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                    {stage.modules.map((module) => (
                      <ModuleCard
                        key={module.code}
                        module={module}
                        onStart={(item) => void start(item)}
                        starting={busy}
                      />
                    ))}
                  </div>
                </section>
              ))}
            </div>
          )}

          <Card className="flex flex-col gap-3 border-slate-200 bg-white p-5 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-semibold text-slate-800">
                Обучение учитывает только ваши сервисы
              </p>
              <p className="mt-0.5 text-xs text-slate-500">
                Если сервис отключён, его модуль скрывается. Если включён позже —
                появляется дообучение.
              </p>
            </div>
            <Link to="/profile">
              <Button variant="outline" size="sm">
                Проверить права
                <ArrowRight className="h-3.5 w-3.5" />
              </Button>
            </Link>
          </Card>
        </>
      ) : null}
    </div>
  );
}
