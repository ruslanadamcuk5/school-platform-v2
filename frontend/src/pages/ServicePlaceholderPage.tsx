import { useEffect, useState, type ReactNode } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  ArrowLeft,
  BookOpen,
  Boxes,
  CheckCircle2,
  Clock,
  Code2,
  ExternalLink,
  Layers,
  Lock,
  Settings2,
  ShieldCheck,
  Sparkles,
  Wrench,
} from 'lucide-react';

import { useAccess } from '../access/AccessContext';
import { apiErrorMessage, API_ORIGIN, fetchServices } from '../api/client';
import type { Service } from '../api/types';
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorAlert,
  PageHeader,
  Spinner,
} from '../components/ui';
import {
  serviceCategoryColors,
  serviceCategoryLabels,
} from '../lib/labels';

const nextSteps: Record<string, string[]> = {
  journal: [
    'Расписание уроков и звонков',
    'Выставление и просмотр оценок',
    'Посещаемость и комментарии учителя',
    'Домашние задания',
  ],
  library: [
    'Каталог учебников и художественной литературы',
    'Выдача и возврат экземпляров',
    'Бронирование и очередь',
    'Отчёты по обеспеченности',
  ],
  lms: [
    'Курсы и учебные модули',
    'Задания и дедлайны',
    'Прогресс ученика',
    'Материалы и тесты',
  ],
  assessment: [
    'Диагностические и контрольные работы',
    'Критериальное оценивание',
    'Аналитика результатов',
    'Печать и экспорт отчётов',
  ],
  analytics: [
    'Сводные дашборды по школе',
    'Сравнение классов и параллелей',
    'Динамика успеваемости',
    'Республиканские срезы',
  ],
  communication: [
    'Объявления и чаты',
    'Уведомления родителям',
    'Опросы и голосования',
    'История коммуникаций',
  ],
  documents: [
    'Шаблоны приказов и справок',
    'Электронный документооборот',
    'Согласование и подписание',
    'Архив с аудитом доступа',
  ],
  safety: [
    'Контроль доступа в здание',
    'Журнал посещаемости',
    'Экстренные уведомления',
    'Интеграция с турникетами',
  ],
  ai: [
    'Помощник учителя по планированию',
    'Проверка и обратная связь',
    'Анализ образовательных данных',
    'Безопасные промпты и аудит',
  ],
  admin: [
    'Управление пользователями школы',
    'Импорт и экспорт данных',
    'Настройки тенанта',
    'Журнал аудита',
  ],
};

const icons: Record<string, string> = {
  journal: '📔',
  library: '📚',
  lms: '🎓',
  assessment: '✅',
  analytics: '📊',
  communication: '💬',
  documents: '📄',
  safety: '🛡️',
  ai: '🤖',
  admin: '⚙️',
  iam: '🔐',
  org: '🏫',
  system: '🧩',
  audit: '🧾',
};

export function ServicePlaceholderPage({ code: codeProp }: { code?: string }) {
  const { code: paramCode } = useParams<{ code: string }>();
  const code = codeProp ?? paramCode ?? '';
  const { services, can } = useAccess();
  const [catalogService, setCatalogService] = useState<Service | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const effectiveService = services.find((service) => service.code === code);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchServices();
        if (!cancelled) {
          setCatalogService(data.items.find((item) => item.code === code) ?? null);
        }
      } catch (caught) {
        if (!cancelled) setError(apiErrorMessage(caught));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [code]);

  if (!effectiveService && !loading && !catalogService) {
    return (
      <div className="space-y-6">
        <PageHeader eyebrow="Сервисы" title="Сервис не найден" />
        <Card>
          <EmptyState
            title="Такого сервиса нет в каталоге"
            description="Проверьте код сервиса или вернитесь к списку подключённых модулей."
            icon={<Boxes className="h-6 w-6" />}
            action={
              <Link to="/services">
                <Button variant="outline">
                  <ArrowLeft className="h-4 w-4" />
                  К сервисам
                </Button>
              </Link>
            }
          />
        </Card>
      </div>
    );
  }

  const name = effectiveService?.name ?? catalogService?.name ?? code;
  const description =
    effectiveService?.description ??
    catalogService?.description ??
    'Сервис платформы «Школьник».';
  const category = effectiveService?.category ?? catalogService?.category ?? 'core';
  const enabled = effectiveService?.enabled ?? false;
  const status = effectiveService?.status ?? catalogService?.status ?? 'active';
  const permissions = catalogService?.manifest.permissions ?? [];
  const dependencies = catalogService?.manifest.depends_on ?? [];
  const steps = nextSteps[code] ?? [
    'Экран модуля в разработке',
    'API-контракт уже доступен',
    'Интеграция с правами и активациями',
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Модуль платформы"
        title={name}
        subtitle={description}
        actions={
          <div className="flex items-center gap-2">
            <Badge className={serviceCategoryColors[category]}>
              {serviceCategoryLabels[category]}
            </Badge>
            <Badge
              className={
                enabled
                  ? 'bg-accent-50 text-accent-700 ring-accent-200'
                  : 'bg-slate-100 text-slate-500 ring-slate-200'
              }
            >
              <span
                className={`h-1.5 w-1.5 rounded-full ${enabled ? 'bg-accent-500' : 'bg-slate-400'}`}
              />
              {enabled ? 'сервис включён' : 'сервис отключён'}
            </Badge>
            {status === 'beta' ? (
              <Badge className="bg-amber-50 text-amber-700 ring-amber-200">beta</Badge>
            ) : null}
          </div>
        }
      />

      {error ? <ErrorAlert message={error} /> : null}

      <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <Card className="relative overflow-hidden p-6 sm:p-8">
          <div className="pointer-events-none absolute right-0 top-0 h-48 w-48 rounded-full bg-brand-100/70 blur-3xl" />
          <div className="relative">
            <div className="flex items-start gap-4">
              <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-3xl bg-slate-100 text-3xl">
                {effectiveService?.icon ?? catalogService?.icon ?? icons[code] ?? '🧩'}
              </div>
              <div className="min-w-0">
                <p className="font-mono text-xs text-slate-400">{code}</p>
                <h2 className="mt-1 text-2xl font-bold tracking-tight text-slate-900">
                  {name}
                </h2>
                <p className="mt-2 max-w-xl text-sm leading-6 text-slate-500">
                  {description}
                </p>
              </div>
            </div>

            <div className="mt-6 rounded-2xl border border-amber-200 bg-amber-50 p-4">
              <div className="flex items-start gap-3">
                <Wrench className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
                <div>
                  <p className="text-sm font-semibold text-amber-900">
                    API уже работает, экран в разработке
                  </p>
                  <p className="mt-1 text-xs leading-5 text-amber-700">
                    Сервис зарегистрирован в каталоге, включён в контур прав и доступен
                    через OpenAPI. Интерфейс модуля появится следующим этапом — сейчас
                    можно проверить контракт и активации.
                  </p>
                </div>
              </div>
            </div>

            <div className="mt-6">
              <h3 className="text-sm font-bold text-slate-900">Что появится в модуле</h3>
              <div className="mt-3 grid gap-2 sm:grid-cols-2">
                {steps.map((step, index) => (
                  <div
                    key={step}
                    className="flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-2.5"
                  >
                    <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-brand-50 text-[10px] font-bold text-brand-600">
                      {index + 1}
                    </span>
                    <span className="text-xs font-medium text-slate-600">{step}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="mt-6 flex flex-wrap gap-2">
              <a href={`${API_ORIGIN}/docs`} target="_blank" rel="noreferrer">
                <Button variant="primary" size="sm">
                  <ExternalLink className="h-4 w-4" />
                  Открыть Swagger
                </Button>
              </a>
              <Link to="/services">
                <Button variant="outline" size="sm">
                  <Settings2 className="h-4 w-4" />
                  Управление сервисами
                </Button>
              </Link>
              <Link to="/">
                <Button variant="ghost" size="sm">
                  <ArrowLeft className="h-4 w-4" />
                  На дашборд
                </Button>
              </Link>
            </div>
          </div>
        </Card>

        <div className="space-y-6">
          <Card className="p-5">
            <h3 className="flex items-center gap-2 text-sm font-bold text-slate-900">
              <ShieldCheck className="h-4 w-4 text-brand-500" />
              Контракт доступа
            </h3>
            <div className="mt-4 space-y-2.5">
              <InfoLine
                icon={<Code2 className="h-4 w-4" />}
                label="API prefix"
                value={catalogService?.api_prefix ?? '—'}
              />
              <InfoLine
                icon={<Lock className="h-4 w-4" />}
                label="Ядро"
                value={catalogService?.is_core ? 'да, отключить нельзя' : 'нет'}
              />
              <InfoLine
                icon={<Layers className="h-4 w-4" />}
                label="Права"
                value={`${permissions.length} в манифесте`}
              />
              <InfoLine
                icon={<Clock className="h-4 w-4" />}
                label="Версия"
                value={`v${catalogService?.version ?? '0.0.0'}`}
              />
            </div>

            {permissions.length > 0 ? (
              <div className="mt-4">
                <p className="text-[10px] font-bold uppercase tracking-wide text-slate-400">
                  Права сервиса
                </p>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {permissions.slice(0, 8).map((permission) => (
                    <span
                      key={permission.code}
                      className="rounded-lg bg-slate-100 px-2 py-1 font-mono text-[9px] text-slate-600"
                      title={permission.name}
                    >
                      {permission.code}
                    </span>
                  ))}
                  {permissions.length > 8 ? (
                    <span className="rounded-lg bg-slate-100 px-2 py-1 text-[9px] font-semibold text-slate-500">
                      +{permissions.length - 8}
                    </span>
                  ) : null}
                </div>
              </div>
            ) : null}

            {dependencies.length > 0 ? (
              <div className="mt-4">
                <p className="text-[10px] font-bold uppercase tracking-wide text-slate-400">
                  Зависимости
                </p>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {dependencies.map((dependency) => (
                    <Badge key={dependency} className="bg-white text-slate-600 ring-slate-200">
                      {dependency}
                    </Badge>
                  ))}
                </div>
              </div>
            ) : null}
          </Card>

          <Card className="p-5">
            <h3 className="flex items-center gap-2 text-sm font-bold text-slate-900">
              <Sparkles className="h-4 w-4 text-brand-500" />
              Доступность
            </h3>
            <div className="mt-3 space-y-2">
              <div className="flex items-center justify-between rounded-xl bg-slate-50 px-3 py-2 text-xs">
                <span className="text-slate-500">В вашем контуре</span>
                <span
                  className={`inline-flex items-center gap-1.5 font-semibold ${enabled ? 'text-accent-700' : 'text-slate-500'}`}
                >
                  {enabled ? (
                    <CheckCircle2 className="h-3.5 w-3.5" />
                  ) : (
                    <Lock className="h-3.5 w-3.5" />
                  )}
                  {enabled ? 'включён' : 'отключён'}
                </span>
              </div>
              <div className="flex items-center justify-between rounded-xl bg-slate-50 px-3 py-2 text-xs">
                <span className="text-slate-500">Источник состояния</span>
                <span className="font-semibold text-slate-700">
                  {effectiveService?.source ?? '—'}
                </span>
              </div>
            </div>
            {!enabled && can('system.services.write') ? (
              <Link to="/services" className="mt-3 block">
                <Button variant="secondary" size="sm" className="w-full">
                  <Settings2 className="h-4 w-4" />
                  Включить в управлении сервисами
                </Button>
              </Link>
            ) : null}
          </Card>

          <Card className="flex items-start gap-3 border-brand-100 bg-gradient-to-br from-brand-50 to-white p-4">
            <BookOpen className="mt-0.5 h-4 w-4 shrink-0 text-brand-600" />
            <p className="text-[11px] leading-5 text-slate-600">
              Полный пакет документации — в <code className="text-brand-700">docs/</code>.
              Архитектура, права и API описаны в ШК-03-04, ШК-03-05 и ШК-04-02.
            </p>
          </Card>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center gap-2 py-4 text-xs text-slate-400">
          <Spinner className="h-4 w-4" />
          Уточняем манифест сервиса…
        </div>
      ) : null}
    </div>
  );
}

function InfoLine({
  icon,
  label,
  value,
}: {
  icon: ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center gap-2.5 rounded-xl border border-slate-200 px-3 py-2">
      <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-slate-100 text-slate-500">
        {icon}
      </span>
      <span className="flex-1 text-[11px] text-slate-500">{label}</span>
      <span className="max-w-[55%] truncate text-[11px] font-semibold text-slate-800">
        {value}
      </span>
    </div>
  );
}
