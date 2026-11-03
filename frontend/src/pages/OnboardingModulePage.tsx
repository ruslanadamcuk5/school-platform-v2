import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  Circle,
  Clock3,
  GraduationCap,
  MousePointerClick,
  Play,
  RefreshCw,
  Sparkles,
  Target,
} from 'lucide-react';

import { apiErrorMessage, fetchOnboardingModule } from '../api/client';
import type { OnboardingModule } from '../api/types';
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorAlert,
  PageHeader,
  Skeleton,
} from '../components/ui';
import { cn } from '../lib/cn';
import { formatDateTime, pluralize } from '../lib/labels';
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

export function OnboardingModulePage() {
  const { moduleCode } = useParams<{ moduleCode: string }>();
  const navigate = useNavigate();
  const { start, busy } = useCoach();
  const [module, setModule] = useState<OnboardingModule | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    if (!moduleCode) {
      setLoading(false);
      return;
    }
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchOnboardingModule(moduleCode as string);
        if (!cancelled) setModule(data);
      } catch (reason) {
        if (!cancelled) setError(apiErrorMessage(reason));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [moduleCode]);

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-72" />
        <Skeleton className="h-48 w-full" />
        <div className="grid gap-3 md:grid-cols-2">
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="h-24 w-full" />
          ))}
        </div>
      </div>
    );
  }

  if (error || !module) {
    return (
      <div className="space-y-6">
        <PageHeader eyebrow="Обучение" title="Модуль недоступен" />
        <ErrorAlert message={error ?? 'Модуль не найден.'} />
        <Button variant="outline" onClick={() => navigate('/onboarding')}>
          <ArrowLeft className="h-4 w-4" />
          Вернуться к программе
        </Button>
      </div>
    );
  }

  const progress = module.total_steps
    ? Math.round((module.completed_steps / module.total_steps) * 100)
    : module.progress_percent;
  const actionLabel =
    module.status === 'completed'
      ? 'Пройти заново'
      : module.status === 'in_progress'
        ? 'Продолжить обучение'
        : 'Начать обучение';

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Модуль обучения"
        title={module.title}
        subtitle={module.description}
        actions={
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" size="sm" onClick={() => navigate('/onboarding')}>
              <ArrowLeft className="h-4 w-4" />
              К программе
            </Button>
            <Button
              size="sm"
              variant={module.status === 'completed' ? 'outline' : 'primary'}
              onClick={() => void start(module)}
              loading={busy}
            >
              {module.status === 'completed' ? (
                <RefreshCw className="h-4 w-4" />
              ) : (
                <Play className="h-4 w-4" />
              )}
              {actionLabel}
            </Button>
          </div>
        }
      />

      <Card className="relative overflow-hidden border-0 bg-slate-950 p-6 text-white shadow-card sm:p-8">
        <div
          className="pointer-events-none absolute inset-0 opacity-80"
          style={{
            backgroundImage:
              'radial-gradient(circle at 14% 20%, rgba(99,102,241,0.45), transparent 36%), radial-gradient(circle at 88% 85%, rgba(16,185,129,0.32), transparent 36%)',
          }}
        />
        <div className="relative flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
          <div className="max-w-2xl">
            <div className="flex flex-wrap items-center gap-2">
              <Badge className="border border-white/10 bg-white/10 text-accent-200 ring-white/10">
                <span>{module.service_icon}</span>
                {module.service_name}
              </Badge>
              <Badge className="border border-white/10 bg-white/5 text-slate-300 ring-white/10">
                <Clock3 className="h-3 w-3" />
                {module.estimated_minutes} мин
              </Badge>
              <Badge className="border border-white/10 bg-white/5 text-slate-300 ring-white/10">
                {statusLabels[module.status]}
              </Badge>
              {module.is_addon ? (
                <Badge className="border border-accent-300/20 bg-accent-400/15 text-accent-200 ring-accent-300/20">
                  <Sparkles className="h-3 w-3" />
                  Дообучение
                </Badge>
              ) : null}
            </div>
            <h2 className="mt-4 text-2xl font-bold tracking-tight sm:text-3xl">
              {module.completed_steps} из {module.total_steps}{' '}
              {pluralize(module.total_steps, 'шага', 'шагов', 'шагов')} пройдено
            </h2>
            <p className="mt-2 max-w-xl text-sm leading-6 text-slate-400">
              Каждый шаг — это короткая инструкция с анимированным указателем на
              нужный элемент интерфейса. Можно остановиться и вернуться позже:
              прогресс сохраняется после каждого шага.
            </p>
            <div className="mt-5 flex flex-wrap gap-2">
              <Button variant="secondary" size="sm" onClick={() => void start(module)} loading={busy}>
                <MousePointerClick className="h-4 w-4" />
                {actionLabel}
              </Button>
              {module.status === 'completed' ? (
                <Link to="/onboarding/reports">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-slate-300 hover:bg-white/10 hover:text-white"
                  >
                    <Target className="h-4 w-4" />
                    Отчёты
                  </Button>
                </Link>
              ) : null}
            </div>
          </div>
          <div className="w-full max-w-sm rounded-2xl border border-white/10 bg-white/[0.06] p-4 backdrop-blur-sm">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-slate-300">Прогресс модуля</span>
              <span className="font-bold text-accent-300">{progress}%</span>
            </div>
            <div className="mt-2 h-2 overflow-hidden rounded-full bg-white/10">
              <div
                className="h-full rounded-full bg-gradient-to-r from-brand-400 to-accent-400 transition-all duration-500"
                style={{ width: `${progress}%` }}
              />
            </div>
            <div className="mt-3 flex items-center justify-between text-[10px] text-slate-500">
              <span>
                Последняя активность:{' '}
                {formatDateTime(module.last_activity_at ?? module.started_at)}
              </span>
              {module.completed_at ? (
                <span className="text-accent-300">
                  {formatDateTime(module.completed_at)}
                </span>
              ) : null}
            </div>
          </div>
        </div>
      </Card>

      {module.status === 'completed' ? (
        <Card className="border-accent-200 bg-accent-50/60 p-5">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-accent-100 text-accent-700">
              <CheckCircle2 className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm font-bold text-accent-900">Модуль завершён</p>
              <p className="mt-0.5 text-xs leading-5 text-accent-800">
                Результат виден администраторам, руководителям школы и учителям в
                отчётах. Можно пройти модуль заново, чтобы освежить знания.
              </p>
            </div>
          </div>
        </Card>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-[1.3fr_0.7fr]">
        <Card className="p-5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h2 className="flex items-center gap-2 text-sm font-bold text-slate-900">
                <GraduationCap className="h-4 w-4 text-brand-500" />
                Шаги модуля
              </h2>
              <p className="mt-0.5 text-xs text-slate-500">
                Нажмите «Начать», чтобы открыть интерактивный режим
              </p>
            </div>
            <Badge className={statusClasses[module.status]}>
              {statusLabels[module.status]}
            </Badge>
          </div>

          <div className="mt-4 space-y-2">
            {module.steps.map((step, index) => {
              const isCurrent =
                step.code === module.current_step_code &&
                module.status !== 'completed';
              return (
                <div
                  key={step.code}
                  className={cn(
                    'flex items-start gap-3 rounded-2xl border p-3 transition',
                    step.completed
                      ? 'border-accent-100 bg-accent-50/50'
                      : isCurrent
                        ? 'border-brand-200 bg-brand-50/50'
                        : 'border-slate-200 bg-white',
                  )}
                >
                  <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-white ring-1 ring-slate-200">
                    {step.completed ? (
                      <CheckCircle2 className="h-4 w-4 text-accent-600" />
                    ) : (
                      <Circle className="h-4 w-4 text-slate-300" />
                    )}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="text-xs font-semibold text-slate-800">
                        {index + 1}. {step.title}
                      </p>
                      {isCurrent ? (
                        <Badge className="bg-brand-50 text-brand-700 ring-brand-200">
                          Сейчас
                        </Badge>
                      ) : null}
                      {step.action === 'click' ? (
                        <Badge className="bg-amber-50 text-amber-700 ring-amber-200">
                          <MousePointerClick className="h-2.5 w-2.5" />
                          Нажатие
                        </Badge>
                      ) : null}
                    </div>
                    <p className="mt-1 line-clamp-2 text-[11px] leading-5 text-slate-500">
                      {step.body}
                    </p>
                  </div>
                  <span className="shrink-0 text-[10px] font-semibold text-slate-400">
                    {step.duration_seconds} сек
                  </span>
                </div>
              );
            })}
          </div>
        </Card>

        <div className="space-y-4">
          <Card className="p-5">
            <h2 className="text-sm font-bold text-slate-900">Как это работает</h2>
            <ul className="mt-3 space-y-3 text-xs leading-5 text-slate-600">
              <li className="flex gap-2.5">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
                  1
                </span>
                Анимированный указатель подсвечивает место, куда нужно нажать.
              </li>
              <li className="flex gap-2.5">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
                  2
                </span>
                Всплывающая подсказка объясняет смысл действия простыми словами.
              </li>
              <li className="flex gap-2.5">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
                  3
                </span>
                После каждого шага прогресс сохраняется — можно вернуться завтра.
              </li>
            </ul>
          </Card>

          <Card className="border-slate-200 bg-slate-50/70 p-5">
            <h2 className="text-sm font-bold text-slate-900">Только ваши сервисы</h2>
            <p className="mt-2 text-xs leading-5 text-slate-600">
              Программа собрана из включённых сервисов и ваших прав. Если сервис
              отключат, модуль исчезнет из программы; если включат новый — появится
              отдельное дообучение.
            </p>
            <Link to="/profile" className="mt-3 inline-flex">
              <Button variant="outline" size="sm">
                Посмотреть права
                <ArrowRight className="h-3.5 w-3.5" />
              </Button>
            </Link>
          </Card>
        </div>
      </div>

      {module.steps.length === 0 ? (
        <Card>
          <EmptyState
            title="В модуле пока нет шагов"
            description="Содержание обновляется вместе с сервисом. Попробуйте позже."
            icon={<GraduationCap className="h-6 w-6" />}
          />
        </Card>
      ) : null}
    </div>
  );
}
